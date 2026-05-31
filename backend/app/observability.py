from app.auth import current_actor
from app.database import AuditLog, ModelTrace, db


def audit(action: str, entity_type: str, entity_id: str, details: dict | None = None):
    actor = current_actor()
    db.session.add(
        AuditLog(
            actor_email=actor["email"],
            actor_role=actor["role"],
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
    )
    db.session.commit()


def record_trace(
    loan_id: str,
    model: str,
    prompt: str,
    retrieved_context: list,
    output_summary: str,
    latency_ms: int = 0,
    job_id: str | None = None,
):
    db.session.add(
        ModelTrace(
            loan_id=loan_id,
            job_id=job_id,
            model=model,
            prompt=prompt,
            retrieved_context=retrieved_context,
            output_summary=output_summary,
            latency_ms=latency_ms,
        )
    )
    db.session.commit()
