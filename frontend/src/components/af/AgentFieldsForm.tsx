import type { KeyboardEvent } from "react";
import { UploadCloud, X, Plus } from "lucide-react";
import type { FieldDef } from "@/types/api";

export function AgentFieldsForm({
  fields,
  values,
  onChange,
}: {
  fields: FieldDef[];
  values: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
}) {
  const set = (k: string, v: unknown) => onChange({ ...values, [k]: v });
  return (
    <div className="space-y-4">
      {fields.map((f) => (
        <FieldRenderer key={f.key} field={f} value={values[f.key]} onChange={(v) => set(f.key, v)} />
      ))}
    </div>
  );
}

function FieldRenderer({ field, value, onChange }: { field: FieldDef; value: unknown; onChange: (v: unknown) => void }) {
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between">
        <label className="text-[12px] font-medium">
          {field.label}
          {field.required && <span className="text-[color:var(--color-danger)] ml-0.5">*</span>}
        </label>
        {field.type === "slider" && (
          <span className="text-[10.5px] text-muted-foreground tabular-nums">{String(value ?? field.default ?? 0)}</span>
        )}
      </div>
      {field.description && <p className="text-[11px] text-muted-foreground -mt-0.5">{field.description}</p>}
      <FieldControl field={field} value={value} onChange={onChange} />
    </div>
  );
}

function FieldControl({ field, value, onChange }: { field: FieldDef; value: unknown; onChange: (v: unknown) => void }) {
  const baseInput =
    "w-full text-xs bg-background border border-border rounded-md px-2.5 py-1.5 outline-none focus:ring-2 ring-primary/30";
  switch (field.type) {
    case "text":
      return <input className={baseInput} placeholder={field.placeholder} value={String(value ?? "")} onChange={(e) => onChange(e.target.value)} />;
    case "textarea":
      return <textarea className={`${baseInput} min-h-[80px] font-mono`} placeholder={field.placeholder} value={String(value ?? "")} onChange={(e) => onChange(e.target.value)} />;
    case "number":
      return (
        <input type="number" className={baseInput} min={field.min} max={field.max} step={field.step ?? 1}
          value={value === "" || value === undefined ? "" : Number(value)}
          onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))} />
      );
    case "select":
      return (
        <select className={baseInput} value={String(value ?? "")} onChange={(e) => onChange(e.target.value)}>
          <option value="">Select...</option>
          {field.options?.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      );
    case "radio":
      return (
        <div className="grid grid-cols-2 gap-1.5">
          {field.options?.map((o) => {
            const active = value === o;
            return (
              <button key={o} type="button" onClick={() => onChange(o)}
                className={`text-[11.5px] px-2.5 py-1.5 rounded-md border transition ${active ? "border-primary bg-primary/10 text-primary font-medium" : "border-border bg-background hover:border-primary/40"}`}>
                {o}
              </button>
            );
          })}
        </div>
      );
    case "multiselect": {
      const arr = Array.isArray(value) ? (value as string[]) : [];
      const toggle = (opt: string) => arr.includes(opt) ? onChange(arr.filter((x) => x !== opt)) : onChange([...arr, opt]);
      return (
        <div className="flex flex-wrap gap-1.5">
          {field.options?.map((o) => {
            const active = arr.includes(o);
            return (
              <button key={o} type="button" onClick={() => toggle(o)}
                className={`text-[11px] px-2 py-1 rounded-full border transition ${active ? "border-primary bg-primary/10 text-primary" : "border-border bg-background text-muted-foreground hover:border-primary/40"}`}>
                {o}
              </button>
            );
          })}
        </div>
      );
    }
    case "slider":
      return (
        <input type="range" className="w-full accent-[color:var(--color-primary)]"
          min={field.min ?? 0} max={field.max ?? 100} step={field.step ?? 1}
          value={Number(value ?? field.default ?? 0)} onChange={(e) => onChange(Number(e.target.value))} />
      );
    case "file": {
      const filename = typeof value === "string" ? value : "";
      return (
        <label className="flex items-center gap-2 px-3 py-3 rounded-md border border-dashed border-border bg-background hover:border-primary cursor-pointer text-[11.5px] text-muted-foreground">
          <UploadCloud size={14} />
          <div className="flex-1 truncate">{filename ? <span className="text-foreground">{filename}</span> : "Click to upload or drag and drop"}</div>
          <input type="file" className="hidden" onChange={(e) => onChange(e.target.files?.[0]?.name ?? "")} />
        </label>
      );
    }
    case "tags": {
      const arr = Array.isArray(value) ? (value as string[]) : [];
      const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
        const t = e.currentTarget;
        if (e.key === "Enter" && t.value.trim()) {
          e.preventDefault();
          onChange([...arr, t.value.trim()]);
          t.value = "";
        }
      };
      return (
        <div className="space-y-1.5">
          <div className="flex flex-wrap gap-1">
            {arr.map((t, i) => (
              <span key={`${t}-${i}`} className="inline-flex items-center gap-1 text-[11px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                {t}
                <button type="button" className="opacity-70 hover:opacity-100" onClick={() => onChange(arr.filter((_, idx) => idx !== i))}>
                  <X size={10} />
                </button>
              </span>
            ))}
          </div>
          <div className="flex items-center gap-1">
            <input className={baseInput} placeholder="Type and press Enter" onKeyDown={onKey} />
            <Plus size={14} className="text-muted-foreground" />
          </div>
        </div>
      );
    }
    case "toggle": {
      const checked = Boolean(value ?? field.default ?? false);
      return (
        <button
          type="button"
          onClick={() => onChange(!checked)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${checked ? "bg-primary" : "bg-border"}`}
        >
          <span className={`inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform ${checked ? "translate-x-6" : "translate-x-1"}`} />
        </button>
      );
    }
    default:
      return null;
  }
}
