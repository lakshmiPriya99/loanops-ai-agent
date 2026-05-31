import os
from dataclasses import asdict

from flask_sqlalchemy import SQLAlchemy

from app.models import Borrower, LoanFile, UploadedDocument
from app.sample_data import LOAN_FILES

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(160), nullable=False)
    role = db.Column(db.String(40), nullable=False, default="processor")


class Loan(db.Model):
    id = db.Column(db.String(32), primary_key=True)
    borrower_name = db.Column(db.String(160), nullable=False)
    borrower_email = db.Column(db.String(255), nullable=False)
    borrower_phone = db.Column(db.String(80), nullable=False)
    annual_income = db.Column(db.Float, nullable=False)
    credit_score = db.Column(db.Integer, nullable=False)
    loan_amount = db.Column(db.Float, nullable=False)
    property_value = db.Column(db.Float, nullable=False)
    loan_purpose = db.Column(db.String(40), nullable=False)
    property_type = db.Column(db.String(160), nullable=False)
    employment_type = db.Column(db.String(80), nullable=False)
    notes = db.Column(db.Text, nullable=False, default="")
    documents = db.relationship("Document", backref="loan", cascade="all, delete-orphan", lazy=True)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.String(32), db.ForeignKey("loan.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.Text, nullable=False, default="")
    storage_provider = db.Column(db.String(40), nullable=False, default="local")
    content_type = db.Column(db.String(160), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False, default=0)
    extracted_text = db.Column(db.Text, nullable=False, default="")


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actor_email = db.Column(db.String(255), nullable=False)
    actor_role = db.Column(db.String(40), nullable=False)
    action = db.Column(db.String(80), nullable=False)
    entity_type = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.String(80), nullable=False)
    details = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)


class ModelTrace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.String(32), nullable=False)
    job_id = db.Column(db.String(80), nullable=True)
    model = db.Column(db.String(80), nullable=False, default="deterministic")
    prompt = db.Column(db.Text, nullable=False, default="")
    retrieved_context = db.Column(db.JSON, nullable=False, default=list)
    output_summary = db.Column(db.Text, nullable=False, default="")
    latency_ms = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)


class AgentJob(db.Model):
    id = db.Column(db.String(80), primary_key=True)
    loan_id = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(40), nullable=False, default="queued")
    result = db.Column(db.JSON, nullable=True)
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)


def configure_database(app):
    database_url = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://loanops:loanops@postgres:5432/loanops"
    )
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        seed_defaults()


def seed_defaults():
    if not User.query.filter_by(email="processor@example.com").first():
        db.session.add_all(
            [
                User(email="processor@example.com", name="Demo Processor", role="processor"),
                User(email="underwriter@example.com", name="Demo Underwriter", role="underwriter"),
                User(email="admin@example.com", name="Demo Admin", role="admin"),
            ]
        )
    for loan in LOAN_FILES.values():
        existing_loan = Loan.query.get(loan.id)
        if existing_loan:
            refresh_demo_loan(existing_loan, loan)
        else:
            db.session.add(loan_from_dataclass(loan))
    db.session.commit()


def refresh_demo_loan(existing_loan: Loan, loan: LoanFile):
    existing_loan.borrower_name = loan.borrower.name
    existing_loan.borrower_email = loan.borrower.email
    existing_loan.borrower_phone = loan.borrower.phone
    existing_loan.annual_income = loan.borrower.annual_income
    existing_loan.credit_score = loan.borrower.credit_score
    existing_loan.loan_amount = loan.loan_amount
    existing_loan.property_value = loan.property_value
    existing_loan.loan_purpose = loan.loan_purpose
    existing_loan.property_type = loan.property_type
    existing_loan.employment_type = loan.employment_type
    existing_loan.notes = loan.notes


def loan_from_dataclass(loan: LoanFile) -> Loan:
    return Loan(
        id=loan.id,
        borrower_name=loan.borrower.name,
        borrower_email=loan.borrower.email,
        borrower_phone=loan.borrower.phone,
        annual_income=loan.borrower.annual_income,
        credit_score=loan.borrower.credit_score,
        loan_amount=loan.loan_amount,
        property_value=loan.property_value,
        loan_purpose=loan.loan_purpose,
        property_type=loan.property_type,
        employment_type=loan.employment_type,
        notes=loan.notes,
    )


def loan_to_dataclass(loan: Loan) -> LoanFile:
    records = [
        UploadedDocument(
            filename=document.filename,
            stored_path=document.stored_path,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            extracted_text=document.extracted_text,
            storage_provider=document.storage_provider,
        )
        for document in loan.documents
    ]
    uploaded = []
    if loan.id in LOAN_FILES:
        uploaded.extend(LOAN_FILES[loan.id].uploaded_documents)
    uploaded.extend(document.filename for document in loan.documents)
    uploaded = list(dict.fromkeys(uploaded))
    return LoanFile(
        id=loan.id,
        borrower=Borrower(
            name=loan.borrower_name,
            email=loan.borrower_email,
            phone=loan.borrower_phone,
            annual_income=loan.annual_income,
            credit_score=loan.credit_score,
        ),
        loan_amount=loan.loan_amount,
        property_value=loan.property_value,
        loan_purpose=loan.loan_purpose,
        property_type=loan.property_type,
        employment_type=loan.employment_type,
        uploaded_documents=uploaded,
        document_records=records,
        notes=loan.notes,
    )


def loan_payload(loan: Loan) -> dict:
    return asdict(loan_to_dataclass(loan))
