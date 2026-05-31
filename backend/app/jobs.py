import os

from app.agent import MortgageAgent, serialize_run
from app.database import Loan, configure_database, loan_to_dataclass
from app.observability import record_trace


def worker_app():
    from flask import Flask

    app = Flask(__name__)
    configure_database(app)
    return app


def run_agent_job(loan_id: str) -> dict:
    app = worker_app()
    with app.app_context():
        loan = Loan.query.get(loan_id)
        if not loan:
            raise ValueError(f"Loan file not found: {loan_id}")
        result = serialize_run(MortgageAgent().run(loan_to_dataclass(loan)))
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini") if os.getenv("OPENAI_API_KEY") else "deterministic"
        record_trace(
            loan_id=loan_id,
            model=model,
            prompt=f"Review loan file {loan_id} and identify missing conditions.",
            retrieved_context=result.get("citations", []),
            output_summary=f"{result['status']} score={result['readiness_score']}",
        )
        return result
