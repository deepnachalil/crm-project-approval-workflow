import { useState, type FormEvent } from "react";
import { clientsApi } from "../api";
import { ApiError } from "../api/http";
import type { Client, ClientInput, Meta } from "../types/api";
import { EMAIL_RE, GST_RE, PHONE_RE, hasErrors, required, type Errors } from "../utils/validation";
import { ErrorAlert } from "./Feedback";
import { Field } from "./Field";

const EMPTY: ClientInput = {
  legal_entity_name: "",
  registered_address: "",
  billing_address: "",
  mode_of_payment: "",
  gst_number: "",
  billing_currency: "",
  primary_contact: { name: "", designation: "", phone: "", email: "" },
};

function validate(v: ClientInput): Errors {
  const e: Errors = {};
  required(v.legal_entity_name, "Legal entity name is required", e, "legal_entity_name");
  required(v.registered_address, "Registered address is required", e, "registered_address");
  required(v.billing_address, "Billing address is required", e, "billing_address");
  required(v.mode_of_payment, "Select a mode of payment", e, "mode_of_payment");
  required(v.billing_currency, "Select a billing currency", e, "billing_currency");
  if (v.gst_number && !GST_RE.test(v.gst_number.trim().toUpperCase())) e.gst_number = "Enter a valid 15-character GSTIN";
  const c = v.primary_contact;
  required(c.name, "Contact name is required", e, "primary_contact.name");
  required(c.designation, "Designation is required", e, "primary_contact.designation");
  if (!PHONE_RE.test(c.phone.trim())) e["primary_contact.phone"] = "Enter a valid phone number";
  if (!EMAIL_RE.test(c.email.trim())) e["primary_contact.email"] = "Enter a valid email address";
  return e;
}

function toInput(c: Client | null): ClientInput {
  if (!c) return EMPTY;
  return {
    legal_entity_name: c.legal_entity_name,
    registered_address: c.registered_address,
    billing_address: c.billing_address,
    mode_of_payment: c.mode_of_payment,
    gst_number: c.gst_number ?? "",
    billing_currency: c.billing_currency,
    primary_contact: { ...c.primary_contact },
  };
}

interface Props {
  client: Client | null;
  meta: Meta;
  onSaved: (client: Client) => void;
  onCancel: () => void;
}

/** Create / edit a client. Used by the Clients page and inline from the project form. */
export function ClientForm({ client, meta, onSaved, onCancel }: Props) {
  const [values, setValues] = useState<ClientInput>(() => toInput(client));
  const [errors, setErrors] = useState<Errors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const set = (field: keyof ClientInput, value: string) => setValues((v) => ({ ...v, [field]: value }));
  const setContact = (field: keyof ClientInput["primary_contact"], value: string) =>
    setValues((v) => ({ ...v, primary_contact: { ...v.primary_contact, [field]: value } }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    e.stopPropagation(); // may be rendered in a portal-less modal above another form
    const errs = validate(values);
    setErrors(errs);
    if (hasErrors(errs)) return;
    setBusy(true);
    setError(null);
    const body = { ...values, gst_number: values.gst_number?.trim() ? values.gst_number.trim().toUpperCase() : null };
    try {
      onSaved(client ? await clientsApi.update(client.id, body) : await clientsApi.create(body));
    } catch (err) {
      if (err instanceof ApiError) setErrors(err.fieldErrors());
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate>
      <ErrorAlert error={error} />
      <div className="form-grid">
        <Field label="Legal Entity Name" error={errors.legal_entity_name} required>
          <input value={values.legal_entity_name} onChange={(e) => set("legal_entity_name", e.target.value)} />
        </Field>
        <Field label="GST Number" error={errors.gst_number} hint="Optional for non-Indian entities">
          <input value={values.gst_number ?? ""} maxLength={15} onChange={(e) => set("gst_number", e.target.value.toUpperCase())} />
        </Field>
        <Field label="Registered Address" error={errors.registered_address} required>
          <textarea rows={3} value={values.registered_address} onChange={(e) => set("registered_address", e.target.value)} />
        </Field>
        <Field label="Billing Address" error={errors.billing_address} required>
          <textarea rows={3} value={values.billing_address} onChange={(e) => set("billing_address", e.target.value)} />
        </Field>
        <Field label="Mode of Payment" error={errors.mode_of_payment} required>
          <select value={values.mode_of_payment} onChange={(e) => set("mode_of_payment", e.target.value)}>
            <option value="">Select…</option>
            {meta.payment_modes.map((m) => <option key={m}>{m}</option>)}
          </select>
        </Field>
        <Field label="Billing Currency" error={errors.billing_currency} required>
          <select value={values.billing_currency} onChange={(e) => set("billing_currency", e.target.value)}>
            <option value="">Select…</option>
            {meta.currencies.map((c) => <option key={c}>{c}</option>)}
          </select>
        </Field>
      </div>

      <h3>Primary Contact</h3>
      <div className="form-grid">
        <Field label="Name" error={errors["primary_contact.name"]} required>
          <input value={values.primary_contact.name} onChange={(e) => setContact("name", e.target.value)} />
        </Field>
        <Field label="Designation" error={errors["primary_contact.designation"]} required>
          <input value={values.primary_contact.designation} onChange={(e) => setContact("designation", e.target.value)} />
        </Field>
        <Field label="Phone" error={errors["primary_contact.phone"]} required>
          <input type="tel" value={values.primary_contact.phone} onChange={(e) => setContact("phone", e.target.value)} />
        </Field>
        <Field label="Email" error={errors["primary_contact.email"]} required>
          <input type="email" value={values.primary_contact.email} onChange={(e) => setContact("email", e.target.value)} />
        </Field>
      </div>

      <div className="form-actions">
        <button type="button" className="btn" onClick={onCancel}>Cancel</button>
        <button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Save Client"}</button>
      </div>
    </form>
  );
}
