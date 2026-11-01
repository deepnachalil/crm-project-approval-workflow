import { http } from "./http";
import type {
  ApprovalRecord,
  AuditEvent,
  Client,
  ClientInput,
  Contract,
  CurrentUser,
  JobCategory,
  LoginResponse,
  Meta,
  PendingApproval,
  ProjectCreate,
  ProjectDetail,
  ProjectSummary,
  ProjectUpdate,
  ProjectVersion,
  RateCard,
  Readiness,
  Role,
  UserRef,
  VersionStatus,
  VersionSummary,
} from "../types/api";

export const authApi = {
  login: (email: string, password: string) => http.post<LoginResponse>("/auth/login", { email, password }),
  me: () => http.get<CurrentUser>("/auth/me"),
};

export const clientsApi = {
  list: (search?: string) => http.get<Client[]>("/clients", { search }),
  get: (id: number) => http.get<Client>(`/clients/${id}`),
  create: (body: ClientInput) => http.post<Client>("/clients", body),
  update: (id: number, body: ClientInput) => http.put<Client>(`/clients/${id}`, body),
};

export interface ProjectFilters {
  status?: VersionStatus | "";
  client_id?: number | "";
  created_by?: number | "";
  search?: string;
}

export const projectsApi = {
  list: (filters: ProjectFilters = {}) => http.get<ProjectSummary[]>("/projects", { ...filters }),
  get: (id: number) => http.get<ProjectDetail>(`/projects/${id}`),
  create: (body: ProjectCreate) => http.post<ProjectDetail>("/projects", body),
  update: (id: number, body: ProjectUpdate) => http.put<ProjectDetail>(`/projects/${id}`, body),
  readiness: (id: number) => http.get<Readiness>(`/projects/${id}/readiness`),
  versions: (id: number) => http.get<VersionSummary[]>(`/projects/${id}/versions`),
  version: (id: number, versionNumber: number) => http.get<ProjectVersion>(`/projects/${id}/versions/${versionNumber}`),
  approvals: (id: number) => http.get<ApprovalRecord[]>(`/projects/${id}/approvals`),
  audit: (id: number) => http.get<AuditEvent[]>(`/projects/${id}/audit`),
  submit: (id: number, comment?: string) => http.post<ProjectDetail>(`/projects/${id}/submit`, { comment }),
  resubmit: (id: number, comment?: string) => http.post<ProjectDetail>(`/projects/${id}/resubmit`, { comment }),
  approve: (id: number, comment?: string) => http.post<ProjectDetail>(`/projects/${id}/approve`, { comment }),
  reject: (id: number, comment: string) => http.post<ProjectDetail>(`/projects/${id}/reject`, { comment }),
};

export interface ContractUpload {
  document_type: string;
  valid_from: string;
  valid_till: string;
  file: File;
}

export const contractsApi = {
  list: (projectId: number, version?: number) => http.get<Contract[]>(`/projects/${projectId}/contracts`, { version }),
  upload: (projectId: number, data: ContractUpload) => {
    const form = new FormData();
    form.append("document_type", data.document_type);
    form.append("valid_from", data.valid_from);
    form.append("valid_till", data.valid_till);
    form.append("file", data.file);
    return http.post<Contract>(`/projects/${projectId}/contracts`, form);
  },
  remove: (contractId: number) => http.delete(`/contracts/${contractId}`),
  downloadUrl: (contractId: number, disposition: "inline" | "attachment") =>
    http.get<{ url: string; expires_in: number }>(`/contracts/${contractId}/download-url`, { disposition }),
};

export const approvalsApi = {
  pending: () => http.get<PendingApproval[]>("/approvals/pending"),
};

export const catalogApi = {
  rateCards: () => http.get<RateCard[]>("/rate-cards"),
  jobCategories: () => http.get<JobCategory[]>("/job-categories"),
  users: (role?: Role) => http.get<UserRef[]>("/users", { role }),
  meta: () => http.get<Meta>("/meta"),
};
