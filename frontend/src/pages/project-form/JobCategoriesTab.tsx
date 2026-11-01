import { useId } from "react";
import type { JobCategory, RateCard } from "../../types/api";
import type { Errors } from "../../utils/validation";
import { newRow, type JobRow } from "./formModel";

interface Props {
  rows: JobRow[];
  errors: Errors;
  catalog: JobCategory[];
  rateCards: RateCard[];
  onChange: (rows: JobRow[]) => void;
}

export function JobCategoriesTab({ rows, errors, catalog, rateCards, onChange }: Props) {
  const listId = useId();

  function update(index: number, patch: Partial<JobRow>) {
    onChange(rows.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  }

  function setName(index: number, name: string) {
    const match = catalog.find((c) => c.name.toLowerCase() === name.trim().toLowerCase());
    const row = rows[index];
    update(index, {
      name,
      job_category_id: match?.id ?? null,
      // Pre-select the catalog's default rate card, but never overwrite a manual choice.
      rate_card_id: row.rate_card_id ?? match?.default_rate_card?.id ?? null,
    });
  }

  return (
    <div>
      <p className="muted">
        Define the job categories for this project and map each one to a rate card. Pick a standard category from the
        list or type a custom name.
      </p>
      {errors.job_categories && <div className="error-text block">{errors.job_categories}</div>}
      <datalist id={listId}>
        {catalog.map((c) => <option key={c.id} value={c.name} />)}
      </datalist>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Job Category</th>
              <th>Rate Card</th>
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={3} className="empty">No job categories defined.</td></tr>}
            {rows.map((r, i) => {
              const nameErr = errors[`job_categories[${i}].name`];
              const rcErr = errors[`job_categories[${i}].rate_card_id`];
              return (
                <tr key={r.key}>
                  <td data-label="Job Category">
                    <input
                      list={listId}
                      aria-label={`Job category ${i + 1}`}
                      aria-invalid={!!nameErr}
                      placeholder="e.g. Software Developer"
                      value={r.name}
                      onChange={(e) => setName(i, e.target.value)}
                    />
                    {nameErr && <div className="error-text">{nameErr}</div>}
                  </td>
                  <td data-label="Rate Card">
                    <select
                      aria-label={`Rate card for job category ${i + 1}`}
                      aria-invalid={!!rcErr}
                      value={r.rate_card_id ?? ""}
                      onChange={(e) => update(i, { rate_card_id: e.target.value ? Number(e.target.value) : null })}
                    >
                      <option value="">Select a rate card…</option>
                      {rateCards.map((rc) => <option key={rc.id} value={rc.id}>{rc.name} ({rc.currency})</option>)}
                    </select>
                    {rcErr && <div className="error-text">{rcErr}</div>}
                  </td>
                  <td className="actions">
                    <button type="button" className="btn btn-sm btn-danger" onClick={() => onChange(rows.filter((_, j) => j !== i))}>
                      Remove
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <button type="button" className="btn" onClick={() => onChange([...rows, newRow()])}>+ Add job category</button>
    </div>
  );
}
