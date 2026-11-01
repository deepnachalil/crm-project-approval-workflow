/**
 * Client-side form validation for immediate feedback. These checks mirror the
 * backend's *input* validation (formats, required-to-save fields). Submission
 * readiness (contracts, rate-card mapping, …) is evaluated by the backend via
 * GET /projects/{id}/readiness so those rules live in one place.
 */
export type Errors = Record<string, string>;

export const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
export const PHONE_RE = /^\+?[0-9][0-9\s\-()]{6,19}$/;
export const GST_RE = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
export const PROJECT_CODE_RE = /^[A-Z0-9][A-Z0-9_-]{2,31}$/;

export function required(value: unknown, message: string, errors: Errors, field: string) {
  if (value === null || value === undefined || (typeof value === "string" && !value.trim())) errors[field] = message;
}

export function dateOrder(start: string | null, end: string | null, errors: Errors, field: string, message: string) {
  if (start && end && end < start) errors[field] = message;
}

export const hasErrors = (errors: Errors) => Object.keys(errors).length > 0;
