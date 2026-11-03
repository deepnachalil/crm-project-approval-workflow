import type { Client } from "../types/api";

export function ClientDetails({ client }: { client: Client }) {
  const c = client.primary_contact;
  return (
    <dl className="details-grid">
      <dt>Legal Entity Name</dt><dd>{client.legal_entity_name}</dd>
      <dt>Registered Address</dt><dd className="pre">{client.registered_address}</dd>
      <dt>Billing Address</dt><dd className="pre">{client.billing_address}</dd>
      <dt>Mode of Payment</dt><dd>{client.mode_of_payment}</dd>
      <dt>Country of Registration</dt><dd>{client.country}</dd>
      <dt>GST Number</dt><dd>{client.gst_number ?? "—"}</dd>
      <dt>Billing Currency</dt><dd>{client.billing_currency}</dd>
      <dt>Primary Contact</dt>
      <dd>
        {c.name}, {c.designation}
        <br />
        <a href={`tel:${c.phone}`}>{c.phone}</a> · <a href={`mailto:${c.email}`}>{c.email}</a>
      </dd>
    </dl>
  );
}
