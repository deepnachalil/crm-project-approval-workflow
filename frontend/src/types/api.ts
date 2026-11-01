// Shapes mirror the backend response schemas (backend/app/schemas).

export type Role = "CRM" | "APPROVER";
export type VersionStatus = "DRAFT" | "PENDING_APPROVAL" | "REJECTED" | "APPROVED";
export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED";
export type ProjectAction = "edit" | "manage_contracts" | "submit" | "resubmit" | "approve" | "reject";

export interface UserRef {
  id: number;
  full_name: string;
  email: string;
}

export interface CurrentUser extends UserRef {
  role: Role;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: CurrentUser;
}

export interface PrimaryContact {
  name: string;
  designation: string;
  phone: string;
  email: string;
}

export interface ClientInput {
  legal_entity_name: string;
  registered_address: string;
  billing_address: string;
  mode_of_payment: string;
  gst_number: string | null;
  billing_currency: string;
  primary_contact: PrimaryContact;
}

export interface Client extends ClientInput {
  id: number;
  created_at: string;
  updated_at: string;
}

export interface RateCard {
  id: number;
  code: string;
  name: string;
  description: string | null;
  currency: string;
}

export interface JobCategory {
  id: number;
  name: string;
  default_rate_card: RateCard | null;
}

export interface Meta {
  business_units: string[];
  payment_modes: string[];
  currencies: string[];
  document_types: string[];
  allowed_file_extensions: string[];
  max_upload_mb: number;
  auth_mode: "local" | "cognito";
}

export interface Contract {
  id: number;
  version_id: number;
  document_type: string;
  valid_from: string;
  valid_till: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  uploaded_by: UserRef;
  uploaded_at: string;
}

export interface ProjectJobCategory {
  id: number;
  name: string;
  job_category_id: number | null;
  rate_card: RateCard | null;
}

export interface Decision {
  status: ApprovalStatus;
  submitted_by: UserRef;
  submitted_at: string;
  approver: UserRef;
  decided_by: UserRef | null;
  decided_at: string | null;
  comment: string | null;
}

export interface ProjectVersion {
  id: number;
  version_number: number;
  status: VersionStatus;
  is_active: boolean;
  based_on_version_number: number | null;
  name: string;
  start_date: string | null;
  end_date: string | null;
  business_unit: string | null;
  client: Client | null;
  crm_user: UserRef;
  approver: UserRef | null;
  job_categories: ProjectJobCategory[];
  contracts: Contract[];
  created_by: UserRef;
  created_at: string;
  updated_at: string;
  last_decision: Decision | null;
}

export interface FieldChange {
  field: string;
  label: string;
  old: string | string[] | null;
  new: string | string[] | null;
}

export interface VersionSummary {
  id: number;
  version_number: number;
  status: VersionStatus;
  is_active: boolean;
  based_on_version_number: number | null;
  created_by: UserRef;
  created_at: string;
  updated_at: string;
  last_decision: Decision | null;
  changes: FieldChange[];
}

export interface ProjectSummary {
  id: number;
  project_code: string;
  name: string;
  client: { id: number; legal_entity_name: string } | null;
  status: VersionStatus;
  current_version_number: number;
  active_version_number: number | null;
  created_by: UserRef;
  created_at: string;
  updated_at: string;
  can_edit: boolean;
}

export interface ProjectDetail {
  id: number;
  project_code: string;
  status: VersionStatus;
  created_by: UserRef;
  created_at: string;
  updated_at: string;
  current_version: ProjectVersion;
  active_version: ProjectVersion | null;
  allowed_actions: ProjectAction[];
}

export interface JobCategoryInput {
  name: string;
  job_category_id: number | null;
  rate_card_id: number | null;
}

export interface ProjectWrite {
  name: string;
  start_date: string | null;
  end_date: string | null;
  client_id: number | null;
  business_unit: string | null;
  crm_user_id: number | null;
  approver_id: number | null;
  job_categories: JobCategoryInput[];
}

export interface ProjectCreate extends ProjectWrite {
  project_code: string;
}

export interface ProjectUpdate extends ProjectWrite {
  change_note?: string | null;
}

export interface Issue {
  field: string;
  message: string;
}

export interface Readiness {
  ready: boolean;
  issues: Issue[];
}

export interface ApprovalComment {
  id: number;
  kind: "SUBMISSION" | "APPROVAL" | "REJECTION";
  comment: string;
  author: UserRef;
  created_at: string;
}

export interface ApprovalRecord {
  id: number;
  version_number: number;
  status: ApprovalStatus;
  is_resubmission: boolean;
  submitted_by: UserRef;
  submitted_at: string;
  approver: UserRef;
  decided_by: UserRef | null;
  decided_at: string | null;
  comments: ApprovalComment[];
}

export interface PendingApproval {
  approval_id: number;
  project: ProjectSummary;
  version_number: number;
  is_resubmission: boolean;
  submitted_by: UserRef;
  submitted_at: string;
}

export interface AuditEvent {
  id: number;
  project_id: number | null;
  version_id: number | null;
  version_number: number | null;
  user: UserRef;
  action: string;
  comment: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}
