import { useState } from "react";
import { contractsApi } from "../api";
import type { Contract } from "../types/api";
import { formatBytes, formatDate } from "../utils/format";
import { ErrorAlert } from "./Feedback";

interface Props {
  contracts: Contract[];
  onDelete?: (contract: Contract) => Promise<void>;
}

export function ContractTable({ contracts, onDelete }: Props) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<unknown>(null);

  async function open(contract: Contract, disposition: "inline" | "attachment") {
    setError(null);
    // Open the tab synchronously (popup blockers), then point it at the short-lived URL.
    const win = disposition === "inline" ? window.open("about:blank", "_blank") : null;
    try {
      const { url } = await contractsApi.downloadUrl(contract.id, disposition);
      if (win) {
        win.location.href = url;
      } else {
        const a = document.createElement("a");
        a.href = url;
        a.download = contract.file_name;
        a.click();
      }
    } catch (e) {
      win?.close();
      setError(e);
    }
  }

  async function remove(contract: Contract) {
    if (!onDelete || !window.confirm(`Delete "${contract.file_name}"?`)) return;
    setBusyId(contract.id);
    setError(null);
    try {
      await onDelete(contract);
    } catch (e) {
      setError(e);
    } finally {
      setBusyId(null);
    }
  }

  if (!contracts.length) return <p className="muted">No contract documents uploaded.</p>;

  return (
    <>
      <ErrorAlert error={error} />
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Document Type</th>
              <th>File</th>
              <th>Valid From</th>
              <th>Valid Till</th>
              <th>Uploaded By</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {contracts.map((c) => (
              <tr key={c.id}>
                <td data-label="Type">{c.document_type}</td>
                <td data-label="File">
                  {c.file_name} <span className="muted small">({formatBytes(c.size_bytes)})</span>
                </td>
                <td data-label="Valid From">{formatDate(c.valid_from)}</td>
                <td data-label="Valid Till">{formatDate(c.valid_till)}</td>
                <td data-label="Uploaded By">{c.uploaded_by.full_name}</td>
                <td className="actions">
                  <button type="button" className="btn btn-sm" onClick={() => open(c, "inline")}>View</button>
                  <button type="button" className="btn btn-sm" onClick={() => open(c, "attachment")}>Download</button>
                  {onDelete && (
                    <button type="button" className="btn btn-sm btn-danger" disabled={busyId === c.id} onClick={() => remove(c)}>
                      {busyId === c.id ? "Deleting…" : "Delete"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
