import { useState } from "react";
import { Link } from "react-router-dom";
import { catalogApi, clientsApi, projectsApi, type ProjectFilters } from "../api";
import { useAuth } from "../auth/AuthContext";
import { ErrorAlert, Loading } from "../components/Feedback";
import { ActiveBadge, StatusBadge, statusLabel } from "../components/StatusBadge";
import { useAsync } from "../hooks/useAsync";
import { useDebounced } from "../hooks/useDebounced";
import type { VersionStatus } from "../types/api";
import { formatDateTime } from "../utils/format";

const STATUSES: VersionStatus[] = ["DRAFT", "PENDING_APPROVAL", "REJECTED", "APPROVED"];

export function ProjectListPage() {
  const { hasRole } = useAuth();
  const [filters, setFilters] = useState<ProjectFilters>({ status: "", client_id: "", created_by: "", search: "" });
  const search = useDebounced(filters.search);
  const projects = useAsync(
    () => projectsApi.list({ ...filters, search }),
    [filters.status, filters.client_id, filters.created_by, search],
  );
  const lookups = useAsync(() => Promise.all([clientsApi.list(), catalogApi.users("CRM")]), []);
  const [clients, creators] = lookups.data ?? [[], []];

  const set = <K extends keyof ProjectFilters>(key: K, value: ProjectFilters[K]) => setFilters((f) => ({ ...f, [key]: value }));
  const filtered = Object.values(filters).some((v) => v !== "");

  return (
    <section>
      <div className="page-header">
        <h1>Projects</h1>
        {hasRole("CRM") && (
          <Link to="/projects/new" className="btn btn-primary">+ New Project</Link>
        )}
      </div>

      <div className="card filters">
        <label>
          Search
          <input placeholder="Project ID or name" value={filters.search} onChange={(e) => set("search", e.target.value)} />
        </label>
        <label>
          Status
          <select value={filters.status} onChange={(e) => set("status", e.target.value as VersionStatus | "")}>
            <option value="">All statuses</option>
            {STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
          </select>
        </label>
        <label>
          Client
          <select value={filters.client_id} onChange={(e) => set("client_id", e.target.value ? Number(e.target.value) : "")}>
            <option value="">All clients</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.legal_entity_name}</option>)}
          </select>
        </label>
        <label>
          Created by
          <select value={filters.created_by} onChange={(e) => set("created_by", e.target.value ? Number(e.target.value) : "")}>
            <option value="">Anyone</option>
            {creators.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
          </select>
        </label>
        {filtered && (
          <button className="btn btn-link" onClick={() => setFilters({ status: "", client_id: "", created_by: "", search: "" })}>
            Clear filters
          </button>
        )}
      </div>

      <ErrorAlert error={projects.error} />
      {projects.loading && !projects.data ? (
        <Loading />
      ) : (
        <div className="card table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Project ID</th>
                <th>Project Name</th>
                <th>Client</th>
                <th>Status</th>
                <th>Current Version</th>
                <th>Created By</th>
                <th>Last Updated</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {projects.data?.length === 0 && (
                <tr><td colSpan={8} className="empty">{filtered ? "No projects match these filters." : "No projects yet."}</td></tr>
              )}
              {projects.data?.map((p) => (
                <tr key={p.id}>
                  <td data-label="Project ID"><Link to={`/projects/${p.id}`}>{p.project_code}</Link></td>
                  <td data-label="Name">{p.name}</td>
                  <td data-label="Client">{p.client?.legal_entity_name ?? "—"}</td>
                  <td data-label="Status"><StatusBadge status={p.status} /></td>
                  <td data-label="Version">
                    v{p.current_version_number}{" "}
                    {p.active_version_number === p.current_version_number ? (
                      <ActiveBadge />
                    ) : (
                      p.active_version_number && <span className="muted small">(active: v{p.active_version_number})</span>
                    )}
                  </td>
                  <td data-label="Created By">{p.created_by.full_name}</td>
                  <td data-label="Updated">{formatDateTime(p.updated_at)}</td>
                  <td className="actions">
                    <Link to={`/projects/${p.id}`} className="btn btn-sm">View</Link>
                    {p.can_edit && <Link to={`/projects/${p.id}/edit`} className="btn btn-sm">Edit</Link>}
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
