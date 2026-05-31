# LoanOps AI Agent

LoanOps AI Agent is a production-minded mortgage lending workflow that helps loan teams create borrower files, upload documents, run an AI review agent asynchronously, identify missing conditions, score underwriting readiness, draft borrower follow-up messages, and review audit logs/model traces.

This project was built for a Forward Deployed AI Engineer role in lending AI. It focuses on the same applied-AI problems Addy AI works on: borrower communication, document intake, underwriting support, agent workflows, evals, and production observability.

## What It Does

1. A lender creates or selects a borrower loan file.
2. The lender uploads borrower documents.
3. The backend stores loan/document data in PostgreSQL.
4. Uploaded documents are saved through a storage abstraction.
5. PDF/text/image documents are parsed with PDF extraction and OCR hooks.
6. The frontend enqueues an async agent run.
7. Redis/RQ sends the job to a worker.
8. The worker retrieves lending guideline context, checks the loan file, and returns:
   - missing conditions
   - underwriting readiness score
   - risk findings
   - next-best actions
   - borrower-ready follow-up message
   - RAG citations
9. Audit logs and model traces are stored for review.
10. Evals verify that important agent behavior has not regressed.

## Tech Stack

- **Frontend:** Next.js, TypeScript, React
- **Backend:** Python, Flask
- **Database:** PostgreSQL
- **Queue:** Redis + RQ worker
- **AI:** RAG-style retrieval, optional OpenAI generation
- **Documents:** PDF text extraction, OCR hooks with Tesseract
- **Storage:** Local Docker volume by default, S3/GCS/Firebase adapters included
- **Infra:** Docker Compose
- **Quality:** JSON-backed eval dataset

## Architecture

```text
Browser / Lender UI
        |
        v
Next.js Frontend
        |
        v
Flask API -------------- PostgreSQL
   |                         |
   |                         |-- loans
   |                         |-- documents
   |                         |-- users/roles
   |                         |-- audit logs
   |                         |-- model traces
   |
   | enqueue job
   v
Redis Queue
   |
   v
RQ Worker
   |
   |-- loads loan/document context
   |-- retrieves guideline context
   |-- runs mortgage AI agent
   |-- writes model trace
   v
Agent Result
```

## Key Features

- Create new borrower loan files end to end.
- Upload borrower documents to a persistent backend.
- Store loans, documents, audit logs, and traces in PostgreSQL.
- Run agent reviews asynchronously through Redis/RQ.
- Retrieve mortgage guideline context for grounded recommendations.
- Detect missing documents for purchase, refinance, W2, and self-employed scenarios.
- Score readiness and flag high-LTV, credit, variable-income, and missing-condition risks.
- Draft borrower-safe follow-up messages.
- Support optional OpenAI generation while preserving deterministic fallback behavior.
- Role-aware workflows for `processor`, `underwriter`, and `admin`.
- Audit logs for important user actions.
- Model traces for prompt/context/output visibility.
- Expanded eval dataset with 13 checks.
- Cloud storage adapters for S3, GCS, and Firebase.

## Run Locally

Prerequisite: Docker Desktop must be running.

```bash
cp .env.example .env
docker compose up --build
```

Open:

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:5001/api/health`

To stop:

```bash
docker compose down
```

To remove persisted database/uploads:

```bash
docker compose down -v
```

## Docker Services

- `frontend`: Next.js lender workspace
- `backend`: Flask API
- `worker`: Redis/RQ async agent worker
- `redis`: queue broker
- `postgres`: persistent relational database

## Deploy Live On Render

This repository includes `render.yaml`, which defines a free live deployment:

- `loanops-frontend`: public Next.js web app
- `loanops-backend`: Flask API
- `loanops-postgres`: managed PostgreSQL database

Render's Blueprint flow provisions all of these services from one file.

Deploy steps:

1. Push this project to a GitHub repository.
2. Open the Render Dashboard.
3. Click **New** > **Blueprint**.
4. Connect the GitHub repository.
5. Select the root-level `render.yaml`.
6. Enter `OPENAI_API_KEY` when Render asks for synced secrets, or leave it blank to use the deterministic demo agent.
7. Deploy the Blueprint.
8. Open the public URL for `loanops-frontend`.

The frontend calls `/api/...` on the same domain. Its Next.js API proxy forwards those requests to the private backend service, so the live browser never needs a hardcoded backend URL.

The free deployment uses `ASYNC_BACKEND=sync`, so agent reviews run directly in the backend request and do not require a paid worker service, Redis, or queue infrastructure. Local Docker Compose still includes Redis/RQ code paths if you want to discuss how the system could be extended back to production-grade async processing.

## Demo Script

Use this flow when presenting the project:

1. Open `http://localhost:3000`.
2. Select an existing borrower, or click **New loan file**.
3. Create a borrower with loan amount, property value, credit score, employment type, and notes.
4. Click **Run agent** before uploading documents.
5. Show missing conditions, readiness score, risk findings, next actions, borrower message, and citations.
6. Upload demo documents.
7. Run the agent again and show how readiness changes.
8. Click **Run evals** and show the score.
9. Switch role to `Underwriter`.
10. Click **Load audit/traces** and show operational reviewability.

## Demo Upload Files

Use the fake borrower documents in `demo_uploads/`:

```text
demo_uploads/emily-carter/appraisal_report.txt
demo_uploads/emily-carter/bank_statement_april.csv
demo_uploads/emily-carter/photo_id.txt
demo_uploads/michael-reynolds/business_tax_return_2024.txt
demo_uploads/michael-reynolds/profit_and_loss_2026_ytd.csv
demo_uploads/michael-reynolds/title_report.txt
demo_uploads/sarah-miller/appraisal_report.txt
demo_uploads/sarah-miller/bonus_income_summary.txt
demo_uploads/sarah-miller/homeowners_insurance.txt
demo_uploads/david-thompson/bank_statement_may.csv
demo_uploads/david-thompson/credit_explanation.txt
demo_uploads/david-thompson/paystub_may.txt
```

## Optional OpenAI

The app works without an OpenAI key. In that mode, it uses deterministic rules and retrieved context to produce stable demo output.

To enable OpenAI borrower-message generation:

```bash
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
```

## Roles

The demo uses lightweight header-based role simulation:

- `processor`: create loans, upload documents, run agent jobs
- `underwriter`: view audit logs and model traces
- `admin`: highest demo role

In the UI, use the role selector in the sidebar. In API calls, pass:

```bash
X-User-Email: underwriter@example.com
X-User-Role: underwriter
```

## API Examples

List loans:

```bash
curl http://localhost:5001/api/loans
```

Create a loan:

```bash
curl -X POST http://localhost:5001/api/loans \
  -H "Content-Type: application/json" \
  -H "X-User-Role: processor" \
  -d '{
    "borrower": {
      "name": "Avery Morgan",
      "email": "avery.morgan@example.com",
      "phone": "313-555-0112",
      "annual_income": 126000,
      "credit_score": 716
    },
    "loan_amount": 365000,
    "property_value": 455000,
    "loan_purpose": "purchase",
    "property_type": "townhome primary residence",
    "employment_type": "W2 salaried",
    "notes": "Borrower wants a 21-day close."
  }'
```

Upload name-only demo documents:

```bash
curl -X POST http://localhost:5001/api/loans/LN-1042/documents \
  -H "Content-Type: application/json" \
  -H "X-User-Role: processor" \
  -d '{"documents":["appraisal_report.txt","photo_id.txt","bank_statement_april.csv"]}'
```

Upload real files:

```bash
curl -X POST http://localhost:5001/api/loans/LN-1042/documents \
  -H "X-User-Role: processor" \
  -F "documents=@demo_uploads/emily-carter/appraisal_report.txt" \
  -F "documents=@demo_uploads/emily-carter/photo_id.txt"
```

Start an async agent run:

```bash
curl -X POST http://localhost:5001/api/agent/run \
  -H "Content-Type: application/json" \
  -H "X-User-Role: processor" \
  -d '{"loan_id":"LN-1042"}'
```

Poll a job:

```bash
curl http://localhost:5001/api/agent/jobs/<job_id>
```

Run evals:

```bash
curl -X POST http://localhost:5001/api/evals/run
```

Read audit logs:

```bash
curl http://localhost:5001/api/audit-logs \
  -H "X-User-Role: underwriter" \
  -H "X-User-Email: underwriter@example.com"
```

Read model traces:

```bash
curl http://localhost:5001/api/model-traces \
  -H "X-User-Role: underwriter" \
  -H "X-User-Email: underwriter@example.com"
```

## Storage Providers

Default storage is local Docker volume storage.

To use S3:

```bash
DOCUMENT_STORAGE_PROVIDER=s3
S3_BUCKET=your-bucket
```

To use GCS:

```bash
DOCUMENT_STORAGE_PROVIDER=gcs
GCS_BUCKET=your-bucket
```

To use Firebase Storage:

```bash
DOCUMENT_STORAGE_PROVIDER=firebase
FIREBASE_BUCKET=your-bucket
```

Cloud credentials are not required for the local demo.

## Evals

The eval dataset lives at:

```text
backend/evals/eval_cases.json
```

The current eval suite checks:

- purchase files ask for appraisal
- self-employed refinance files ask for tax returns
- title report gaps are detected
- high-LTV files receive risk findings
- borrower messages include expected context
- retrieved citations are present

Expected local result:

```text
13/13 passing
```

## Project Structure

```text
backend/
  app/
    agent.py             # Agent workflow, scoring, missing-doc logic
    auth.py              # Header-based role checks
    cloud_storage.py     # Local/S3/GCS/Firebase storage adapters
    database.py          # SQLAlchemy models and DB mapping
    jobs.py              # RQ worker job
    main.py              # Flask API
    observability.py     # Audit logs and model trace writing
    queue.py             # Redis/RQ queue setup
    rag.py               # Lightweight guideline retrieval
    storage.py           # Upload persistence, PDF extraction, OCR hooks
  data/
    agency_guidelines.md
  evals/
    eval_cases.json
    run_evals.py
frontend/
  app/
  components/
  lib/
demo_uploads/
docker-compose.yml
```

## How To Explain It

Short pitch:

> LoanOps AI Agent is an end-to-end mortgage AI workflow. A lender can create a borrower file, upload documents, process an async AI review, identify missing conditions, draft borrower follow-up, and review audit logs/model traces. It uses Next.js, Flask, PostgreSQL, Redis/RQ, Docker, RAG-style retrieval, document parsing, and evals.

Why it is production-minded:

> The agent runs asynchronously, data is persisted in PostgreSQL, uploaded documents go through a storage abstraction, important actions are audited, model runs are traced, and evals guard against regressions.

## Known Tradeoffs

- Auth is intentionally simplified with headers for demo purposes. In production, use real identity providers and session/JWT enforcement.
- Local RAG retrieval is lightweight and inspectable. In production, this could be upgraded to embeddings and a vector database.
- OCR is supported through Tesseract, but production document processing would likely include richer classification, layout extraction, confidence scores, and human review queues.
- Cloud storage adapters are included, but the local demo defaults to Docker volume storage so it can run without credentials.
