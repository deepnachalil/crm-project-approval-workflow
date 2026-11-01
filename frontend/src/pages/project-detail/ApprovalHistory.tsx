import { StatusBadge } from "../../components/StatusBadge";
import type { ApprovalRecord } from "../../types/api";
import { formatDateTime } from "../../utils/format";

const KIND_LABEL = { SUBMISSION: "Submission note", APPROVAL: "Approval comment", REJECTION: "Rejection reason" } as const;

export function ApprovalHistory({ approvals }: { approvals: ApprovalRecord[] }) {
  if (!approvals.length) return <p className="muted">This project has not been submitted for approval yet.</p>;
  return (
    <ol className="timeline">
      {approvals.map((a) => (
        <li key={a.id} className="timeline-item">
          <div>
            <strong>v{a.version_number}</strong> {a.is_resubmission ? "resubmitted" : "submitted"} by {a.submitted_by.full_name} on{" "}
            {formatDateTime(a.submitted_at)} → assigned to {a.approver.full_name} <StatusBadge status={a.status} />
          </div>
          {a.decided_at && (
            <div className="muted small">
              Decision by {a.decided_by?.full_name} on {formatDateTime(a.decided_at)}
            </div>
          )}
          {a.comments.map((c) => (
            <blockquote key={c.id} className={`comment comment-${c.kind.toLowerCase()}`}>
              <div className="small muted">{KIND_LABEL[c.kind]} · {c.author.full_name}</div>
              <div className="pre">{c.comment}</div>
            </blockquote>
          ))}
        </li>
      ))}
    </ol>
  );
}
