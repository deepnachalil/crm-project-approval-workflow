import { useId, type ReactElement, cloneElement } from "react";

interface FieldProps {
  label: string;
  error?: string;
  required?: boolean;
  hint?: string;
  children: ReactElement<{ id?: string; "aria-invalid"?: boolean; "aria-describedby"?: string }>;
}

/** Label + input + inline error, wired up for accessibility. */
export function Field({ label, error, required, hint, children }: FieldProps) {
  const id = useId();
  const msgId = `${id}-msg`;
  return (
    <div className={`field${error ? " field-error" : ""}`}>
      <label htmlFor={id}>
        {label}
        {required && <span className="required" aria-hidden> *</span>}
      </label>
      {cloneElement(children, { id, "aria-invalid": !!error, "aria-describedby": error || hint ? msgId : undefined })}
      {error ? <span id={msgId} className="error-text">{error}</span> : hint && <span id={msgId} className="hint">{hint}</span>}
    </div>
  );
}
