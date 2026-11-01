import { ClientDetails } from "../../components/ClientDetails";
import { ContractTable } from "../../components/ContractTable";
import { ActiveBadge, StatusBadge } from "../../components/StatusBadge";
import type { ProjectVersion } from "../../types/api";
import { formatDate, formatDateTime } from "../../utils/format";

/** Read-only view of a project version's complete configuration. */
export function VersionView({ projectCode, version }: { projectCode: string; version: ProjectVersion }) {
  return (
    <div className="version-view">
      <div className="version-meta">
        <strong>Version v{version.version_number}</strong> <StatusBadge status={version.status} /> {version.is_active && <ActiveBadge />}
        <span className="muted small">
          {" "}· created by {version.created_by.full_name} on {formatDateTime(version.created_at)}
          {version.based_on_version_number && ` · based on v${version.based_on_version_number}`}
        </span>
      </div>

      <h3>Basic Information</h3>
      <dl className="details-grid">
        <dt>Project ID</dt><dd>{projectCode}</dd>
        <dt>Project Name</dt><dd>{version.name}</dd>
        <dt>Start Date</dt><dd>{formatDate(version.start_date)}</dd>
        <dt>End Date</dt><dd>{formatDate(version.end_date)}</dd>
        <dt>CRM / Creator</dt><dd>{version.crm_user.full_name}</dd>
        <dt>Business Unit</dt><dd>{version.business_unit ?? "—"}</dd>
        <dt>Reviewer / Approver</dt><dd>{version.approver?.full_name ?? "—"}</dd>
      </dl>

      <h3>Client</h3>
      {version.client ? <ClientDetails client={version.client} /> : <p className="muted">No client selected.</p>}

      <h3>Contracts</h3>
      <ContractTable contracts={version.contracts} />

      <h3>Job Categories &amp; Rate Cards</h3>
      {version.job_categories.length ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Job Category</th><th>Rate Card</th><th>Currency</th></tr>
            </thead>
            <tbody>
              {version.job_categories.map((jc) => (
                <tr key={jc.id}>
                  <td data-label="Job Category">{jc.name}</td>
                  <td data-label="Rate Card">{jc.rate_card?.name ?? <span className="error-text">Not mapped</span>}</td>
                  <td data-label="Currency">{jc.rate_card?.currency ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">No job categories defined.</p>
      )}
    </div>
  );
}
