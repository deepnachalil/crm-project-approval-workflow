import { useState } from "react";
import { ClientDetails } from "../../components/ClientDetails";
import { ClientForm } from "../../components/ClientForm";
import { Field } from "../../components/Field";
import { Modal } from "../../components/Modal";
import type { Client, Meta } from "../../types/api";

interface Props {
  clients: Client[];
  clientId: number | null;
  error?: string;
  meta: Meta;
  onChange: (clientId: number | null) => void;
  onClientSaved: (client: Client) => void;
}

export function ClientTab({ clients, clientId, error, meta, onChange, onClientSaved }: Props) {
  const selected = clients.find((c) => c.id === clientId) ?? null;
  const [editing, setEditing] = useState<"new" | "edit" | null>(null);

  return (
    <div>
      <div className="row-between">
        <Field label="Client" error={error} required>
          <select value={clientId ?? ""} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
            <option value="">Select an existing client…</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.legal_entity_name}</option>)}
          </select>
        </Field>
        <div className="inline-actions">
          {selected && <button type="button" className="btn btn-sm" onClick={() => setEditing("edit")}>Edit client</button>}
          <button type="button" className="btn btn-sm" onClick={() => setEditing("new")}>+ New client</button>
        </div>
      </div>

      {selected ? (
        <div className="panel">
          <ClientDetails client={selected} />
        </div>
      ) : (
        <p className="muted">Select a client to see its billing and contact details.</p>
      )}

      {editing && (
        <Modal title={editing === "new" ? "New Client" : "Edit Client"} onClose={() => setEditing(null)}>
          <ClientForm
            client={editing === "edit" ? selected : null}
            meta={meta}
            onCancel={() => setEditing(null)}
            onSaved={(client) => {
              setEditing(null);
              onClientSaved(client);
            }}
          />
        </Modal>
      )}
    </div>
  );
}
