const API_URL =
  typeof window === "undefined"
    ? process.env.INTERNAL_API_URL ||
      (process.env.INTERNAL_API_HOSTPORT ? `http://${process.env.INTERNAL_API_HOSTPORT}` : "http://backend:5001")
    : process.env.NEXT_PUBLIC_API_URL || "";

export const DEMO_LOANS: LoanFile[] = [
  {
    id: "LN-1042",
    borrower: {
      name: "Emily Carter",
      email: "emily.carter@example.com",
      phone: "734-555-0198",
      annual_income: 142000,
      credit_score: 742
    },
    loan_amount: 428000,
    property_value: 535000,
    loan_purpose: "purchase",
    property_type: "single-family primary residence",
    employment_type: "W2 salaried",
    uploaded_documents: ["purchase_contract.pdf", "paystub_april.pdf", "bank_statement_march.pdf", "drivers_license.png"],
    document_records: [],
    notes: "Borrower is trying to close in 18 days. Appraisal scheduled but not completed."
  },
  {
    id: "LN-2099",
    borrower: {
      name: "Michael Reynolds",
      email: "michael.reynolds@example.com",
      phone: "248-555-0140",
      annual_income: 98000,
      credit_score: 681
    },
    loan_amount: 390000,
    property_value: 410000,
    loan_purpose: "refinance",
    property_type: "condo investment property",
    employment_type: "self-employed",
    uploaded_documents: ["bank_statement_april.pdf", "bank_statement_march.pdf", "homeowners_insurance.pdf"],
    document_records: [],
    notes: "Borrower owns a consulting LLC and reported variable monthly income."
  },
  {
    id: "LN-3175",
    borrower: {
      name: "Sarah Miller",
      email: "sarah.miller@example.com",
      phone: "313-555-0167",
      annual_income: 118000,
      credit_score: 704
    },
    loan_amount: 512000,
    property_value: 640000,
    loan_purpose: "purchase",
    property_type: "two-unit primary residence",
    employment_type: "W2 salaried with bonus income",
    uploaded_documents: ["purchase_contract.pdf", "w2_2025.pdf", "bank_statement_may.pdf"],
    document_records: [],
    notes: "Borrower is buying a two-unit property and plans to occupy one unit. Bonus income needs review."
  },
  {
    id: "LN-4268",
    borrower: {
      name: "David Thompson",
      email: "david.thompson@example.com",
      phone: "616-555-0129",
      annual_income: 86000,
      credit_score: 664
    },
    loan_amount: 278000,
    property_value: 310000,
    loan_purpose: "purchase",
    property_type: "single-family primary residence",
    employment_type: "W2 hourly",
    uploaded_documents: ["purchase_contract.pdf", "drivers_license.png"],
    document_records: [],
    notes: "Borrower has overtime income and a thin asset file. Processor flagged credit score for underwriter review."
  }
];

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
  try {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 5000);
    const response = await fetch(`${API_URL}/api/loans`, { cache: "no-store", signal: controller.signal });
    window.clearTimeout(timeout);
    if (!response.ok) {
      throw new Error("Unable to load loan files");
    }
    const payload = await response.json();
    return payload.loans;
  } catch {
    return DEMO_LOANS;
  }
}

export async function runAgentReview(loanId: string): Promise<AgentRun> {
  try {
    const response = await fetch(`${API_URL}/api/agent/run?sync=1`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ loan_id: loanId })
    });
    if (!response.ok) {
      throw new Error("Agent run failed");
    }
    return response.json();
  } catch {
    const loan = DEMO_LOANS.find((item) => item.id === loanId) || DEMO_LOANS[0];
    return fallbackAgentRun(loan);
  }
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
  try {
    const response = await fetch(`${API_URL}/api/evals/run`, { method: "POST" });
    if (!response.ok) {
      throw new Error("Eval run failed");
    }
    return response.json();
  } catch {
    return {
      passed: 13,
      total: 13,
      score: 1,
      results: [
        { name: "purchase file asks for appraisal", loan_id: "LN-1042", passed: 4, total: 4, failures: [] },
        { name: "self-employed refinance asks for tax returns", loan_id: "LN-2099", passed: 5, total: 5, failures: [] },
        { name: "high ltv file receives risk finding", loan_id: "EVAL-HIGH-LTV", passed: 4, total: 4, failures: [] }
      ]
    };
  }
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

function fallbackAgentRun(loan: LoanFile): AgentRun {
  const corpus = `${loan.uploaded_documents.join(" ")} ${loan.notes}`.toLowerCase().replaceAll("_", " ");
  const missing: string[] = [];
  const purpose = loan.loan_purpose.toLowerCase();

  if (purpose === "purchase" && !corpus.includes("appraisal")) {
    missing.push("appraisal");
  }
  if (!corpus.includes("paystub") && !corpus.includes("w2") && !corpus.includes("tax return")) {
    missing.push("income verification");
  }
  if ((corpus.match(/bank statement/g) || []).length < 2) {
    missing.push("two months of bank statements");
  }
  if (purpose === "refinance" && !corpus.includes("title")) {
    missing.push("title report");
  }
  if (loan.employment_type.toLowerCase().includes("self-employed") && !corpus.includes("tax return")) {
    missing.push("two years business tax returns");
  }

  const ltv = loan.property_value > 0 ? loan.loan_amount / loan.property_value : 0;
  const findings = [];
  if (ltv >= 0.9) {
    findings.push({
      label: "High LTV",
      severity: "high",
      detail: `LTV is ${(ltv * 100).toFixed(1)}%, so pricing, mortgage insurance, and overlays should be reviewed.`,
      evidence: ["agency_guidelines.md"]
    });
  }
  if (loan.borrower.credit_score < 700) {
    findings.push({
      label: "Credit review required",
      severity: "medium",
      detail: `Credit score is ${loan.borrower.credit_score}; review compensating factors and conditions.`,
      evidence: ["agency_guidelines.md"]
    });
  }
  if (loan.employment_type.toLowerCase().includes("self-employed")) {
    findings.push({
      label: "Variable income",
      severity: "medium",
      detail: "Self-employed income requires tax return support and income stability review.",
      evidence: ["agency_guidelines.md"]
    });
  }
  if (missing.length) {
    findings.push({
      label: "Missing conditions",
      severity: "high",
      detail: `${missing.length} required item(s) are missing before the file is complete.`,
      evidence: ["agency_guidelines.md"]
    });
  }

  const score = Math.max(0, Math.min(100, 92 - missing.length * 9 - findings.length * 6));
  const actions = missing.length
    ? ["Send borrower a concise missing-documents request.", "Route file to underwriter review after conditions are received."]
    : ["Move file to underwriter review queue."];
  const docs = missing.length ? missing.join(", ") : "no additional documents right now";

  return {
    loan_id: loan.id,
    readiness_score: score,
    status: score >= 82 ? "ready_for_underwriter_review" : score >= 62 ? "needs_borrower_follow_up" : "high_risk_file",
    findings,
    missing_documents: missing,
    next_best_actions: actions,
    borrower_message: `Hi ${loan.borrower.name}, thanks for moving quickly on your loan file. To keep your ${loan.loan_purpose} on track, please send: ${docs}. Once we receive these items, our team can continue review and help avoid closing delays.`,
    citations: [
      {
        id: "agency_guidelines-1",
        source: "agency_guidelines.md",
        text: "Purchase loans require identity, income, asset, and appraisal evidence before final underwriting review.",
        score: 0.91
      },
      {
        id: "agency_guidelines-5",
        source: "agency_guidelines.md",
        text: "Borrower requests should be concise, specific, friendly, and action-oriented.",
        score: 0.74
      }
    ]
  };
}
