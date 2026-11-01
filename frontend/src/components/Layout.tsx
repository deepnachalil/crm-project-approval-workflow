import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function Layout() {
  const { user, logout, hasRole } = useAuth();
  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">Project Setup &amp; Approval</div>
        <nav className="nav">
          <NavLink to="/projects">Projects</NavLink>
          {hasRole("APPROVER") && <NavLink to="/approvals">Pending Approvals</NavLink>}
          {hasRole("CRM") && <NavLink to="/clients">Clients</NavLink>}
        </nav>
        <div className="user">
          <span>
            {user?.full_name} <span className="role-tag">{user?.role === "CRM" ? "CRM" : "Approver"}</span>
          </span>
          <button className="btn btn-link" onClick={logout}>Sign out</button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
