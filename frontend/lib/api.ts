const API_URL =
  typeof window === "undefined"
    ? process.env.INTERNAL_API_URL ||
      (process.env.INTERNAL_API_HOSTPORT ? `http://${process.env.INTERNAL_API_HOSTPORT}` : "http://backend:5001")
    : process.env.NEXT_PUBLIC_API_URL || "";

export type LoanFile = {
  id: string;
  borrower: {
    name: string;
    email: string;
    phone: string;
    annual_income: number;
    credit_score: number;
  };
  loan_amount: number;
  property_value: number;
  loan_purpose: string;
  property_type: string;
  employment_type: string;
  uploaded_documents: string[];
  document_records: Array<{
    filename: string;
    stored_path: string;
    storage_provider: string;
    content_type: string;
    size_bytes: number;
    extracted_text: string;
  }>;
  notes: string;
};

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") {
    return {};
  }
  return {
    "X-User-Email": window.localStorage.getItem("loanops_email") || "processor@example.com",
    "X-User-Role": window.localStorage.getItem("loanops_role") || "processor"
  };
}

export type AgentRun = {
  loan_id: string;
  readiness_score: number;
  status: string;
  findings: Array<{
    label: string;
    severity: string;
    detail: string;
    evidence: string[];
  }>;
  missing_documents: string[];
  borrower_message: string;
  next_best_actions: string[];
  citations: Array<{
    id: string;
    source: string;
    text: string;
    score: number;
  }>;
};

export type AgentJob = {
  job_id: string;
  loan_id?: string;
  status: string;
  result?: AgentRun;
  error?: string;
};

export async function fetchLoans(): Promise<LoanFile[]> {
  const response = await fetch(`${API_URL}/api/loans`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Unable to load loan files");
  }
  const payload = await response.json();
  return payload.loans;
}

export async function runAgentReview(loanId: string): Promise<AgentRun> {
  const response = await fetch(`${API_URL}/api/agent/run?sync=1`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ loan_id: loanId })
  });
  if (!response.ok) {
    throw new Error("Agent run failed");
  }
  return response.json();
}

export async function fetchAgentJob(jobId: string): Promise<AgentJob> {
  const response = await fetch(`${API_URL}/api/agent/jobs/${jobId}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Agent job lookup failed");
  }
  return response.json();
}

export type CreateLoanPayload = {
  borrower: {
    name: string;
    email: string;
    phone: string;
    annual_income: number;
    credit_score: number;
  };
  loan_amount: number;
  property_value: number;
  loan_purpose: string;
  property_type: string;
  employment_type: string;
  notes: string;
};

export async function createLoan(payload: CreateLoanPayload): Promise<LoanFile> {
  const response = await fetch(`${API_URL}/api/loans`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error("Loan creation failed");
  }
  return response.json();
}

export async function uploadDocuments(loanId: string, files: File[]): Promise<LoanFile> {
  const body = new FormData();
  files.forEach((file) => body.append("documents", file));
  const response = await fetch(`${API_URL}/api/loans/${loanId}/documents`, {
    method: "POST",
    headers: authHeaders(),
    body
  });
  if (!response.ok) {
    throw new Error("Document upload failed");
  }
  const payload = await response.json();
  return payload.loan;
}

export async function runEvals() {
  const response = await fetch(`${API_URL}/api/evals/run`, { method: "POST" });
  if (!response.ok) {
    throw new Error("Eval run failed");
  }
  return response.json();
}

export async function fetchAuditLogs() {
  const response = await fetch(`${API_URL}/api/audit-logs`, { headers: authHeaders(), cache: "no-store" });
  if (!response.ok) {
    throw new Error("Audit log lookup failed");
  }
  return response.json();
}

export async function fetchModelTraces() {
  const response = await fetch(`${API_URL}/api/model-traces`, { headers: authHeaders(), cache: "no-store" });
  if (!response.ok) {
    throw new Error("Model trace lookup failed");
  }
  return response.json();
}
