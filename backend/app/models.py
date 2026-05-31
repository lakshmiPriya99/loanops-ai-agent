from dataclasses import dataclass, field
from typing import Any


@dataclass
class Borrower:
    name: str
    email: str
    phone: str
    annual_income: float
    credit_score: int


@dataclass
class UploadedDocument:
    filename: str
    stored_path: str
    content_type: str
    size_bytes: int
    extracted_text: str = ""
    storage_provider: str = "local"


@dataclass
class LoanFile:
    id: str
    borrower: Borrower
    loan_amount: float
    property_value: float
    loan_purpose: str
    property_type: str
    employment_type: str
    uploaded_documents: list[str] = field(default_factory=list)
    document_records: list[UploadedDocument] = field(default_factory=list)
    notes: str = ""

    @property
    def ltv(self) -> float:
        if self.property_value <= 0:
            return 0
        return round(self.loan_amount / self.property_value, 3)


@dataclass
class AgentFinding:
    label: str
    severity: str
    detail: str
    evidence: list[str]


@dataclass
class AgentRun:
    loan_id: str
    readiness_score: int
    status: str
    findings: list[AgentFinding]
    missing_documents: list[str]
    borrower_message: str
    next_best_actions: list[str]
    citations: list[dict[str, Any]]
