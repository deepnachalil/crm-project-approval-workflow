export interface TabDef<K extends string> {
  key: K;
  label: string;
  badge?: string | number;
  invalid?: boolean;
  disabled?: boolean;
}

export function Tabs<K extends string>({ tabs, active, onChange }: { tabs: TabDef<K>[]; active: K; onChange: (k: K) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.key}
          role="tab"
          type="button"
          aria-selected={active === t.key}
          disabled={t.disabled}
          className={`tab${active === t.key ? " tab-active" : ""}${t.invalid ? " tab-invalid" : ""}`}
          onClick={() => onChange(t.key)}
        >
          {t.label}
          {t.badge !== undefined && <span className="tab-badge">{t.badge}</span>}
          {t.invalid && <span className="tab-dot" aria-label="has errors" />}
        </button>
      ))}
    </div>
  );
}
