import type { ProjectVersion, ProjectWrite } from "../../types/api";
import { PROJECT_CODE_RE, dateOrder, required, type Errors } from "../../utils/validation";

export type TabKey = "basic" | "client" | "contracts" | "jobs";

export interface JobRow {
  key: string;
  name: string;
  job_category_id: number | null;
  rate_card_id: number | null;
}

export interface FormValues {
  project_code: string;
  name: string;
  start_date: string;
  end_date: string;
  business_unit: string;
  crm_user_id: number | null;
  approver_id: number | null;
  client_id: number | null;
  job_categories: JobRow[];
}

let rowSeq = 0;
export const newRow = (partial: Partial<JobRow> = {}): JobRow => ({
  key: `row-${++rowSeq}`,
  name: "",
  job_category_id: null,
  rate_card_id: null,
  ...partial,
});

export const emptyForm = (crmUserId: number | null): FormValues => ({
  project_code: "",
  name: "",
  start_date: "",
  end_date: "",
  business_unit: "",
  crm_user_id: crmUserId,
  approver_id: null,
  client_id: null,
  job_categories: [newRow()],
});

export function fromVersion(code: string, v: ProjectVersion): FormValues {
  return {
    project_code: code,
    name: v.name,
    start_date: v.start_date ?? "",
    end_date: v.end_date ?? "",
    business_unit: v.business_unit ?? "",
    crm_user_id: v.crm_user.id,
    approver_id: v.approver?.id ?? null,
    client_id: v.client?.id ?? null,
    job_categories: v.job_categories.map((jc) =>
      newRow({ name: jc.name, job_category_id: jc.job_category_id, rate_card_id: jc.rate_card?.id ?? null }),
    ),
  };
}

export function toPayload(v: FormValues): ProjectWrite {
  return {
    name: v.name.trim(),
    start_date: v.start_date || null,
    end_date: v.end_date || null,
    business_unit: v.business_unit || null,
    crm_user_id: v.crm_user_id,
    approver_id: v.approver_id,
    client_id: v.client_id,
    job_categories: v.job_categories
      .filter((r) => r.name.trim() || r.rate_card_id) // ignore completely empty rows
      .map((r) => ({ name: r.name.trim(), job_category_id: r.job_category_id, rate_card_id: r.rate_card_id })),
  };
}

/** Checks needed to *save* (drafts may be incomplete); `strict` adds the submit-time required fields. */
export function validateForm(v: FormValues, { isNew, strict }: { isNew: boolean; strict: boolean }): Errors {
  const e: Errors = {};
  if (isNew) {
    required(v.project_code, "Project ID is required", e, "project_code");
    if (v.project_code && !PROJECT_CODE_RE.test(v.project_code.trim().toUpperCase()))
      e.project_code = "3–32 characters: letters, digits, '-' or '_'";
  }
  required(v.name, "Project name is required", e, "name");
  dateOrder(v.start_date, v.end_date, e, "end_date", "End date must be on or after the start date");

  const seen = new Set<string>();
  v.job_categories.forEach((r, i) => {
    const name = r.name.trim().toLowerCase();
    if (!name && r.rate_card_id) e[`job_categories[${i}].name`] = "Enter a job category name";
    if (name && seen.has(name)) e[`job_categories[${i}].name`] = "Duplicate job category";
    seen.add(name);
    if (strict && name && !r.rate_card_id) e[`job_categories[${i}].rate_card_id`] = "Select a rate card";
  });

  if (strict) {
    required(v.start_date, "Start date is required", e, "start_date");
    required(v.end_date, "End date is required", e, "end_date");
    required(v.business_unit, "Business unit is required", e, "business_unit");
    required(v.approver_id, "Select an approver", e, "approver_id");
    required(v.client_id, "Select a client", e, "client_id");
    if (!v.job_categories.some((r) => r.name.trim())) e.job_categories = "Define at least one job category";
  }
  return e;
}

const TAB_FIELDS: Record<TabKey, (field: string) => boolean> = {
  basic: (f) => ["project_code", "name", "start_date", "end_date", "business_unit", "crm_user_id", "approver_id"].includes(f),
  client: (f) => f === "client_id",
  contracts: (f) => f === "contracts",
  jobs: (f) => f.startsWith("job_categories"),
};

export const tabHasErrors = (tab: TabKey, errors: Errors) => Object.keys(errors).some(TAB_FIELDS[tab]);
export const firstTabWithErrors = (errors: Errors): TabKey | undefined =>
  (Object.keys(TAB_FIELDS) as TabKey[]).find((t) => tabHasErrors(t, errors));
