import type { ApprovalStatus, VersionStatus } from "../types/api";

const LABELS: Record<VersionStatus | ApprovalStatus, string> = {
  DRAFT: "Draft",
  PENDING_APPROVAL: "Pending Approval",
  PENDING: "Pending",
  REJECTED: "Rejected",
  APPROVED: "Approved",
};

export const statusLabel = (s: VersionStatus | ApprovalStatus) => LABELS[s];

export function StatusBadge({ status }: { status: VersionStatus | ApprovalStatus }) {
  return <span className={`badge badge-${status.toLowerCase()}`}>{LABELS[status]}</span>;
}

export function ActiveBadge() {
  return <span className="badge badge-active">Active</span>;
}
