# Project Setup & Approval Workflow

A full-stack application for configuring client projects and routing them through an approval workflow:

- **React + TypeScript** frontend
- **Python (FastAPI) REST API** that runs locally under uvicorn and on **AWS Lambda** behind **API Gateway**
- **PostgreSQL** database (local Docker / Amazon RDS)
- Contract document storage on **local disk** in development and **Amazon S3** on AWS
- **Role-based authentication**: local JWT login in development, **Amazon Cognito** on AWS

> **Deployment status:** Phase 1 (local implementation) only. Nothing has been deployed and no AWS
> credentials are used anywhere in this repository. `infra/template.yaml` describes the AWS stack but
> must not be deployed until the code has been reviewed and credentials are supplied (see [§10](#10-aws-deployment-future-phase)).

---

## Table of contents

1. [Project overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Project structure](#3-project-structure)
4. [Local setup](#4-local-setup)
5. [Environment variables](#5-environment-variables)
6. [API documentation](#6-api-documentation)
7. [Test credentials](#7-test-credentials)
8. [Database schema](#8-database-schema)
9. [Approval workflow & versioning](#9-approval-workflow--versioning)
10. [AWS deployment (future phase)](#10-aws-deployment-future-phase)
11. [Testing](#11-testing)
12. [Security notes](#12-security-notes)
13. [Design decisions & known limitations](#13-design-decisions--known-limitations)

---

## 1. Project overview

There are two roles:

| Role | Can do |
|---|---|
| **CRM (project creator)** | Create and edit clients. Create and edit projects. Upload, view, download and delete contracts. Define job categories and map them to rate cards. Submit for approval. Edit and resubmit rejected projects. Update approved projects, which creates a new version. View status, version history, approval history and the audit trail. |
| **Approver (reviewer)** | View projects pending their approval. View the complete configuration of any project or version. Approve. Reject with a mandatory comment. Review resubmissions. **Cannot edit anything.** |

A project has four configuration sections: **Basic Information**, **Client**, **Contracts** and
**Job Categories & Rate Cards**. A project can only be submitted when every mandatory field is filled,
at least one contract is attached, and every job category is mapped to a rate card. The backend
enforces these rules on every submission; the frontend shows the same checks as guidance.

Approved configurations are **never overwritten**. Editing an approved project creates a new draft
version. The approved version stays active until the new version is approved.

---

## 2. Architecture

```text
                    ┌──────────────────────────┐
                    │  React UI (Vite, TS)     │   local: http://localhost:5173
                    │  S3 + CloudFront on AWS  │
                    └────────────┬─────────────┘
                                 │ HTTPS + Bearer token
                                 ▼
                    ┌──────────────────────────┐
                    │  API Gateway (REST)      │◄────── Cognito authorizer validates the ID token
                    └────────────┬─────────────┘        ┌───────────────┐
                                 │                      │   Cognito     │
                                 ▼                      │   User Pool   │
                    ┌──────────────────────────┐        └───────────────┘
                    │  AWS Lambda (Python)     │   local: uvicorn on :8000
                    │  FastAPI + Mangum        │   (same application code)
                    └──────┬────────────┬──────┘
          private subnets  │            │  S3 gateway endpoint
                           ▼            ▼
              ┌────────────────┐  ┌────────────────┐
              │ RDS PostgreSQL │  │  S3 contracts  │   local: ./storage on disk
              │ (password in   │  │  bucket        │
              │ Secrets Mgr)   │  └────────────────┘
              └────────────────┘
```

**Backend layering** (`backend/app`):

```text
api/routes  →  services  →  repositories  →  models (SQLAlchemy)
   │              │
   │              ├── policies.py      single source of truth for workflow/permission rules
   │              ├── validation.py    submission-readiness rules
   │              └── storage/         StorageService protocol → LocalStorage | S3Storage
   └── schemas (Pydantic) for request/response validation
```

- **Environment switching is configuration-only.** `STORAGE_BACKEND=local|s3`, `AUTH_MODE=local|cognito`,
  and either `DATABASE_URL` or `DB_HOST`/`DB_NAME`/`DB_SECRET_ARN`. AWS-specific code is limited to
  `storage/s3.py`, `db.py` (reading the RDS secret) and `security/auth_provider.py` (reading Cognito claims).
- **Same code locally and on Lambda.** `app/main.py` is the FastAPI app. `app/lambda_handler.py` wraps it with Mangum.
- **Authorization is enforced on the backend.** Every route has a role guard, and services check roles and
  workflow state again. The UI uses `allowed_actions` from the API to decide which buttons to show, so it
  never re-implements the rules.

---

## 3. Project structure

```text
project-root/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI app factory (CORS, error handlers, routers)
│   │   ├── lambda_handler.py    AWS Lambda entry point (Mangum)
│   │   ├── migrate_handler.py   Run migrations (CLI locally, Lambda on AWS)
│   │   ├── seed.py              Roles, rate-card catalog, demo users/clients
│   │   ├── config.py            Environment-based settings
│   │   ├── db.py                Engine/session; builds the RDS URL from Secrets Manager on AWS
│   │   ├── errors.py            Domain exceptions → consistent error envelope
│   │   ├── models/              SQLAlchemy models (users, clients, catalog, projects, approvals, audit)
│   │   ├── schemas/             Pydantic request/response schemas
│   │   ├── repositories/        Data-access queries
│   │   ├── services/            Business logic: projects/versioning, workflow, contracts, clients, audit
│   │   ├── security/            Password hashing, JWTs, auth providers (local / Cognito)
│   │   ├── storage/             File storage abstraction (local disk / S3)
│   │   ├── reference/           catalog.json – configurable rate cards, job categories, picklists
│   │   └── api/                 Routes, dependencies (auth, role guards), error handlers
│   ├── migrations/              Alembic migrations
│   ├── tests/                   pytest suite (business rules, workflow, versioning, audit, migration)
│   ├── requirements.txt         Runtime dependencies (packaged into Lambda)
│   ├── requirements-dev.txt     + uvicorn, pytest, httpx
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/                 HTTP client (error handling, auth header) and typed API services
│   │   ├── auth/                AuthContext, route guards, Cognito sign-in
│   │   ├── components/          Layout, Field, Tabs, Modal, StatusBadge, ContractTable, ClientForm…
│   │   ├── pages/               Projects list/detail/form, Approvals, Clients, Login
│   │   │   ├── project-form/    Tab components and the form model with client-side validation
│   │   │   └── project-detail/  Version view, version history, approval history, audit trail, action modal
│   │   ├── hooks/               useAsync, useDebounced
│   │   ├── types/api.ts         Types mirroring backend schemas
│   │   └── utils/               Formatting and validation helpers
│   └── .env.example
├── infra/
│   └── template.yaml            AWS SAM / CloudFormation stack (NOT deployed)
├── docker-compose.yml           Local PostgreSQL
└── README.md
```

---

## 4. Local setup

**Prerequisites:** Python 3.12+ (Lambda runs 3.12; also tested locally on 3.15), Node.js 20+, and Docker (for PostgreSQL).

### 4.1 Start PostgreSQL

```bash
docker compose up -d postgres
```

This starts PostgreSQL 17 on `localhost:5432` with database `crm_projects` and throwaway local credentials `crm_local` / `crm_local_password`.

### 4.2 Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env          # Windows: copy .env.example .env
# Edit .env and set JWT_SECRET to a long random string, e.g.:
#   python -c "import secrets; print(secrets.token_urlsafe(48))"

# Create the schema and seed roles, rate cards, job categories, demo users and clients
python -m app.migrate_handler --seed

# Start the API on http://localhost:8000 (interactive docs at /docs)
uvicorn app.main:app --reload --port 8000
```

Migrations only: `python -m app.migrate_handler` (or `alembic upgrade head`). The seed is idempotent and safe to re-run.

### 4.3 Frontend

```bash
cd frontend
npm install
cp .env.example .env.local    # defaults point at http://localhost:8000 with local auth
npm run dev                   # http://localhost:5173
```

`npm run build` type-checks and builds a production bundle into `frontend/dist`.

### 4.4 Run the tests

```bash
cd backend
pytest
```

The tests use in-memory SQLite, so they need neither Docker nor AWS.

---

## 5. Environment variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_ENV` | | `local` | `local`, `test` or `aws`. `aws` tunes the connection pool for Lambda. |
| `DATABASE_URL` | local | – | SQLAlchemy URL, e.g. `postgresql+psycopg://user:pass@localhost:5432/crm_projects` |
| `DB_HOST` / `DB_PORT` / `DB_NAME` | AWS | `5432` | RDS endpoint. Used when `DATABASE_URL` is empty. |
| `DB_SECRET_ARN` | AWS | – | ARN of the RDS-managed Secrets Manager secret holding the username and password |
| `AUTH_MODE` | | `local` | `local` (users table + JWT) or `cognito` (API Gateway Cognito authorizer) |
| `JWT_SECRET` | local auth | – | HMAC secret for session and download tokens. **Required** when `AUTH_MODE=local` or `STORAGE_BACKEND=local`. |
| `JWT_EXPIRES_MINUTES` | | `480` | Session token lifetime |
| `COGNITO_USER_POOL_ID` / `COGNITO_CLIENT_ID` | cognito | – | Cognito identifiers (informational; token validation happens in API Gateway) |
| `STORAGE_BACKEND` | | `local` | `local` (disk) or `s3` |
| `LOCAL_STORAGE_DIR` | | `./storage` | Directory for uploaded files when `STORAGE_BACKEND=local` |
| `PUBLIC_API_URL` | | `http://localhost:8000` | Base URL used to build local download links |
| `S3_BUCKET_NAME` | s3 | – | Contracts bucket |
| `AWS_REGION` | AWS | – | Set automatically by the Lambda runtime |
| `DOWNLOAD_URL_EXPIRES_SECONDS` | | `300` | Lifetime of presigned or signed download URLs |
| `MAX_UPLOAD_MB` | | `5` | Maximum contract file size. Keep ≤ 5 on AWS because of API Gateway payload limits. |
| `CORS_ORIGINS` | | `http://localhost:5173` | Comma-separated allowed browser origins |
| `SEED_DEMO_PASSWORD` | | `Password123!` | Password given to local demo users by the seed |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | API base URL (the API Gateway stage URL on AWS) |
| `VITE_AUTH_MODE` | `local` | `local` or `cognito`. Must match the backend. |
| `VITE_COGNITO_REGION` | – | Cognito region (cognito mode) |
| `VITE_COGNITO_USER_POOL_ID` | – | User pool ID (public identifier) |
| `VITE_COGNITO_CLIENT_ID` | – | App client ID (public identifier, no secret) |

The frontend never receives database credentials or AWS keys.

---

## 6. API documentation

Interactive OpenAPI docs are served at **`http://localhost:8000/docs`** when the backend is running.

### Conventions

- **Authentication:** every endpoint except `POST /auth/login`, `GET /health` and `GET /files/{token}`
  requires `Authorization: Bearer <token>`. Locally the token comes from `/auth/login`. On AWS it is
  the Cognito **ID token**.
- **Errors** always use one envelope:

  ```json
  { "error": { "code": "VALIDATION_FAILED", "message": "Project is not ready to be submitted for approval",
               "details": [ { "field": "contracts", "message": "Upload at least one contract document" } ] } }
  ```

  | Status | Code | Meaning |
  |---|---|---|
  | 401 | `UNAUTHENTICATED` | Missing, invalid or expired token |
  | 403 | `FORBIDDEN` | Wrong role, or not the assigned approver |
  | 404 | `NOT_FOUND` | Unknown resource |
  | 409 | `CONFLICT` | Invalid workflow transition, e.g. editing a project pending approval, or a duplicate Project ID |
  | 422 | `VALIDATION_FAILED` | Input validation or submission-readiness failure. `details` lists each field. |

- **Statuses:** `DRAFT`, `PENDING_APPROVAL`, `REJECTED`, `APPROVED`.

### Authentication

| Method | Endpoint | Role | Request | Response |
|---|---|---|---|---|
| POST | `/auth/login` | public | `{ "email", "password" }` | `{ access_token, token_type, expires_in, user: {id, email, full_name, role} }`. Local auth mode only. |
| GET | `/auth/me` | any | – | Current user `{ id, email, full_name, role }` |

### Clients

| Method | Endpoint | Role | Request | Response |
|---|---|---|---|---|
| GET | `/clients?search=` | any | – | `Client[]` |
| GET | `/clients/{id}` | any | – | `Client` |
| POST | `/clients` | CRM | `ClientInput` | `201 Client` |
| PUT | `/clients/{id}` | CRM | `ClientInput` | `Client` |

`ClientInput`:
```json
{ "legal_entity_name": "Acme Technologies Pvt Ltd", "registered_address": "…", "billing_address": "…",
  "mode_of_payment": "Bank Transfer", "gst_number": "29ABCDE1234F1Z5", "billing_currency": "INR",
  "primary_contact": { "name": "…", "designation": "…", "phone": "+91 98450 12345", "email": "…" } }
```
`gst_number` is optional (validated as a GSTIN when given). `mode_of_payment` and `billing_currency` must come from the catalog (`GET /meta`).

### Projects

| Method | Endpoint | Role | Request | Response |
|---|---|---|---|---|
| GET | `/projects?status=&client_id=&created_by=&search=` | any | – | `ProjectSummary[]`: `id, project_code, name, client, status, current_version_number, active_version_number, created_by, created_at, updated_at, can_edit` |
| POST | `/projects` | CRM | `ProjectCreate` | `201 ProjectDetail` (version 1, `DRAFT`) |
| GET | `/projects/{id}` | any | – | `ProjectDetail`: `current_version` (latest), `active_version` (approved, in effect), `allowed_actions` for the caller |
| PUT | `/projects/{id}` | CRM | `ProjectUpdate` | `ProjectDetail`. Draft or Rejected: updated in place. Approved: **creates a new draft version**. Pending: `409`. |
| GET | `/projects/{id}/readiness` | any | – | `{ ready, issues: [{field, message}] }` for the latest version |
| GET | `/projects/{id}/versions` | any | – | `VersionSummary[]` (newest first), each with `changes: [{field, label, old, new}]` against the version it was based on |
| GET | `/projects/{id}/versions/{n}` | any | – | Full configuration of version *n* |
| GET | `/projects/{id}/approvals` | any | – | Approval history: submissions, decisions, comments |
| GET | `/projects/{id}/audit` | any | – | Audit events (newest first) |

`ProjectCreate` (drafts may be saved incomplete; completeness is checked on submit):
```json
{ "project_code": "PRJ-2026-001", "name": "Payments Platform", "start_date": "2026-01-01", "end_date": "2026-12-31",
  "client_id": 1, "business_unit": "Digital Engineering", "crm_user_id": 1, "approver_id": 3,
  "job_categories": [ { "name": "Software Developer", "job_category_id": 1, "rate_card_id": 1 } ] }
```
`ProjectUpdate` has the same fields without `project_code` (which cannot change), plus an optional `change_note` that is recorded in the audit trail. `PUT` is a full replacement.

### Workflow

| Method | Endpoint | Role | Request | Transition |
|---|---|---|---|---|
| POST | `/projects/{id}/submit` | CRM | `{ "comment"?: string }` | `DRAFT → PENDING_APPROVAL` (readiness enforced, `422` with issues otherwise) |
| POST | `/projects/{id}/resubmit` | CRM | `{ "comment"?: string }` | `REJECTED → PENDING_APPROVAL` (readiness enforced) |
| GET | `/approvals/pending` | APPROVER | – | Requests assigned to the caller: `[{ approval_id, project, version_number, is_resubmission, submitted_by, submitted_at }]` |
| POST | `/projects/{id}/approve` | APPROVER (assigned) | `{ "comment"?: string }` | `PENDING_APPROVAL → APPROVED`. The version becomes active and the previous active version is deactivated. |
| POST | `/projects/{id}/reject` | APPROVER (assigned) | `{ "comment": string }` (**required**) | `PENDING_APPROVAL → REJECTED` |

All workflow endpoints return the updated `ProjectDetail`.

### Contracts

| Method | Endpoint | Role | Request | Response |
|---|---|---|---|---|
| POST | `/projects/{id}/contracts` | CRM | `multipart/form-data`: `document_type`, `valid_from`, `valid_till`, `file` | `201 Contract`. On an approved project this creates a new draft version. |
| GET | `/projects/{id}/contracts?version=` | any | – | Contracts of the latest version, or of version *n* |
| GET | `/contracts/{id}` | any | – | Contract metadata |
| GET | `/contracts/{id}/download-url?disposition=inline\|attachment` | any | – | `{ url, expires_in }`. A presigned S3 URL on AWS, a signed local link in development. Use `inline` to view and `attachment` to download. |
| DELETE | `/contracts/{id}` | CRM | – | `204`. Only allowed on the latest version; on an approved project it creates a new draft version without the file. |
| GET | `/files/{token}` | token | – | Serves the file (local storage backend only) |

Uploads are checked for allowed extension (`.pdf .doc .docx .png .jpg .jpeg`), MIME type, file signature ("magic bytes"), non-empty content, size limit, document type and date order.

### Catalog & lookups

| Method | Endpoint | Role | Response |
|---|---|---|---|
| GET | `/rate-cards` | any | `[{ id, code, name, description, currency }]` |
| GET | `/job-categories` | any | `[{ id, name, default_rate_card }]` |
| GET | `/users?role=CRM\|APPROVER` | any | `[{ id, full_name, email }]` for user pickers |
| GET | `/meta` | any | Business units, payment modes, currencies, document types, allowed file types, max upload size, auth mode |
| GET | `/health` | public | `{ "status": "ok" }` |

The rate-card catalog, standard job categories and picklists are configured in
[`backend/app/reference/catalog.json`](backend/app/reference/catalog.json). Re-run the seed after editing it.

---

## 7. Test credentials

Created by `python -m app.migrate_handler --seed` **for local development only**:

| Role | Email | Password |
|---|---|---|
| CRM | `crm@example.com` (Priya Sharma) | `Password123!` |
| CRM | `crm2@example.com` (Arjun Mehta) | `Password123!` |
| Approver | `approver@example.com` (Rahul Verma) | `Password123!` |
| Approver | `approver2@example.com` (Neha Kapoor) | `Password123!` |

These are mock accounts on `example.com`. Override the password with `SEED_DEMO_PASSWORD`. Two sample
clients are also seeded. On AWS, users are created in Cognito and matched to database rows by email.

---

## 8. Database schema

```text
roles ──< users
              │ created_by / updated_by
clients ◄─────┤
              │
projects ─────┤ created_by                     rate_cards ──< job_categories (catalog, default rate card)
   │                                               ▲               ▲
   └──< project_versions ── client_id ──► clients  │               │
          │  status, is_active, version_number      │               │
          │  name, dates, business_unit,            │               │
          │  crm_user_id, approver_id ──► users     │               │
          │  based_on_version_id ──► project_versions (self)        │
          ├──< project_job_categories ── rate_card_id ──────────────┘ (and job_category_id)
          ├──< contracts (document_type, validity, file metadata, storage_key)
          └──< approval_requests (status, submitted_by, approver, decided_by, timestamps, is_resubmission)
                     └──< approval_comments (kind: SUBMISSION | APPROVAL | REJECTION, text, author)

audit_events (project_id, version_id, client_id, user_id, action, comment, details JSON, created_at)
```

| Table | Purpose / notes |
|---|---|
| `roles`, `users` | `CRM` / `APPROVER`. `password_hash` (PBKDF2) is used only in local auth mode. |
| `clients` | Legal entity, addresses, payment mode, GST, currency, primary contact. Legal entity name is unique. |
| `rate_cards`, `job_categories` | Configurable catalog seeded from `catalog.json` |
| `projects` | Stable identity: unique `project_code`, creator, `latest_version_number` |
| `project_versions` | All configuration. Unique `(project_id, version_number)`. **Partial unique index** guarantees at most one `is_active` version per project. |
| `project_job_categories` | Job categories of a version and their rate-card mapping |
| `contracts` | Per-version document metadata. Rows copied into a new version share the same `storage_key` (no file duplication). A file is deleted only when no row references it. |
| `approval_requests`, `approval_comments` | Every submission and its decision, with comments (rejection reason, approval note, submission note) |
| `audit_events` | Append-only log, indexed by `(project_id, created_at)` |

Indexes cover foreign keys used in filters (`client_id`, `approver_id`, `created_by_id`), `status`,
`(approver_id, status)` for the approver inbox, and `storage_key`.

Migrations live in `backend/migrations`. A test verifies that the migration produces exactly the schema the ORM models describe.

---

## 9. Approval workflow & versioning

### Status transitions

```text
              submit                     approve
  Draft ───────────────► Pending Approval ───────────► Approved (active)
                               │
                               │ reject (comment required)
                               ▼
                           Rejected ──── edit (in place) ────┐
                               ▲                             │
                               └──────── resubmit ◄──────────┘
                                   (→ Pending Approval)
```

- **Submit / Resubmit** are allowed only for the CRM role and only when the readiness rules pass:
  all mandatory fields set, end date ≥ start date, approver has the approver role, ≥ 1 contract,
  ≥ 1 job category, and every job category mapped to a rate card.
- **Pending Approval** locks the project. Edits and contract changes return `409`.
- **Approve / Reject** are allowed only for the **assigned** approver. Rejection requires a comment.
- Every transition creates an `approval_requests` / `approval_comments` record and audit events.

### Updating an approved project (versioning)

```text
v1  Approved  Active ──── CRM saves a change ────► v2  Draft             (copy of v1 + changes)
                                                  │  submit
                                                  ▼
v1  Approved  Active                              v2  Pending Approval
                                                  │  approve
                                                  ▼
v1  Approved  inactive                            v2  Approved  Active
```

- The edit is applied to a **new version** (`based_on_version_id = v1`). v1 is never modified.
- Later edits update the same draft until it is submitted.
- If v2 is rejected, v1 **stays active**. The CRM fixes v2 and resubmits.
- Uploading or deleting a contract on an approved project also creates the new draft version.
- Saving an approved project with no changes is rejected (`422`), so no empty versions are created.
- On approval, the previous active version is deactivated and the new one activated in the same transaction.

The project detail page shows the current version, the active version, the configuration of any past
version, a version history with field-level changes, the approval history and the audit trail.

### Audit events

`PROJECT_CREATED`, `PROJECT_UPDATED` (with field-level changes and an optional change note),
`CONTRACT_UPLOADED`, `CONTRACT_DELETED`, `SUBMITTED_FOR_APPROVAL`, `APPROVAL_ASSIGNED`,
`PROJECT_APPROVED`, `PROJECT_REJECTED`, `PROJECT_RESUBMITTED`, `NEW_VERSION_CREATED`,
`VERSION_ACTIVATED`, `CLIENT_CREATED`, `CLIENT_UPDATED`.

Each event stores an event ID, project ID, version ID (and number), user, action, timestamp,
comment and structured details. Events are written in the same transaction as the change they
describe, so a failed action leaves no audit record.

---

## 10. AWS deployment (future phase)

> ⚠️ **Not performed yet.** This happens only after the code has been reviewed and AWS credentials
> have been provided and approved. No AWS calls have been made, and the repository contains no credentials.

### What `infra/template.yaml` creates

| Resource | Notes |
|---|---|
| VPC with 2 private subnets | No NAT gateway. S3 is reached through a gateway endpoint and Secrets Manager through an interface endpoint. |
| `AWS::RDS::DBInstance` (PostgreSQL 17) | Private, encrypted. `ManageMasterUserPassword` generates the password and stores it in Secrets Manager. Snapshot on delete. |
| `AWS::S3::Bucket` (contracts) | Private, SSE, versioned, TLS-only bucket policy, retained on stack delete |
| `AWS::Cognito::UserPool` + client | Admin-created users, strong password policy, public SPA client (no secret) |
| `AWS::Serverless::Api` | Cognito authorizer by default, CORS restricted to the CloudFront origin, `multipart/form-data` binary support |
| `AWS::Serverless::Function` ×2 | `ApiFunction` (FastAPI via Mangum) and `MigrationFunction` (Alembic). Least-privilege IAM: the RDS secret, S3 `projects/*` objects, VPC access. |
| S3 + CloudFront (frontend) | Private bucket with Origin Access Control and SPA error routing |

Lambda configuration is passed as environment variables derived from stack resources. The template
contains no access keys or passwords. The template passes `cfn-lint` (run offline).

### Planned steps (once approved)

1. Configure credentials securely (e.g. `aws configure sso` or a named profile, never committed). Verify with `aws sts get-caller-identity`.
2. Build and deploy the backend stack from a clean checkout, so that `backend/.venv`, `tests/` and `storage/` aren't packaged:
   ```bash
   sam build --template-file infra/template.yaml --use-container
   sam deploy --guided --stack-name crm-projects-dev --capabilities CAPABILITY_IAM
   ```
3. Run database migrations and seed reference data inside the VPC:
   ```bash
   aws lambda invoke --function-name <MigrationFunctionName> --payload '{"seed": true}' --cli-binary-format raw-in-base64-out out.json
   ```
4. Create the Cognito users (CRM / approver) and the matching rows in `users` with the same email and role. The seed's `demo_users` option can create the database rows.
5. Build the frontend with the stack outputs and publish it:
   ```bash
   VITE_API_BASE_URL=<ApiUrl> VITE_AUTH_MODE=cognito VITE_COGNITO_REGION=<region> \
   VITE_COGNITO_USER_POOL_ID=<UserPoolId> VITE_COGNITO_CLIENT_ID=<UserPoolClientId> npm run build
   aws s3 sync frontend/dist s3://<FrontendBucketName> --delete
   aws cloudfront create-invalidation --distribution-id <FrontendDistributionId> --paths "/*"
   ```
6. Run the complete workflow against the deployed URL (`FrontendUrl`).

### Frontend hosting fallback (`FrontendHosting` parameter)

New AWS accounts can't create CloudFront distributions until AWS Support verifies them
("Your account must be verified before you can add new CloudFront resources"). Until then, deploy with
`FrontendHosting=s3website`. The frontend bucket is then served from its public S3 website endpoint
(HTTP only, public-read policy, ACLs still blocked), and API CORS automatically targets that origin.
Once the account is verified, redeploy with `FrontendHosting=cloudfront` (the default) to switch back to the
private bucket and CloudFront/HTTPS. In website mode there's no CloudFront invalidation step.

### Building without SAM CLI / Docker

With only Python 3.13+ locally, `sam build` can't build the `python3.12` function. Use this alternative instead:
copy `backend/app`, `backend/migrations` and `backend/alembic.ini` into a build folder. Install the dependencies there
with `pip install -r backend/requirements.txt --platform manylinux2014_aarch64 --implementation cp --python-version 3.12 --only-binary=:all: --target <build>`,
then point `CodeUri` at that folder and run `aws cloudformation package` + `aws cloudformation deploy --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND`.

---

## 11. Testing

`cd backend && pytest` runs 61 tests covering:

| Area | Examples |
|---|---|
| Auth & clients | login, invalid credentials, missing token, role guards, client validation (GSTIN, email), duplicates |
| Project creation | required fields, unique Project ID, date order, client selection populates details, unknown client, approver role, unknown rate card, duplicate job categories, readiness report, listing filters |
| Submission | incomplete project, no contract, no job categories, unmapped rate card, valid submission → Pending Approval, pending project locked |
| Approval | approver approves (decision recorded), rejects with comment, rejection requires comment, CRM cannot approve, unassigned approver cannot decide, cannot approve a draft |
| Rejection | CRM edits rejected project in place, must use resubmit, resubmission re-validated, approval history |
| Versioning | update to approved creates v2 draft, v1 unchanged and active, edits reuse the draft, v2 requires approval, approved v2 becomes active, rejected v2 keeps v1 active, field-level changes, no-op update rejected, contract upload/delete on approved project |
| Contracts | upload/view/download, signed URL required, type/signature/empty/date/document-type validation, delete, historical versions immutable |
| Audit | full lifecycle event sequence, event contents, field changes, failed actions not audited |
| Migrations | Alembic upgrade matches the ORM models exactly; downgrade works |

---

## 12. Security notes

- No AWS keys, secrets or passwords are committed. `.env` files are git-ignored and only `.env.example` files with placeholders are included.
- Lambda uses its **IAM execution role**. The DB password is generated and held by RDS and Secrets Manager, and read at runtime.
- **Backend authorization on every endpoint:** route-level role guards, service-level checks, and assigned-approver enforcement.
- **Input validation:** Pydantic schemas (formats, lengths, date order), reference checks (client, users, rate cards) and readiness rules.
- **Upload validation:** extension allow-list, MIME check, magic-byte signature, size limit, sanitized file names, random storage keys, path-traversal protection.
- **Downloads** use short-lived URLs (presigned S3 or signed local tokens) with `nosniff` and `no-store` headers.
- All queries go through the SQLAlchemy ORM, so they are parameterized.
- Passwords (local mode) are hashed with PBKDF2-SHA256 (390k iterations) and compared in constant time.

---

## 13. Design decisions & known limitations

- **FastAPI + Mangum** lets the same ASGI app run under uvicorn locally and in Lambda, with no separate code paths.
- **Version-centric model:** all configuration lives on immutable-once-submitted `project_versions`. This makes "never overwrite the approved version" structural, not a convention.
- **Cognito validation at API Gateway:** Lambda reads verified claims from the request context, so it needs no internet egress and no NAT gateway. Roles stay in the database, so authorization does not depend on the identity provider.
- **Uploads go through the API** (≤ 5 MB, an API Gateway limit). For larger files the S3 storage service could issue presigned PUT URLs instead. The storage abstraction already isolates this change.
- **Client master data is shared:** project versions reference clients by ID, so editing a client's details is reflected in every version that references it.
- **List endpoints are not paginated**, which is acceptable at assignment scale. Add `limit`/`offset` before production use.
- **Local tests use SQLite** so they run anywhere. The schema avoids PostgreSQL-only features apart from JSONB and partial indexes, which have SQLite equivalents.
