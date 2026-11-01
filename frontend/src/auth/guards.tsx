import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import type { Role } from "../types/api";
import { useAuth } from "./AuthContext";
import { Loading } from "../components/Feedback";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, initializing } = useAuth();
  const location = useLocation();
  if (initializing) return <Loading />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <>{children}</>;
}

/** UI-level guard only; the backend enforces roles on every endpoint. */
export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { hasRole } = useAuth();
  if (!hasRole(role)) {
    return (
      <div className="card">
        <h2>Not permitted</h2>
        <p>This page is only available to {role === "CRM" ? "CRM users" : "approvers"}.</p>
      </div>
    );
  }
  return <>{children}</>;
}
