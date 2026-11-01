import type { ReactNode } from "react";
import { ApiError } from "../api/http";
import type { Issue } from "../types/api";

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div className="loading" role="status">{label}</div>;
}

export function Alert({ kind = "info", title, children }: { kind?: "info" | "success" | "warning" | "error"; title?: string; children?: ReactNode }) {
  return (
    <div className={`alert alert-${kind}`} role={kind === "error" ? "alert" : "status"}>
      {title && <strong>{title}</strong>}
      {children && <div>{children}</div>}
    </div>
  );
}

export function IssueList({ issues }: { issues: Issue[] }) {
  if (!issues.length) return null;
  return (
    <ul className="issue-list">
      {issues.map((i) => (
        <li key={i.field + i.message}>{i.message}</li>
      ))}
    </ul>
  );
}

/** Renders any thrown error; API validation errors show their field messages. */
export function ErrorAlert({ error, title }: { error: unknown; title?: string }) {
  if (!error) return null;
  if (error instanceof ApiError) {
    return (
      <Alert kind="error" title={title ?? error.message}>
        {title && <p>{error.message}</p>}
        <IssueList issues={error.details} />
      </Alert>
    );
  }
  return <Alert kind="error" title={title ?? "Something went wrong"}>{error instanceof Error ? error.message : String(error)}</Alert>;
}
