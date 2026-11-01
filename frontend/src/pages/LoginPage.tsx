import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ErrorAlert } from "../components/Feedback";
import { Field } from "../components/Field";
import { config } from "../config";
import { EMAIL_RE, type Errors } from "../utils/validation";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const from = (useLocation().state as { from?: string } | null)?.from ?? "/projects";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Errors>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={from} replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const errs: Errors = {};
    if (!EMAIL_RE.test(email.trim())) errs.email = "Enter a valid email address";
    if (!password) errs.password = "Enter your password";
    setErrors(errs);
    if (Object.keys(errs).length) return;

    setBusy(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <form className="card login-card" onSubmit={onSubmit} noValidate>
        <h1>Sign in</h1>
        <p className="muted">Project Setup &amp; Approval Workflow</p>
        <ErrorAlert error={error} />
        <Field label="Email" error={errors.email} required>
          <input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Password" error={errors.password} required>
          <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        {config.authMode === "local" && (
          <div className="hint-box">
            <strong>Local test users</strong> (password <code>Password123!</code>)
            <ul>
              <li>CRM: crm@example.com, crm2@example.com</li>
              <li>Approver: approver@example.com, approver2@example.com</li>
            </ul>
          </div>
        )}
      </form>
    </div>
  );
}
