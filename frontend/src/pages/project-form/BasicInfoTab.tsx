import { Field } from "../../components/Field";
import type { Meta, UserRef } from "../../types/api";
import type { Errors } from "../../utils/validation";
import type { FormValues } from "./formModel";

interface Props {
  values: FormValues;
  errors: Errors;
  isNew: boolean;
  meta: Meta;
  crmUsers: UserRef[];
  approvers: UserRef[];
  onChange: <K extends keyof FormValues>(key: K, value: FormValues[K]) => void;
}

export function BasicInfoTab({ values, errors, isNew, meta, crmUsers, approvers, onChange }: Props) {
  return (
    <div className="form-grid">
      <Field label="Project ID" error={errors.project_code} required hint={isNew ? "e.g. PRJ-2026-001 — cannot be changed later" : undefined}>
        <input value={values.project_code} disabled={!isNew} onChange={(e) => onChange("project_code", e.target.value.toUpperCase())} />
      </Field>
      <Field label="Project Name" error={errors.name} required>
        <input value={values.name} onChange={(e) => onChange("name", e.target.value)} />
      </Field>
      <Field label="Project Start Date" error={errors.start_date} required>
        <input type="date" value={values.start_date} onChange={(e) => onChange("start_date", e.target.value)} />
      </Field>
      <Field label="Project End Date" error={errors.end_date} required>
        <input type="date" value={values.end_date} min={values.start_date || undefined} onChange={(e) => onChange("end_date", e.target.value)} />
      </Field>
      <Field label="CRM / Creator" error={errors.crm_user_id} required>
        <select value={values.crm_user_id ?? ""} onChange={(e) => onChange("crm_user_id", e.target.value ? Number(e.target.value) : null)}>
          {crmUsers.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
        </select>
      </Field>
      <Field label="Business Unit" error={errors.business_unit} required>
        <select value={values.business_unit} onChange={(e) => onChange("business_unit", e.target.value)}>
          <option value="">Select…</option>
          {meta.business_units.map((b) => <option key={b}>{b}</option>)}
        </select>
      </Field>
      <Field label="Reviewer / Approver" error={errors.approver_id} required hint="The approver who will review this project">
        <select value={values.approver_id ?? ""} onChange={(e) => onChange("approver_id", e.target.value ? Number(e.target.value) : null)}>
          <option value="">Select…</option>
          {approvers.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
        </select>
      </Field>
    </div>
  );
}
