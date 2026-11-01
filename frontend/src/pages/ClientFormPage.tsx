import { useNavigate, useParams } from "react-router-dom";
import { catalogApi, clientsApi } from "../api";
import { ClientForm } from "../components/ClientForm";
import { ErrorAlert, Loading } from "../components/Feedback";
import { useAsync } from "../hooks/useAsync";

export function ClientFormPage() {
  const { id } = useParams();
  const clientId = id ? Number(id) : null;
  const navigate = useNavigate();
  const data = useAsync(
    () => Promise.all([catalogApi.meta(), clientId ? clientsApi.get(clientId) : Promise.resolve(null)]),
    [clientId],
  );

  if (data.loading) return <Loading />;
  if (data.error || !data.data) return <ErrorAlert error={data.error} />;
  const [meta, client] = data.data;

  return (
    <section>
      <div className="page-header">
        <h1>{clientId ? "Edit Client" : "New Client"}</h1>
      </div>
      <div className="card">
        <ClientForm client={client} meta={meta} onSaved={() => navigate("/clients")} onCancel={() => navigate("/clients")} />
      </div>
    </section>
  );
}
