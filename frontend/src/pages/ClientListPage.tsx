import { useState } from "react";
import { Link } from "react-router-dom";
import { clientsApi } from "../api";
import { ErrorAlert, Loading } from "../components/Feedback";
import { useAsync } from "../hooks/useAsync";
import { useDebounced } from "../hooks/useDebounced";

export function ClientListPage() {
  const [search, setSearch] = useState("");
  const debounced = useDebounced(search);
  const clients = useAsync(() => clientsApi.list(debounced), [debounced]);

  return (
    <section>
      <div className="page-header">
        <h1>Clients</h1>
        <Link to="/clients/new" className="btn btn-primary">+ New Client</Link>
      </div>
      <div className="card filters">
        <label>
          Search
          <input placeholder="Legal entity name" value={search} onChange={(e) => setSearch(e.target.value)} />
        </label>
      </div>
      <ErrorAlert error={clients.error} />
      {clients.loading && !clients.data ? (
        <Loading />
      ) : (
        <div className="card table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Legal Entity Name</th>
                <th>GST Number</th>
                <th>Currency</th>
                <th>Payment</th>
                <th>Primary Contact</th>
                <th aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {clients.data?.length === 0 && <tr><td colSpan={6} className="empty">No clients found.</td></tr>}
              {clients.data?.map((c) => (
                <tr key={c.id}>
                  <td data-label="Name">{c.legal_entity_name}</td>
                  <td data-label="GST">{c.gst_number ?? "—"}</td>
                  <td data-label="Currency">{c.billing_currency}</td>
                  <td data-label="Payment">{c.mode_of_payment}</td>
                  <td data-label="Contact">{c.primary_contact.name} ({c.primary_contact.email})</td>
                  <td className="actions"><Link to={`/clients/${c.id}/edit`} className="btn btn-sm">Edit</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
