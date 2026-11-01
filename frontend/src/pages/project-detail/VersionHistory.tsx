import { ActiveBadge, StatusBadge } from "../../components/StatusBadge";
import type { FieldChange, VersionSummary } from "../../types/api";
import { formatDateTime } from "../../utils/format";

function ChangeValue({ value }: { value: FieldChange["old"] }) {
  if (value === null || value === undefined || value === "") return <span className="muted">—</span>;
  if (Array.isArray(value)) {
    return value.length ? <ul className="plain-list">{value.map((v) => <li key={v}>{v}</li>)}</ul> : <span className="muted">none</span>;
  }
  return <>{value}</>;
}

export function ChangeTable({ changes }: { changes: FieldChange[] }) {
  if (!changes.length) return <p className="muted small">No configuration changes.</p>;
  return (
    <table className="table table-compact">
      <thead>
        <tr><th>Field</th><th>Before</th><th>After</th></tr>
      </thead>
      <tbody>
        {changes.map((c) => (
          <tr key={c.field}>
            <td data-label="Field">{c.label}</td>
            <td data-label="Before"><ChangeValue value={c.old} /></td>
            <td data-label="After"><ChangeValue value={c.new} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function VersionHistory({ versions, onView }: { versions: VersionSummary[]; onView: (n: number) => void }) {
  return (
    <ol className="timeline">
      {versions.map((v) => (
        <li key={v.id} className="timeline-item">
          <div className="row-between">
            <div>
              <strong>v{v.version_number}</strong> <StatusBadge status={v.status} /> {v.is_active && <ActiveBadge />}
              <div className="muted small">
                Created by {v.created_by.full_name} · {formatDateTime(v.created_at)}
                {v.last_decision?.decided_at &&
                  ` · ${v.last_decision.status === "APPROVED" ? "approved" : "rejected"} by ${v.last_decision.decided_by?.full_name} on ${formatDateTime(v.last_decision.decided_at)}`}
              </div>
            </div>
            <button type="button" className="btn btn-sm" onClick={() => onView(v.version_number)}>View configuration</button>
          </div>
          {v.based_on_version_number ? (
            <details>
              <summary>Changes from v{v.based_on_version_number} ({v.changes.length})</summary>
              <ChangeTable changes={v.changes} />
            </details>
          ) : (
            <p className="muted small">Initial version.</p>
          )}
        </li>
      ))}
    </ol>
  );
}
