"use client";

import { ClipboardCheck, FileSearch, MessageSquareText, Play, ShieldCheck } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import type { AgentRun, LoanFile } from "../lib/api";
import {
  createLoan,
  fetchAuditLogs,
  fetchModelTraces,
  runAgentReview,
  runEvals,
  uploadDocuments
} from "../lib/api";

type Props = {
  loans: LoanFile[];
};

export function LoanWorkspace({ loans }: Props) {
  const [loanFiles, setLoanFiles] = useState(loans);
  const [selectedId, setSelectedId] = useState(loans[0]?.id || "");
  const [agentRun, setAgentRun] = useState<AgentRun | null>(null);
  const [evals, setEvals] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [role, setRole] = useState("processor");
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [traces, setTraces] = useState<any[]>([]);

  const selected = useMemo(
    () => loanFiles.find((loan) => loan.id === selectedId) || loanFiles[0],
    [loanFiles, selectedId]
  );

  async function handleRun() {
    setLoading(true);
    try {
      setAgentRun(await runAgentReview(selected.id));
    } finally {
      setLoading(false);
    }
  }

  async function handleEval() {
    setEvals(await runEvals());
  }

  function changeRole(nextRole: string) {
    setRole(nextRole);
    window.localStorage.setItem("loanops_role", nextRole);
    window.localStorage.setItem("loanops_email", `${nextRole}@example.com`);
  }

  async function loadOpsData() {
    const [audit, tracePayload] = await Promise.all([fetchAuditLogs(), fetchModelTraces()]);
    setAuditLogs(audit.audit_logs || []);
    setTraces(tracePayload.model_traces || []);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setCreating(true);
    try {
      const loan = await createLoan({
        borrower: {
          name: String(form.get("name") || ""),
          email: String(form.get("email") || ""),
          phone: String(form.get("phone") || ""),
          annual_income: Number(form.get("annual_income") || 0),
          credit_score: Number(form.get("credit_score") || 0)
        },
        loan_amount: Number(form.get("loan_amount") || 0),
        property_value: Number(form.get("property_value") || 0),
        loan_purpose: String(form.get("loan_purpose") || "purchase"),
        property_type: String(form.get("property_type") || ""),
        employment_type: String(form.get("employment_type") || ""),
        notes: String(form.get("notes") || "")
      });
      setLoanFiles((current) => [...current, loan]);
      setSelectedId(loan.id);
      setAgentRun(null);
      setShowCreate(false);
      event.currentTarget.reset();
    } finally {
      setCreating(false);
    }
  }

  async function handleUpload(files: FileList | null) {
    if (!files?.length || !selected) {
      return;
    }
    setUploading(true);
    try {
      const updated = await uploadDocuments(selected.id, Array.from(files));
      setLoanFiles((current) => current.map((loan) => (loan.id === updated.id ? updated : loan)));
      setAgentRun(null);
    } finally {
      setUploading(false);
    }
  }

  if (!selected) {
    return <main className="shell">No loan files available.</main>;
  }

  const ltv = selected.property_value > 0 ? selected.loan_amount / selected.property_value : 0;

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={28} />
          <div>
            <span>LoanOps</span>
            <strong>AI Agent</strong>
          </div>
        </div>
        <nav>
          <button className="new-loan" onClick={() => setShowCreate((value) => !value)} type="button">
            {showCreate ? "Close form" : "New loan file"}
          </button>
          {loanFiles.map((loan) => (
            <button
              className={loan.id === selected.id ? "loan active" : "loan"}
              key={loan.id}
              onClick={() => {
                setSelectedId(loan.id);
                setAgentRun(null);
              }}
              type="button"
            >
              <strong>{loan.borrower.name}</strong>
              <span>{loan.id} · {loan.loan_purpose}</span>
            </button>
          ))}
        </nav>
        <button className="eval" onClick={handleEval} type="button">
          <ClipboardCheck size={18} />
          Run evals
        </button>
        <select className="role-select" value={role} onChange={(event) => changeRole(event.target.value)}>
          <option value="processor">Processor</option>
          <option value="underwriter">Underwriter</option>
          <option value="admin">Admin</option>
        </select>
        <button className="eval" onClick={loadOpsData} type="button">
          Load audit/traces
        </button>
        {evals && <p className="eval-score">Eval score {evals.passed}/{evals.total}</p>}
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Forward Deployed Mortgage AI</p>
            <h1>{selected.borrower.name}</h1>
            <span className="muted">{selected.property_type}</span>
          </div>
          <button className="primary" onClick={handleRun} disabled={loading} type="button">
            <Play size={18} />
            {loading ? "Reviewing" : "Run agent"}
          </button>
        </header>

        <section className="metrics">
          <Metric label="Loan amount" value={currency(selected.loan_amount)} />
          <Metric label="Property value" value={currency(selected.property_value)} />
          <Metric label="LTV" value={`${(ltv * 100).toFixed(1)}%`} />
          <Metric label="Credit" value={selected.borrower.credit_score.toString()} />
        </section>

        {showCreate ? (
          <section className="panel create-panel">
            <h2>New borrower loan file</h2>
            <form className="create-form" onSubmit={handleCreate}>
              <input name="name" placeholder="Borrower name" required />
              <input name="email" placeholder="Email" required type="email" />
              <input name="phone" placeholder="Phone" required />
              <input name="annual_income" placeholder="Annual income" required type="number" />
              <input name="credit_score" placeholder="Credit score" required type="number" />
              <input name="loan_amount" placeholder="Loan amount" required type="number" />
              <input name="property_value" placeholder="Property value" required type="number" />
              <select name="loan_purpose">
                <option value="purchase">Purchase</option>
                <option value="refinance">Refinance</option>
              </select>
              <input name="property_type" placeholder="Property type" defaultValue="single-family primary residence" />
              <select name="employment_type">
                <option value="W2 salaried">W2 salaried</option>
                <option value="self-employed">Self-employed</option>
              </select>
              <textarea name="notes" placeholder="Loan notes, timeline, edge cases" />
              <button className="primary" disabled={creating} type="submit">
                {creating ? "Creating" : "Create loan file"}
              </button>
            </form>
          </section>
        ) : null}

        <section className="grid">
          <div className="panel span-2">
            <div className="panel-title">
              <FileSearch size={20} />
              <h2>Loan file</h2>
            </div>
            <div className="detail-grid">
              <Detail label="Purpose" value={selected.loan_purpose} />
              <Detail label="Employment" value={selected.employment_type} />
              <Detail label="Income" value={currency(selected.borrower.annual_income)} />
              <Detail label="Contact" value={selected.borrower.email} />
            </div>
            <div className="documents">
              {selected.uploaded_documents.map((doc) => (
                <span key={doc}>{doc}</span>
              ))}
            </div>
            {selected.document_records?.length ? (
              <div className="records">
                {selected.document_records.map((record) => (
                  <article key={`${record.filename}-${record.size_bytes}`}>
                    <strong>{record.filename}</strong>
                    <span>
                      {record.storage_provider} · {record.content_type} · {formatBytes(record.size_bytes)}
                    </span>
                    {record.extracted_text && <p>{record.extracted_text}</p>}
                  </article>
                ))}
              </div>
            ) : null}
            <label className="upload">
              <input
                multiple
                onChange={(event) => handleUpload(event.target.files)}
                type="file"
              />
              {uploading ? "Uploading..." : "Upload borrower documents"}
            </label>
            <p className="note">{selected.notes}</p>
          </div>

          <div className="panel">
            <h2>Readiness</h2>
            {agentRun ? (
              <>
                <div className="score">{agentRun.readiness_score}</div>
                <p className="status">{agentRun.status.replaceAll("_", " ")}</p>
              </>
            ) : (
              <p className="empty">Run the agent to score file readiness.</p>
            )}
          </div>

          <div className="panel">
            <h2>Missing conditions</h2>
            {agentRun ? (
              <ul className="compact">
                {agentRun.missing_documents.map((doc) => <li key={doc}>{doc}</li>)}
              </ul>
            ) : (
              <p className="empty">Conditions appear after agent review.</p>
            )}
          </div>

          <div className="panel span-2">
            <h2>Findings</h2>
            {agentRun ? (
              <div className="findings">
                {agentRun.findings.map((finding) => (
                  <article key={finding.label} className={`finding ${finding.severity}`}>
                    <strong>{finding.label}</strong>
                    <span>{finding.severity}</span>
                    <p>{finding.detail}</p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="empty">No findings yet.</p>
            )}
          </div>

          <div className="panel">
            <h2>Next actions</h2>
            {agentRun ? (
              <ul className="compact">
                {agentRun.next_best_actions.map((action) => <li key={action}>{action}</li>)}
              </ul>
            ) : (
              <p className="empty">Run the agent for action routing.</p>
            )}
          </div>

          <div className="panel span-2">
            <div className="panel-title">
              <MessageSquareText size={20} />
              <h2>Borrower message</h2>
            </div>
            <p className="message">{agentRun?.borrower_message || "Run the agent to draft a borrower-ready follow-up."}</p>
          </div>

          <div className="panel">
            <h2>RAG citations</h2>
            {agentRun ? (
              <div className="citations">
                {agentRun.citations.map((citation) => (
                  <article key={citation.id}>
                    <strong>{citation.source}</strong>
                    <span>score {citation.score}</span>
                    <p>{citation.text}</p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="empty">Grounding sources appear here.</p>
            )}
          </div>

          <div className="panel span-2">
            <h2>Audit logs</h2>
            {auditLogs.length ? (
              <div className="ops-list">
                {auditLogs.slice(0, 6).map((log) => (
                  <article key={log.id}>
                    <strong>{log.action}</strong>
                    <span>{log.actor_email} · {log.entity_type} {log.entity_id}</span>
                  </article>
                ))}
              </div>
            ) : (
              <p className="empty">Switch to underwriter/admin and load audit logs.</p>
            )}
          </div>

          <div className="panel">
            <h2>Model traces</h2>
            {traces.length ? (
              <div className="ops-list">
                {traces.slice(0, 4).map((trace) => (
                  <article key={trace.id}>
                    <strong>{trace.model}</strong>
                    <span>{trace.loan_id} · {trace.output_summary}</span>
                  </article>
                ))}
              </div>
            ) : (
              <p className="empty">Async agent traces appear here.</p>
            )}
          </div>
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="label">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function currency(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

function formatBytes(value: number) {
  if (!value) {
    return "name only";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  return `${(value / 1024).toFixed(1)} KB`;
}
