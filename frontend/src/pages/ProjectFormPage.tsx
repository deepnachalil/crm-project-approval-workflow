import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { catalogApi, clientsApi, contractsApi, projectsApi } from "../api";
import { ApiError } from "../api/http";
import { useAuth } from "../auth/AuthContext";
import { ContractTable } from "../components/ContractTable";
import { Alert, ErrorAlert, Loading } from "../components/Feedback";
import { ReadinessPanel } from "../components/ReadinessPanel";
import { StatusBadge } from "../components/StatusBadge";
import { Tabs } from "../components/Tabs";
import { useAsync } from "../hooks/useAsync";
import type { Client, ProjectDetail, Readiness } from "../types/api";
import { hasErrors, type Errors } from "../utils/validation";
import { BasicInfoTab } from "./project-form/BasicInfoTab";
import { ClientTab } from "./project-form/ClientTab";
import { ContractUploadForm } from "./project-form/ContractUploadForm";
import { JobCategoriesTab } from "./project-form/JobCategoriesTab";
import {
  emptyForm,
  firstTabWithErrors,
  fromVersion,
  tabHasErrors,
  toPayload,
  validateForm,
  type FormValues,
  type TabKey,
} from "./project-form/formModel";

export function ProjectFormPage() {
  const { id } = useParams();
  const projectId = id ? Number(id) : null;
  const isNew = projectId === null;
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();

  const lookups = useAsync(
    () =>
      Promise.all([
        catalogApi.meta(),
        clientsApi.list(),
        catalogApi.rateCards(),
        catalogApi.jobCategories(),
        catalogApi.users("CRM"),
        catalogApi.users("APPROVER"),
      ]),
    [],
  );

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [readiness, setReadiness] = useState<Readiness>();
  const [clients, setClients] = useState<Client[]>([]);
  const [values, setValues] = useState<FormValues>(() => emptyForm(user?.id ?? null));
  const [dirty, setDirty] = useState(false);
  const [errors, setErrors] = useState<Errors>({});
  const [tab, setTab] = useState<TabKey>((searchParams.get("tab") as TabKey) || "basic");
  const [loadError, setLoadError] = useState<unknown>(null);
  const [actionError, setActionError] = useState<unknown>(null);
  const [notice, setNotice] = useState<string | null>(searchParams.get("created") ? "Draft created. You can now upload contract documents." : null);
  const [busy, setBusy] = useState<"save" | "submit" | null>(null);

  useEffect(() => {
    if (lookups.data) setClients(lookups.data[1]);
  }, [lookups.data]);

  async function refresh(resetForm: boolean): Promise<ProjectDetail | null> {
    if (!projectId) return null;
    const [p, r] = await Promise.all([projectsApi.get(projectId), projectsApi.readiness(projectId)]);
    setProject(p);
    setReadiness(r);
    if (resetForm) {
      setValues(fromVersion(p.project_code, p.current_version));
      setDirty(false);
    }
    return p;
  }

  useEffect(() => {
    refresh(true).catch(setLoadError);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  function change<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setValues((v) => ({ ...v, [key]: value }));
    setDirty(true);
    setNotice(null);
  }

  /** Saves the form. Returns the saved project id, or null if validation failed. */
  async function save(strict: boolean): Promise<number | null> {
    const errs = validateForm(values, { isNew, strict });
    setErrors(errs);
    if (hasErrors(errs)) {
      setTab(firstTabWithErrors(errs) ?? tab);
      return null;
    }
    try {
      if (isNew) {
        const created = await projectsApi.create({ ...toPayload(values), project_code: values.project_code.trim().toUpperCase() });
        return created.id;
      }
      if (dirty) {
        const before = project?.current_version.version_number;
        const updated = await projectsApi.update(projectId!, toPayload(values));
        const after = updated.current_version.version_number;
        setNotice(
          after !== before
            ? `Saved as new draft version v${after}. The approved version v${before} stays active until v${after} is approved.`
            : "Changes saved.",
        );
        await refresh(true);
      }
      return projectId;
    } catch (err) {
      if (err instanceof ApiError) {
        const fieldErrs = err.fieldErrors();
        setErrors(fieldErrs);
        const t = firstTabWithErrors(fieldErrs);
        if (t) setTab(t);
      }
      setActionError(err);
      return null;
    }
  }

  async function onSaveDraft() {
    setBusy("save");
    setActionError(null);
    const savedId = await save(false);
    setBusy(null);
    if (savedId && isNew) navigate(`/projects/${savedId}/edit?tab=contracts&created=1`, { replace: true });
  }

  async function onSubmit() {
    if (!project) return;
    setBusy("submit");
    setActionError(null);
    const savedId = await save(true);
    if (savedId) {
      try {
        const resubmission = project.status === "REJECTED";
        await (resubmission ? projectsApi.resubmit(savedId) : projectsApi.submit(savedId));
        navigate(`/projects/${savedId}?submitted=1`);
        return;
      } catch (err) {
        if (err instanceof ApiError) {
          setErrors(err.fieldErrors());
          const t = firstTabWithErrors(err.fieldErrors());
          if (t) setTab(t);
        }
        setActionError(err);
        await refresh(false).catch(() => undefined);
      }
    }
    setBusy(null);
  }

  async function onContractsChanged(message: string) {
    const before = project?.current_version.version_number;
    const after = (await refresh(false))?.current_version.version_number;
    // A contract change on an approved project creates a new draft version server-side.
    setNotice(after !== before ? `${message} A new draft version v${after} was created.` : message);
  }

  if (lookups.loading || (!isNew && !project && !loadError)) return <Loading />;
  if (lookups.error || loadError) return <ErrorAlert error={lookups.error || loadError} />;
  const [meta, , rateCards, jobCatalog, crmUsers, approvers] = lookups.data!;

  const actions = project?.allowed_actions ?? [];
  if (project && !actions.includes("edit")) {
    const owner = project.current_version.crm_user;
    const reason =
      owner.id !== user?.id
        ? `Only ${owner.full_name}, the project's CRM / Creator, can edit it.`
        : project.status === "PENDING_APPROVAL"
          ? "It is pending approval."
          : "It is locked.";
    return (
      <section>
        <Alert kind="warning" title="This project cannot be edited">
          {reason} <Link to={`/projects/${project.id}`}>View project</Link>
        </Alert>
      </section>
    );
  }

  const version = project?.current_version;
  const editingApproved = version?.status === "APPROVED";
  const canSubmit = actions.includes("submit") || actions.includes("resubmit");

  return (
    <section>
      <div className="page-header">
        <div>
          <h1>{isNew ? "New Project" : `Edit ${project!.project_code}`}</h1>
          {version && (
            <p className="muted">
              Version v{version.version_number} · <StatusBadge status={version.status} />
            </p>
          )}
        </div>
        {project && <Link to={`/projects/${project.id}`} className="btn">View project</Link>}
      </div>

      {editingApproved && (
        <Alert kind="info" title="Editing an approved project">
          Saving changes (including contract changes) creates a new draft version v{version!.version_number + 1}. The current approved
          version stays active until the new version is approved.
        </Alert>
      )}
      {version?.status === "REJECTED" && version.last_decision?.comment && (
        <Alert kind="error" title={`Rejected by ${version.last_decision.decided_by?.full_name ?? "approver"}`}>
          <p className="pre">{version.last_decision.comment}</p>
          Correct the configuration and resubmit.
        </Alert>
      )}
      {notice && <Alert kind="success">{notice}</Alert>}
      <ErrorAlert error={actionError} />

      <div className="card">
        <Tabs
          active={tab}
          onChange={setTab}
          tabs={[
            { key: "basic", label: "Basic Information", invalid: tabHasErrors("basic", errors) },
            { key: "client", label: "Client", invalid: tabHasErrors("client", errors) },
            { key: "contracts", label: "Contracts", badge: version?.contracts.length, invalid: tabHasErrors("contracts", errors) },
            { key: "jobs", label: "Job Categories & Rate Cards", badge: values.job_categories.length, invalid: tabHasErrors("jobs", errors) },
          ]}
        />
        <div className="tab-panel">
          {tab === "basic" && (
            <BasicInfoTab values={values} errors={errors} isNew={isNew} meta={meta} crmUsers={crmUsers} approvers={approvers} onChange={change} />
          )}
          {tab === "client" && (
            <ClientTab
              clients={clients}
              clientId={values.client_id}
              error={errors.client_id}
              meta={meta}
              onChange={(cid) => change("client_id", cid)}
              onClientSaved={(c) => {
                setClients((list) => [...list.filter((x) => x.id !== c.id), c].sort((a, b) => a.legal_entity_name.localeCompare(b.legal_entity_name)));
                change("client_id", c.id);
              }}
            />
          )}
          {tab === "contracts" &&
            (project ? (
              <div>
                {errors.contracts && <div className="error-text block">{errors.contracts}</div>}
                <ContractTable
                  contracts={version!.contracts}
                  onDelete={async (c) => {
                    await contractsApi.remove(c.id);
                    await onContractsChanged(`Deleted "${c.file_name}".`);
                  }}
                />
                <ContractUploadForm projectId={project.id} meta={meta} onUploaded={() => onContractsChanged("Contract uploaded.")} />
              </div>
            ) : (
              <Alert kind="info" title="Save the draft first">
                Contract documents can be uploaded once the project draft has been saved.
              </Alert>
            ))}
          {tab === "jobs" && (
            <JobCategoriesTab
              rows={values.job_categories}
              errors={errors}
              catalog={jobCatalog}
              rateCards={rateCards}
              onChange={(rows) => change("job_categories", rows)}
            />
          )}
        </div>
      </div>

      {project && <ReadinessPanel readiness={readiness} stale={dirty} />}

      <div className="form-actions sticky-actions">
        <Link to={project ? `/projects/${project.id}` : "/projects"} className="btn">Cancel</Link>
        <button type="button" className="btn" disabled={!!busy || (!isNew && !dirty)} onClick={onSaveDraft}>
          {busy === "save" ? "Saving…" : isNew ? "Save Draft" : "Save Changes"}
        </button>
        {project && canSubmit && (
          <button type="button" className="btn btn-primary" disabled={!!busy} onClick={onSubmit}>
            {busy === "submit" ? "Submitting…" : project.status === "REJECTED" ? "Save & Resubmit" : "Save & Submit for Approval"}
          </button>
        )}
      </div>
    </section>
  );
}
