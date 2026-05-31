import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import asdict
from pathlib import Path

from app.models import AgentFinding, AgentRun, LoanFile
from app.rag import GuidelineStore


REQUIRED_DOCUMENTS = {
    "purchase": ["purchase contract", "income verification", "bank statements", "photo ID", "appraisal"],
    "refinance": ["income verification", "bank statements", "homeowners insurance", "title report"],
}


class MortgageAgent:
    def __init__(self):
        self.guidelines = GuidelineStore(Path(__file__).resolve().parents[1] / "data")

    def run(self, loan: LoanFile) -> AgentRun:
        context_query = (
            f"{loan.loan_purpose} {loan.property_type} {loan.employment_type} "
            f"ltv {loan.ltv} credit {loan.borrower.credit_score} {loan.notes}"
        )
        citations = self.guidelines.search(context_query)
        missing_docs = self._missing_documents(loan)
        findings = self._findings(loan, missing_docs, citations)
        readiness = self._readiness_score(loan, missing_docs, findings)
        actions = self._next_actions(loan, missing_docs, findings)
        message = self._borrower_message(loan, missing_docs, actions, citations)

        if readiness >= 82:
            status = "ready_for_underwriter_review"
        elif readiness >= 62:
            status = "needs_borrower_follow_up"
        else:
            status = "high_risk_file"

        return AgentRun(
            loan_id=loan.id,
            readiness_score=readiness,
            status=status,
            findings=findings,
            missing_documents=missing_docs,
            borrower_message=message,
            next_best_actions=actions,
            citations=citations,
        )

    def _missing_documents(self, loan: LoanFile) -> list[str]:
        uploaded = self._document_corpus(loan)
        required = REQUIRED_DOCUMENTS.get(loan.loan_purpose, REQUIRED_DOCUMENTS["purchase"])

        missing = []
        for doc in required:
            if doc == "income verification":
                has_income_doc = any(term in uploaded for term in ["paystub", "w2", "tax return", "profit loss"])
                if not has_income_doc:
                    missing.append(doc)
            elif doc == "bank statements":
                if uploaded.count("bank statement") < 2:
                    missing.append("two months of bank statements")
            elif doc.lower() not in uploaded:
                missing.append(doc)

        if "self-employed" in loan.employment_type.lower() and "tax return" not in uploaded:
            missing.append("two years business tax returns")

        return missing

    def _document_corpus(self, loan: LoanFile) -> str:
        filenames = " ".join(loan.uploaded_documents)
        extracted = " ".join(record.extracted_text for record in loan.document_records)
        return f"{filenames} {extracted}".lower().replace("_", " ")

    def _findings(
        self, loan: LoanFile, missing_docs: list[str], citations: list[dict[str, str | float]]
    ) -> list[AgentFinding]:
        findings = []
        evidence = [item["source"] for item in citations]

        if loan.ltv >= 0.9:
            findings.append(
                AgentFinding(
                    label="High LTV",
                    severity="high",
                    detail=f"LTV is {loan.ltv:.1%}, so pricing, mortgage insurance, and overlays should be reviewed.",
                    evidence=evidence,
                )
            )

        if loan.borrower.credit_score < 700:
            findings.append(
                AgentFinding(
                    label="Credit review required",
                    severity="medium",
                    detail=f"Credit score is {loan.borrower.credit_score}; review compensating factors and conditions.",
                    evidence=evidence,
                )
            )

        if "self-employed" in loan.employment_type.lower():
            findings.append(
                AgentFinding(
                    label="Variable income",
                    severity="medium",
                    detail="Self-employed income requires tax return support and income stability review.",
                    evidence=evidence,
                )
            )

        if missing_docs:
            findings.append(
                AgentFinding(
                    label="Missing conditions",
                    severity="high",
                    detail=f"{len(missing_docs)} required item(s) are missing before the file is complete.",
                    evidence=evidence,
                )
            )

        return findings

    def _readiness_score(self, loan: LoanFile, missing_docs: list[str], findings: list[AgentFinding]) -> int:
        score = 92
        score -= len(missing_docs) * 9
        score -= sum(12 for finding in findings if finding.severity == "high")
        score -= sum(6 for finding in findings if finding.severity == "medium")
        if loan.borrower.credit_score >= 740:
            score += 4
        if loan.ltv < 0.8:
            score += 3
        return max(0, min(score, 100))

    def _next_actions(self, loan: LoanFile, missing_docs: list[str], findings: list[AgentFinding]) -> list[str]:
        actions = []
        if missing_docs:
            actions.append("Send borrower a concise missing-documents request.")
        if any(finding.label == "High LTV" for finding in findings):
            actions.append("Route file to underwriting for LTV and mortgage-insurance review.")
        if "Appraisal scheduled" in loan.notes or "appraisal" in missing_docs:
            actions.append("Follow up on appraisal completion and expected delivery date.")
        if "self-employed" in loan.employment_type.lower():
            actions.append("Request tax returns and verify stable self-employed income.")
        return actions or ["Move file to underwriter review queue."]

    def _borrower_message(
        self, loan: LoanFile, missing_docs: list[str], actions: list[str], citations: list[dict[str, str | float]]
    ) -> str:
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        if openai_key:
            generated = self._openai_message(loan, missing_docs, actions, citations)
            if generated:
                return generated

        docs = ", ".join(missing_docs) if missing_docs else "no additional documents right now"
        return (
            f"Hi {loan.borrower.name}, thanks for moving quickly on your loan file. "
            f"To keep your {loan.loan_purpose} on track, please send: {docs}. "
            "Once we receive these items, our team can continue review and help avoid closing delays."
        )

    def _openai_message(
        self, loan: LoanFile, missing_docs: list[str], actions: list[str], citations: list[dict[str, str | float]]
    ) -> str:
        try:
            from openai import OpenAI
        except ImportError:
            return ""

        client = OpenAI(timeout=8.0, max_retries=0)
        context = "\n\n".join(item["text"] for item in citations)
        prompt = (
            "Draft a concise, friendly borrower email. Do not mention internal risk scores. "
            "Ground the request in the loan context and missing documents.\n\n"
            f"Borrower: {loan.borrower.name}\nLoan purpose: {loan.loan_purpose}\n"
            f"Missing docs: {missing_docs}\nNext actions: {actions}\nGuidelines:\n{context}"
        )
        def create_response():
            return client.responses.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                input=prompt,
                temperature=0.2,
            )

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(create_response)
        try:
            response = future.result(timeout=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "6")))
            return response.output_text.strip()
        except (Exception, TimeoutError):
            future.cancel()
            return ""
        finally:
            executor.shutdown(wait=False, cancel_futures=True)


def serialize_run(run: AgentRun) -> dict:
    payload = asdict(run)
    payload["findings"] = [asdict(item) for item in run.findings]
    return payload
