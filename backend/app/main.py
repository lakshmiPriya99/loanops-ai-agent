import os
import threading
from datetime import datetime
from dataclasses import asdict
from uuid import uuid4

from flask import Flask, jsonify, request
from flask_cors import CORS
from rq.job import Job as RQJob

from app.agent import MortgageAgent, serialize_run
from app.auth import require_role
from app.database import AgentJob, AuditLog, Document, Loan, ModelTrace, configure_database, db, loan_payload, loan_to_dataclass
from app.jobs import run_agent_job
from app.models import Borrower, LoanFile
from app.observability import audit
from app.queue import agent_queue, redis_connection
from app.sample_data import LOAN_FILES
from app.storage import (
    add_named_document,
    hydrate_loan_state,
    persist_custom_loans,
    persist_loan_state,
    save_uploaded_file,
)


app = Flask(__name__)
CORS(app)
configure_database(app)
agent = MortgageAgent()


def use_thread_jobs():
    return os.getenv("ASYNC_BACKEND", "rq").lower() == "thread"


def use_sync_jobs():
    return os.getenv("ASYNC_BACKEND", "rq").lower() == "sync"


def run_thread_job(job_id: str, loan_id: str):
    with app.app_context():
        job = AgentJob.query.get(job_id)
        if not job:
            return
        job.status = "started"
        db.session.commit()
        try:
            result = run_agent_job(loan_id)
            job.status = "finished"
            job.result = result
            job.ended_at = datetime.utcnow()
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            job.ended_at = datetime.utcnow()
        db.session.commit()


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "addy-mortgage-agent"})


@app.get("/api/loans")
def loans():
    return jsonify({"loans": [loan_payload(loan) for loan in Loan.query.order_by(Loan.id).all()]})


@app.post("/api/loans")
@require_role("processor")
def create_loan():
    payload = request.get_json(silent=True) or {}
    borrower_payload = payload.get("borrower", {})
    existing_ids = [loan.id for loan in Loan.query.all() if loan.id.startswith("LN-")]
    loan_id = payload.get("id") or f"LN-{max([int(key.split('-')[1]) for key in existing_ids] + [3000]) + 1}"

    if Loan.query.get(loan_id):
        return jsonify({"error": "Loan ID already exists"}), 409

    required = ["name", "email", "phone", "annual_income", "credit_score"]
    missing = [field for field in required if borrower_payload.get(field) in (None, "")]
    if missing:
        return jsonify({"error": f"Missing borrower fields: {', '.join(missing)}"}), 400

    loan = Loan(
        id=loan_id,
        borrower_name=borrower_payload["name"],
        borrower_email=borrower_payload["email"],
        borrower_phone=borrower_payload["phone"],
        annual_income=float(borrower_payload["annual_income"]),
        credit_score=int(borrower_payload["credit_score"]),
        loan_amount=float(payload.get("loan_amount", 0)),
        property_value=float(payload.get("property_value", 0)),
        loan_purpose=payload.get("loan_purpose", "purchase"),
        property_type=payload.get("property_type", "single-family primary residence"),
        employment_type=payload.get("employment_type", "W2 salaried"),
        notes=payload.get("notes", ""),
    )
    db.session.add(loan)
    db.session.commit()
    audit("create_loan", "loan", loan.id, {"borrower": loan.borrower_name})
    return jsonify(loan_payload(loan)), 201


@app.get("/api/loans/<loan_id>")
def loan_detail(loan_id):
    loan = Loan.query.get(loan_id)
    if not loan:
        return jsonify({"error": "Loan file not found"}), 404
    return jsonify(loan_payload(loan))


@app.post("/api/loans/<loan_id>/documents")
@require_role("processor")
def upload_document(loan_id):
    loan = Loan.query.get(loan_id)
    if not loan:
        return jsonify({"error": "Loan file not found"}), 404

    records = []
    loan_file = loan_to_dataclass(loan)
    if request.files:
        for file in request.files.getlist("documents"):
            if file.filename:
                records.append(save_uploaded_file(loan_file, file))
    else:
        payload = request.get_json(silent=True) or {}
        for name in payload.get("documents", []):
            if name and name.strip():
                records.append(add_named_document(loan_file, name))

    for record in records:
        db.session.add(
            Document(
                loan_id=loan.id,
                filename=record.filename,
                stored_path=record.stored_path,
                storage_provider=record.storage_provider,
                content_type=record.content_type,
                size_bytes=record.size_bytes,
                extracted_text=record.extracted_text,
            )
        )
    db.session.commit()
    audit("upload_documents", "loan", loan.id, {"filenames": [record.filename for record in records]})

    return jsonify({"loan": loan_payload(Loan.query.get(loan.id)), "uploaded": [asdict(record) for record in records]})


@app.post("/api/agent/run")
def run_agent():
    loan_id = request.json.get("loan_id", "LN-1042") if request.is_json else "LN-1042"
    loan = Loan.query.get(loan_id)
    if not loan:
        return jsonify({"error": "Loan file not found"}), 404
    if request.args.get("sync") == "1" or use_sync_jobs():
        result = serialize_run(agent.run(loan_to_dataclass(loan)))
        audit("run_agent_sync", "loan", loan_id, {"status": result["status"]})
        return jsonify(result)
    if use_thread_jobs():
        job_id = f"thread-{uuid4()}"
        db.session.add(AgentJob(id=job_id, loan_id=loan_id, status="queued"))
        db.session.commit()
        threading.Thread(target=run_thread_job, args=(job_id, loan_id), daemon=True).start()
        audit("enqueue_agent_thread", "loan", loan_id, {"job_id": job_id})
        return jsonify({"job_id": job_id, "loan_id": loan_id, "status": "queued"}), 202
    job = agent_queue().enqueue(run_agent_job, loan_id, job_timeout=120, result_ttl=3600)
    audit("enqueue_agent_run", "loan", loan_id, {"job_id": job.id})
    return jsonify({"job_id": job.id, "loan_id": loan_id, "status": job.get_status()}), 202


@app.get("/api/agent/jobs/<job_id>")
def agent_job_status(job_id):
    if use_thread_jobs() or job_id.startswith("thread-"):
        job = AgentJob.query.get(job_id)
        if not job:
            return jsonify({"error": "Agent job not found"}), 404
        return jsonify(
            {
                "job_id": job.id,
                "loan_id": job.loan_id,
                "status": job.status,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                "result": job.result,
                "error": job.error,
            }
        )
    try:
        job = RQJob.fetch(job_id, connection=redis_connection())
    except Exception:
        return jsonify({"error": "Agent job not found"}), 404

    payload = {
        "job_id": job.id,
        "status": job.get_status(),
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
    }
    if job.is_finished:
        payload["result"] = job.result
    if job.is_failed:
        payload["error"] = str(job.exc_info)
    return jsonify(payload)


@app.post("/api/evals/run")
def run_evals():
    from evals.run_evals import run_all

    openai_key = os.environ.pop("OPENAI_API_KEY", None)
    try:
        return jsonify(run_all(agent, LOAN_FILES))
    finally:
        if openai_key is not None:
            os.environ["OPENAI_API_KEY"] = openai_key


@app.get("/api/audit-logs")
@require_role("underwriter")
def audit_logs():
    rows = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return jsonify(
        {
            "audit_logs": [
                {
                    "id": row.id,
                    "actor_email": row.actor_email,
                    "actor_role": row.actor_role,
                    "action": row.action,
                    "entity_type": row.entity_type,
                    "entity_id": row.entity_id,
                    "details": row.details,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        }
    )


@app.get("/api/model-traces")
@require_role("underwriter")
def model_traces():
    rows = ModelTrace.query.order_by(ModelTrace.created_at.desc()).limit(100).all()
    return jsonify(
        {
            "model_traces": [
                {
                    "id": row.id,
                    "loan_id": row.loan_id,
                    "job_id": row.job_id,
                    "model": row.model,
                    "prompt": row.prompt,
                    "retrieved_context": row.retrieved_context,
                    "output_summary": row.output_summary,
                    "latency_ms": row.latency_ms,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
