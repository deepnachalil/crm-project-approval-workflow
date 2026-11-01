import type { Readiness } from "../types/api";
import { Alert, IssueList } from "./Feedback";

/** Submission checklist as evaluated by the backend (GET /projects/{id}/readiness). */
export function ReadinessPanel({ readiness, stale }: { readiness: Readiness | undefined; stale?: boolean }) {
  if (!readiness) return null;
  if (readiness.ready) {
    return (
      <Alert kind="success" title="Ready to submit for approval">
        {stale && "Based on the last saved draft — unsaved changes will be saved first."}
      </Alert>
    );
  }
  return (
    <Alert kind="warning" title="Not ready for approval yet">
      {stale && <p className="small">Based on the last saved draft.</p>}
      <IssueList issues={readiness.issues} />
    </Alert>
  );
}
