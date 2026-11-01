import { useEffect, useState } from "react";
import { projectsApi } from "../../api";
import { ApiError } from "../../api/http";
import { ErrorAlert, Loading } from "../../components/Feedback";
import { Field } from "../../components/Field";
import { Modal } from "../../components/Modal";
import { ReadinessPanel } from "../../components/ReadinessPanel";
import type { ProjectDetail, Readiness } from "../../types/api";

export type WorkflowAction = "submit" | "resubmit" | "approve" | "reject";

const TITLES: Record<WorkflowAction, string> = {
  submit: "Submit for approval",
  resubmit: "Resubmit for approval",
  approve: "Approve project",
  reject: "Reject project",
};

interface Props {
  action: WorkflowAction;
  project: ProjectDetail;
  onClose: () => void;
  onDone: (project: ProjectDetail) => void;
}

export function ActionModal({ action, project, onClose, onDone }: Props) {
  const [comment, setComment] = useState("");
  const [commentError, setCommentError] = useState<string>();
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [readiness, setReadiness] = useState<Readiness>();
  const isSubmission = action === "submit" || action === "resubmit";

  useEffect(() => {
    if (isSubmission) projectsApi.readiness(project.id).then(setReadiness).catch(setError);
  }, [isSubmission, project.id]);

  async function confirm() {
    if (action === "reject" && !comment.trim()) {
      setCommentError("Rejection comments are required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const text = comment.trim() || undefined;
      const updated = await {
        submit: () => projectsApi.submit(project.id, text),
        resubmit: () => projectsApi.resubmit(project.id, text),
        approve: () => projectsApi.approve(project.id, text),
        reject: () => projectsApi.reject(project.id, text!),
      }[action]();
      onDone(updated);
    } catch (err) {
      if (err instanceof ApiError) setCommentError(err.fieldErrors().comment);
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const v = project.current_version;
  const blocked = isSubmission && readiness !== undefined && !readiness.ready;

  return (
    <Modal
      title={TITLES[action]}
      onClose={onClose}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button
            type="button"
            className={`btn ${action === "reject" ? "btn-danger" : "btn-primary"}`}
            disabled={busy || blocked || (isSubmission && !readiness)}
            onClick={confirm}
          >
            {busy ? "Working…" : TITLES[action]}
          </button>
        </>
      }
    >
      <p>
        <strong>{project.project_code}</strong> — {v.name} (v{v.version_number})
      </p>
      {isSubmission && (readiness ? <ReadinessPanel readiness={readiness} /> : <Loading label="Checking readiness…" />)}
      {isSubmission && v.approver && <p>This will be sent to <strong>{v.approver.full_name}</strong> for review.</p>}
      {action === "approve" && project.active_version && project.active_version.id !== v.id && (
        <p>Approving makes v{v.version_number} the active version, replacing v{project.active_version.version_number}.</p>
      )}
      <ErrorAlert error={error} />
      <Field
        label={action === "reject" ? "Rejection reason" : "Comments"}
        required={action === "reject"}
        error={commentError}
        hint={action === "reject" ? "Explain what needs to be corrected" : "Optional"}
      >
        <textarea rows={4} maxLength={2000} value={comment} onChange={(e) => { setComment(e.target.value); setCommentError(undefined); }} />
      </Field>
    </Modal>
  );
}
