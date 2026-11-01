import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { projectsApi } from "../api";
import { Alert, ErrorAlert, Loading } from "../components/Feedback";
import { ActiveBadge, StatusBadge } from "../components/StatusBadge";
import { Tabs } from "../components/Tabs";
import { useAsync } from "../hooks/useAsync";
import type { ProjectAction, ProjectDetail, ProjectVersion } from "../types/api";
import { formatDateTime } from "../utils/format";
import { ActionModal, type WorkflowAction } from "./project-detail/ActionModal";
import { ApprovalHistory } from "./project-detail/ApprovalHistory";
import { AuditTrail } from "./project-detail/AuditTrail";
import { VersionHistory } from "./project-detail/VersionHistory";
import { VersionView } from "./project-detail/VersionView";

type DetailTab = "config" | "versions" | "approvals" | "audit";

const DONE_MESSAGES: Record<WorkflowAction, string> = {
  submit: "Project submitted for approval.",
  resubmit: "Project resubmitted for approval.",
  approve: "Project approved. This version is now active.",
  reject: "Project rejected. The CRM can now correct and resubmit it.",
};

export function ProjectDetailPage() {
  const projectId = Number(useParams().id);
  const [searchParams] = useSearchParams();
  const project = useAsync(() => projectsApi.get(projectId), [projectId]);
  const [tab, setTab] = useState<DetailTab>("config");
  const [viewing, setViewing] = useState<number | null>(null); // version number shown in the config tab
  const [historyVersion, setHistoryVersion] = useState<ProjectVersion | null>(null);
  const [action, setAction] = useState<WorkflowAction | null>(null);
  const [notice, setNotice] = useState<string | null>(searchParams.get("submitted") ? DONE_MESSAGES.submit : null);

  // Secondary data is loaded when its tab is opened and refreshed whenever the project changes.
  const updatedAt = project.data?.updated_at;
  const versions = useAsync(() => (tab === "versions" ? projectsApi.versions(projectId) : Promise.resolve(undefined)), [tab, updatedAt]);
  const approvals = useAsync(() => (tab === "approvals" ? projectsApi.approvals(projectId) : Promise.resolve(undefined)), [tab, updatedAt]);
  const audit = useAsync(() => (tab === "audit" ? projectsApi.audit(projectId) : Promise.resolve(undefined)), [tab, updatedAt]);

  const p = project.data;
  const current = p?.current_version;
  const active = p?.active_version;

  useEffect(() => {
    if (!p || viewing === null || viewing === current?.version_number || viewing === active?.version_number) {
      setHistoryVersion(null);
      return;
    }
    projectsApi.version(projectId, viewing).then(setHistoryVersion).catch(() => setHistoryVersion(null));
  }, [p, viewing, projectId, current?.version_number, active?.version_number]);

  if (project.loading && !p) return <Loading />;
  if (project.error || !p || !current) return <ErrorAlert error={project.error} />;

  const shown: ProjectVersion =
    viewing === null || viewing === current.version_number
      ? current
      : viewing === active?.version_number
        ? active
        : (historyVersion ?? current);
  const can = (a: ProjectAction) => p.allowed_actions.includes(a);
  const decision = current.last_decision;

  function onDone(updated: ProjectDetail, done: WorkflowAction) {
    project.setData(updated);
    setAction(null);
    setViewing(null);
    setNotice(DONE_MESSAGES[done]);
  }

  return (
    <section>
      <div className="page-header">
        <div>
          <div className="muted small"><Link to="/projects">Projects</Link> / {p.project_code}</div>
          <h1>
            {current.name} <StatusBadge status={p.status} />
          </h1>
          <p className="muted">
            {p.project_code} · Current version v{current.version_number}
            {active ? ` · Active version v${active.version_number}` : " · No active version yet"} · Created by {p.created_by.full_name} ·
            Updated {formatDateTime(p.updated_at)}
          </p>
        </div>
        <div className="inline-actions">
          {can("edit") && <Link to={`/projects/${p.id}/edit`} className="btn">{p.status === "APPROVED" ? "Update (new version)" : "Edit"}</Link>}
          {can("submit") && <button className="btn btn-primary" onClick={() => setAction("submit")}>Submit for Approval</button>}
          {can("resubmit") && <button className="btn btn-primary" onClick={() => setAction("resubmit")}>Resubmit</button>}
          {can("approve") && <button className="btn btn-primary" onClick={() => setAction("approve")}>Approve</button>}
          {can("reject") && <button className="btn btn-danger" onClick={() => setAction("reject")}>Reject</button>}
        </div>
      </div>

      {notice && <Alert kind="success">{notice}</Alert>}
      {p.status === "REJECTED" && decision?.comment && (
        <Alert kind="error" title={`Rejected by ${decision.decided_by?.full_name} on ${formatDateTime(decision.decided_at)}`}>
          <p className="pre">{decision.comment}</p>
        </Alert>
      )}
      {p.status === "PENDING_APPROVAL" && decision && (
        <Alert kind="info" title="Awaiting approval">
          Submitted by {decision.submitted_by.full_name} on {formatDateTime(decision.submitted_at)}; assigned to {decision.approver.full_name}.
          {active && active.id !== current.id && ` Version v${active.version_number} remains active until this version is approved.`}
        </Alert>
      )}
      {p.status === "APPROVED" && decision?.decided_by && (
        <Alert kind="success" title={`Approved by ${decision.decided_by.full_name} on ${formatDateTime(decision.decided_at)}`}>
          {decision.comment && <p className="pre">{decision.comment}</p>}
        </Alert>
      )}

      <div className="card">
        <Tabs
          active={tab}
          onChange={setTab}
          tabs={[
            { key: "config", label: "Configuration" },
            { key: "versions", label: "Version History", badge: current.version_number },
            { key: "approvals", label: "Approval History" },
            { key: "audit", label: "Audit Trail" },
          ]}
        />
        <div className="tab-panel">
          {tab === "config" && (
            <>
              {(active && active.id !== current.id) || current.version_number > 1 ? (
                <div className="version-switch">
                  <span>Showing:</span>
                  <button className={`btn btn-sm${shown.id === current.id ? " btn-selected" : ""}`} onClick={() => setViewing(null)}>
                    Current (v{current.version_number})
                  </button>
                  {active && active.id !== current.id && (
                    <button className={`btn btn-sm${shown.id === active.id ? " btn-selected" : ""}`} onClick={() => setViewing(active.version_number)}>
                      Active (v{active.version_number}) <ActiveBadge />
                    </button>
                  )}
                  {shown.id !== current.id && shown.id !== active?.id && <span className="muted">v{shown.version_number} (historical)</span>}
                </div>
              ) : null}
              <VersionView projectCode={p.project_code} version={shown} />
            </>
          )}
          {tab === "versions" &&
            (versions.loading ? <Loading /> : versions.error ? <ErrorAlert error={versions.error} /> : (
              <VersionHistory versions={versions.data ?? []} onView={(n) => { setViewing(n); setTab("config"); }} />
            ))}
          {tab === "approvals" &&
            (approvals.loading ? <Loading /> : approvals.error ? <ErrorAlert error={approvals.error} /> : <ApprovalHistory approvals={approvals.data ?? []} />)}
          {tab === "audit" && (audit.loading ? <Loading /> : audit.error ? <ErrorAlert error={audit.error} /> : <AuditTrail events={audit.data ?? []} />)}
        </div>
      </div>

      {action && <ActionModal action={action} project={p} onClose={() => setAction(null)} onDone={(u) => onDone(u, action)} />}
    </section>
  );
}
