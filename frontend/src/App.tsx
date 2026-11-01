import { Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth, RequireRole } from "./auth/guards";
import { Layout } from "./components/Layout";
import { ApprovalsPage } from "./pages/ApprovalsPage";
import { ClientFormPage } from "./pages/ClientFormPage";
import { ClientListPage } from "./pages/ClientListPage";
import { LoginPage } from "./pages/LoginPage";
import { ProjectDetailPage } from "./pages/ProjectDetailPage";
import { ProjectFormPage } from "./pages/ProjectFormPage";
import { ProjectListPage } from "./pages/ProjectListPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Navigate to="/projects" replace />} />
        <Route path="/projects" element={<ProjectListPage />} />
        <Route path="/projects/new" element={<RequireRole role="CRM"><ProjectFormPage key="new" /></RequireRole>} />
        <Route path="/projects/:id" element={<ProjectDetailPage />} />
        <Route path="/projects/:id/edit" element={<RequireRole role="CRM"><ProjectFormPage /></RequireRole>} />
        <Route path="/approvals" element={<RequireRole role="APPROVER"><ApprovalsPage /></RequireRole>} />
        <Route path="/clients" element={<RequireRole role="CRM"><ClientListPage /></RequireRole>} />
        <Route path="/clients/new" element={<RequireRole role="CRM"><ClientFormPage key="new" /></RequireRole>} />
        <Route path="/clients/:id/edit" element={<RequireRole role="CRM"><ClientFormPage /></RequireRole>} />
        <Route path="*" element={<div className="card"><h2>Page not found</h2></div>} />
      </Route>
    </Routes>
  );
}
