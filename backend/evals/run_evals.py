from copy import deepcopy
import json
from pathlib import Path

from app.models import Borrower, LoanFile


def run_all(agent, loan_files):
    eval_loan_files = deepcopy(loan_files)
    for loan in eval_loan_files.values():
        loan.document_records = []
        loan.uploaded_documents = [
            doc
            for doc in loan.uploaded_documents
            if doc
            in {
                "purchase_contract.pdf",
                "paystub_april.pdf",
                "bank_statement_march.pdf",
                "drivers_license.png",
                "bank_statement_april.pdf",
                "bank_statement_march.pdf",
                "homeowners_insurance.pdf",
            }
        ]

    cases = json.loads((Path(__file__).with_name("eval_cases.json")).read_text(encoding="utf-8"))

    results = []
    for case in cases:
        if "loan" in case:
            payload = case["loan"]
            payload["borrower"] = Borrower(**payload["borrower"])
            run = agent.run(LoanFile(**payload))
        else:
            run = agent.run(eval_loan_files[case["loan_id"]])
        assertions = build_assertions(case)
        passed = 0
        failures = []
        for index, assertion in enumerate(assertions, start=1):
            try:
                ok = assertion(run)
            except Exception as exc:
                ok = False
                failures.append(f"assertion {index}: {exc}")
            if ok:
                passed += 1
            else:
                failures.append(f"assertion {index} failed")

        results.append(
            {
                "name": case["name"],
                "loan_id": case.get("loan_id") or case["loan"]["id"],
                "passed": passed,
                "total": len(assertions),
                "failures": failures,
            }
        )

    total = sum(item["total"] for item in results)
    passed = sum(item["passed"] for item in results)
    return {"passed": passed, "total": total, "score": round(passed / total, 3), "results": results}


def build_assertions(case):
    assertions = []
    for needle in case.get("contains_missing", []):
        assertions.append(lambda run, needle=needle: needle in " ".join(run.missing_documents).lower())
    for needle in case.get("message_contains", []):
        assertions.append(lambda run, needle=needle: needle in run.borrower_message)
    for label in case.get("finding_labels", []):
        assertions.append(lambda run, label=label: any(label == finding.label for finding in run.findings))
    if case.get("status_any"):
        allowed = set(case["status_any"])
        assertions.append(lambda run, allowed=allowed: run.status in allowed)
    assertions.append(lambda run: bool(run.citations))
    return assertions
