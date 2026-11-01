import { Link } from "react-router-dom";
import { approvalsApi } from "../api";
import { ErrorAlert, Loading } from "../components/Feedback";
import { useAsync } from "../hooks/useAsync";
import { formatDateTime } from "../utils/format";

export function ApprovalsPage() {
  const pending = useAsync(() => approvalsApi.pending(), []);

  return (
    <section>
      <div className="page-header">
        <h1>Pending Approvals</h1>
        <button className="btn" onClick={() => pending.reload()}>Refresh</button>
      </div>
      <ErrorAlert error={pending.error} />
      {pending.loading && !pending.data ? (
        <Loading />
      ) : (
        <div className="card table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Project ID</th>
                <th>Project Name</th>
                <th>Client</th>
                <th>Version</th>
                <th>Submitted By</th>
                <th>Submitted</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {pending.data?.length === 0 && <tr><td colSpan={7} className="empty">Nothing waiting for your review.</td></tr>}
              {pending.data?.map((a) => (
                <tr key={a.approval_id}>
                  <td data-label="Project ID">{a.project.project_code}</td>
                  <td data-label="Name">{a.project.name}</td>
                  <td data-label="Client">{a.project.client?.legal_entity_name ?? "—"}</td>
                  <td data-label="Version">
                    v{a.version_number}
                    {a.is_resubmission && <span className="badge badge-resubmitted">Resubmitted</span>}
                    {a.project.active_version_number && <span className="badge badge-update">Update · active v{a.project.active_version_number}</span>}
                  </td>
                  <td data-label="Submitted By">{a.submitted_by.full_name}</td>
                  <td data-label="Submitted">{formatDateTime(a.submitted_at)}</td>
                  <td className="actions">
                    <Link to={`/projects/${a.project.id}`} className="btn btn-sm btn-primary">Review</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
