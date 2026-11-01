import type { AuditEvent, FieldChange } from "../../types/api";
import { formatDateTime, humanize } from "../../utils/format";
import { ChangeTable } from "./VersionHistory";

function describe(e: AuditEvent): string | null {
  const d = e.details ?? {};
  switch (e.action) {
    case "CONTRACT_UPLOADED":
    case "CONTRACT_DELETED":
      return `${d.document_type}: ${d.file_name}`;
    case "APPROVAL_ASSIGNED":
      return `Assigned to ${d.approver}`;
    case "NEW_VERSION_CREATED":
      return `Draft created from approved v${d.based_on_version}`;
    case "VERSION_ACTIVATED":
      return d.previous_active_version ? `Replaces v${d.previous_active_version} as the active version` : "Now the active version";
    default:
      return null;
  }
}

export function AuditTrail({ events }: { events: AuditEvent[] }) {
  if (!events.length) return <p className="muted">No audit events.</p>;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>#</th>
            <th>Timestamp</th>
            <th>User</th>
            <th>Action</th>
            <th>Version</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {events.map((e) => {
            const changes = (e.details?.changes as FieldChange[] | undefined) ?? [];
            const summary = describe(e);
            return (
              <tr key={e.id}>
                <td data-label="Event ID" className="muted">{e.id}</td>
                <td data-label="Timestamp">{formatDateTime(e.created_at)}</td>
                <td data-label="User">{e.user.full_name}</td>
                <td data-label="Action"><span className={`audit-action audit-${e.action.toLowerCase()}`}>{humanize(e.action)}</span></td>
                <td data-label="Version">{e.version_number ? `v${e.version_number}` : "—"}</td>
                <td data-label="Details">
                  {summary && <div>{summary}</div>}
                  {e.comment && <div className="pre">“{e.comment}”</div>}
                  {changes.length > 0 && (
                    <details>
                      <summary>{changes.length} field{changes.length > 1 ? "s" : ""} changed</summary>
                      <ChangeTable changes={changes} />
                    </details>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
