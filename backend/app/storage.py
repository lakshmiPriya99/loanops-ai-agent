import json
import re
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from app.cloud_storage import storage_backend
from app.models import LoanFile, UploadedDocument


UPLOAD_ROOT = Path(__file__).resolve().parents[1] / "uploads"
STATE_PATH = UPLOAD_ROOT / "loan_state.json"
CUSTOM_LOANS_PATH = UPLOAD_ROOT / "custom_loans.json"


def hydrate_loan_state(loan_files: dict[str, LoanFile]) -> None:
    hydrate_custom_loans(loan_files)
    if not STATE_PATH.exists():
        return
    payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    for loan_id, records in payload.items():
        loan = loan_files.get(loan_id)
        if not loan:
            continue
        loan.document_records = [UploadedDocument(**record) for record in records]
        for record in loan.document_records:
            if record.filename not in loan.uploaded_documents:
                loan.uploaded_documents.append(record.filename)


def persist_loan_state(loan_files: dict[str, LoanFile]) -> None:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        loan_id: [asdict(record) for record in loan.document_records]
        for loan_id, loan in loan_files.items()
        if loan.document_records
    }
    STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def hydrate_custom_loans(loan_files: dict[str, LoanFile]) -> None:
    if not CUSTOM_LOANS_PATH.exists():
        return
    payload = json.loads(CUSTOM_LOANS_PATH.read_text(encoding="utf-8"))
    from app.models import Borrower

    for item in payload:
        borrower = Borrower(**item["borrower"])
        item = {**item, "borrower": borrower, "document_records": []}
        loan_files[item["id"]] = LoanFile(**item)


def persist_custom_loans(loan_files: dict[str, LoanFile]) -> None:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    sample_ids = {"LN-1042", "LN-2099"}
    payload = []
    for loan_id, loan in loan_files.items():
        if loan_id in sample_ids:
            continue
        item = asdict(loan)
        item["document_records"] = []
        payload.append(item)
    CUSTOM_LOANS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_uploaded_file(loan: LoanFile, file_storage) -> UploadedDocument:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    loan_dir = UPLOAD_ROOT / loan.id
    loan_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(file_storage.filename or f"document-{uuid4().hex}")
    stored_path = loan_dir / f"{uuid4().hex}-{safe_name}"
    file_storage.save(stored_path)
    backend = storage_backend()
    stored_uri = backend.save(stored_path, f"loans/{loan.id}/{stored_path.name}")

    record = UploadedDocument(
        filename=safe_name,
        stored_path=stored_uri,
        storage_provider=backend.provider,
        content_type=file_storage.content_type or "application/octet-stream",
        size_bytes=stored_path.stat().st_size,
        extracted_text=extract_text(stored_path, file_storage.content_type or ""),
    )
    loan.document_records.append(record)
    if record.filename not in loan.uploaded_documents:
        loan.uploaded_documents.append(record.filename)
    return record


def add_named_document(loan: LoanFile, filename: str) -> UploadedDocument:
    record = UploadedDocument(
        filename=sanitize_filename(filename),
        stored_path="",
        storage_provider="demo",
        content_type="demo/name-only",
        size_bytes=0,
        extracted_text=infer_text_from_filename(filename),
    )
    loan.document_records.append(record)
    if record.filename not in loan.uploaded_documents:
        loan.uploaded_documents.append(record.filename)
    return record


def sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "", filename).strip()
    return cleaned or f"document-{uuid4().hex}"


def extract_text(path: Path, content_type: str) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".csv"} or content_type.startswith("text/"):
        return path.read_text(encoding="utf-8", errors="ignore")[:4000]
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return infer_text_from_filename(path.name)
        reader = PdfReader(str(path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return text[:4000] or ocr_text(path) or infer_text_from_filename(path.name)
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        return ocr_text(path) or infer_text_from_filename(path.name)
    return infer_text_from_filename(path.name)


def ocr_text(path: Path) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""
    try:
        return pytesseract.image_to_string(Image.open(path))[:4000]
    except Exception:
        return ""


def infer_text_from_filename(filename: str) -> str:
    name = filename.replace("_", " ").replace("-", " ").lower()
    hints = []
    if "appraisal" in name:
        hints.append("appraisal report")
    if "bank" in name or "statement" in name:
        hints.append("bank statement asset documentation")
    if "paystub" in name or "w2" in name:
        hints.append("income verification")
    if "tax" in name or "return" in name:
        hints.append("tax return income documentation")
    if "id" in name or "license" in name:
        hints.append("photo identity verification")
    if "title" in name:
        hints.append("title report")
    if "insurance" in name:
        hints.append("homeowners insurance")
    return " ".join(hints)
