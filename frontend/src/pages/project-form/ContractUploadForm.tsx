import { useRef, useState } from "react";
import { contractsApi } from "../../api";
import { ApiError } from "../../api/http";
import { ErrorAlert } from "../../components/Feedback";
import { Field } from "../../components/Field";
import type { Meta } from "../../types/api";
import { dateOrder, hasErrors, required, type Errors } from "../../utils/validation";

interface Props {
  projectId: number;
  meta: Meta;
  onUploaded: () => Promise<void> | void;
}

export function ContractUploadForm({ projectId, meta, onUploaded }: Props) {
  const [documentType, setDocumentType] = useState("");
  const [validFrom, setValidFrom] = useState("");
  const [validTill, setValidTill] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [errors, setErrors] = useState<Errors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  function validate(): Errors {
    const e: Errors = {};
    required(documentType, "Select a document type", e, "document_type");
    required(validFrom, "Valid from is required", e, "valid_from");
    required(validTill, "Valid till is required", e, "valid_till");
    dateOrder(validFrom, validTill, e, "valid_till", "Valid till must be on or after valid from");
    if (!file) {
      e.file = "Choose a file";
    } else {
      const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
      if (!meta.allowed_file_extensions.includes(ext)) e.file = `Allowed types: ${meta.allowed_file_extensions.join(", ")}`;
      else if (file.size > meta.max_upload_mb * 1024 * 1024) e.file = `Maximum file size is ${meta.max_upload_mb} MB`;
      else if (file.size === 0) e.file = "File is empty";
    }
    return e;
  }

  async function onUpload() {
    const errs = validate();
    setErrors(errs);
    if (hasErrors(errs) || !file) return;
    setBusy(true);
    setError(null);
    try {
      await contractsApi.upload(projectId, { document_type: documentType, valid_from: validFrom, valid_till: validTill, file });
      setDocumentType("");
      setValidFrom("");
      setValidTill("");
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      await onUploaded();
    } catch (err) {
      if (err instanceof ApiError) setErrors(err.fieldErrors());
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    // Not a <form>: it is rendered inside the project form, and nested forms are invalid HTML.
    <div className="subform">
      <h4>Upload contract</h4>
      <ErrorAlert error={error} />
      <div className="form-grid form-grid-4">
        <Field label="Document Type" error={errors.document_type} required>
          <select value={documentType} onChange={(e) => setDocumentType(e.target.value)}>
            <option value="">Select…</option>
            {meta.document_types.map((t) => <option key={t}>{t}</option>)}
          </select>
        </Field>
        <Field label="Valid From" error={errors.valid_from} required>
          <input type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />
        </Field>
        <Field label="Valid Till" error={errors.valid_till} required>
          <input type="date" value={validTill} min={validFrom || undefined} onChange={(e) => setValidTill(e.target.value)} />
        </Field>
        <Field label="File" error={errors.file} required hint={`${meta.allowed_file_extensions.join(", ")} · max ${meta.max_upload_mb} MB`}>
          <input
            ref={fileInput}
            type="file"
            accept={meta.allowed_file_extensions.join(",")}
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </Field>
      </div>
      <button type="button" className="btn btn-primary" disabled={busy} onClick={onUpload}>
        {busy ? "Uploading…" : "Upload"}
      </button>
    </div>
  );
}
