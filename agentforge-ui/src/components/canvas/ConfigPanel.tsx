import { useWorkflowStore } from "@/store/workflowStore";
import { AGENT_REGISTRY } from "@/mocks/data";
import type { FieldDef } from "@/types/api";
import { useState, type KeyboardEvent } from "react";
import { Trash2, X, UploadCloud, Plus } from "lucide-react";

const TABS = ["Config", "Credentials", "Runtime", "Advanced"] as const;

export function ConfigPanel() {
  const selectedId = useWorkflowStore((s) => s.selectedNodeId);
  const node = useWorkflowStore((s) => s.nodes.find((n) => n.id === selectedId) || null);
  const updateNodeConfig = useWorkflowStore((s) => s.updateNodeConfig);
  const removeNode = useWorkflowStore((s) => s.removeNode);
  const [tab, setTab] = useState<typeof TABS[number]>("Config");

  if (!node) {
    return (
      <aside className="w-96 shrink-0 border-l border-border bg-surface flex items-center justify-center text-center p-6">
        <div>
          <div className="text-sm font-semibold mb-1">No agent selected</div>
          <p className="text-xs text-muted-foreground">Click any node on the canvas to configure it.</p>
        </div>
      </aside>
    );
  }

  const def = AGENT_REGISTRY.find((a) => a.type === node.data.agent)!;
  const config = node.data.config as Record<string, unknown>;

  return (
    <aside className="w-96 shrink-0 border-l border-border bg-surface flex flex-col">
      <div className="px-4 py-3 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <div className="text-[10.5px] uppercase tracking-wider text-muted-foreground">{def.type}</div>
            <h3 className="text-sm font-semibold truncate">{def.name}</h3>
          </div>
          <button
            onClick={() => removeNode(node.id)}
            className="h-8 w-8 grid place-items-center rounded-md hover:bg-danger/10 text-muted-foreground hover:text-[color:var(--color-danger)]"
            title="Delete node"
          >
            <Trash2 size={14} />
          </button>
        </div>
        <p className="text-[11px] text-muted-foreground mt-1">{def.description}</p>
      </div>

      <div className="px-2 pt-2 border-b border-border flex gap-0.5 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-2.5 py-1.5 text-[11.5px] rounded-t-md transition whitespace-nowrap ${
              tab === t ? "bg-primary/10 text-primary font-medium" : "text-muted-foreground hover:bg-muted"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {tab === "Config" && (
          <>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="rounded-md bg-muted p-2">
                <div className="text-muted-foreground">Inputs</div>
                <div className="font-medium mt-0.5">{def.inputs.join(", ")}</div>
              </div>
              <div className="rounded-md bg-muted p-2">
                <div className="text-muted-foreground">Outputs</div>
                <div className="font-medium mt-0.5">{def.outputs.join(", ")}</div>
              </div>
            </div>
            {def.fields.map((f) => (
              <FieldRenderer
                key={f.key}
                field={f}
                value={config[f.key]}
                onChange={(v) => updateNodeConfig(node.id, { [f.key]: v })}
              />
            ))}
          </>
        )}
        {tab === "Credentials" && (
          <div className="text-[11.5px] text-muted-foreground">
            Reference credentials inline using <code className="bg-muted px-1 rounded">{"${ENV_VAR}"}</code>. Manage secrets in the Credentials page.
          </div>
        )}
        {tab === "Runtime" && (
          <div className="space-y-3 text-[11.5px] text-muted-foreground">
            <div>Timeout, retries, and concurrency are inherited from workflow defaults.</div>
          </div>
        )}
        {tab === "Advanced" && (
          <pre className="text-[11px] bg-muted rounded p-2 overflow-auto">{JSON.stringify(config, null, 2)}</pre>
        )}
      </div>
    </aside>
  );
}

function FieldRenderer({ field, value, onChange }: { field: FieldDef; value: unknown; onChange: (v: unknown) => void }) {
  const labelEl = (
    <div className="flex items-baseline justify-between">
      <label className="text-[11.5px] font-medium">
        {field.label}
        {field.required && <span className="text-[color:var(--color-danger)] ml-0.5">*</span>}
      </label>
      {field.type === "slider" && (
        <span className="text-[10.5px] text-muted-foreground tabular-nums">{String(value ?? field.default ?? 0)}</span>
      )}
    </div>
  );

  return (
    <div className="space-y-1">
      {labelEl}
      {field.description && <p className="text-[10.5px] text-muted-foreground -mt-0.5">{field.description}</p>}
      <FieldControl field={field} value={value} onChange={onChange} />
    </div>
  );
}

function FieldControl({ field, value, onChange }: { field: FieldDef; value: unknown; onChange: (v: unknown) => void }) {
  const baseInput =
    "w-full text-xs bg-background border border-border rounded-md px-2.5 py-1.5 outline-none focus:ring-2 ring-primary/30";

  switch (field.type) {
    case "text":
      return (
        <input
          className={baseInput}
          placeholder={field.placeholder}
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
        />
      );
    case "textarea":
      return (
        <textarea
          className={`${baseInput} min-h-[80px] font-mono`}
          placeholder={field.placeholder}
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
        />
      );
    case "number":
      return (
        <input
          type="number"
          className={baseInput}
          min={field.min}
          max={field.max}
          step={field.step ?? 1}
          value={value === "" || value === undefined ? "" : Number(value)}
          onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
        />
      );
    case "select":
      return (
        <select
          className={baseInput}
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">Select...</option>
          {field.options?.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
      );
    case "radio":
      return (
        <div className="grid grid-cols-2 gap-1.5">
          {field.options?.map((o) => {
            const active = value === o;
            return (
              <button
                key={o}
                type="button"
                onClick={() => onChange(o)}
                className={`text-[11.5px] px-2.5 py-1.5 rounded-md border transition ${
                  active
                    ? "border-primary bg-primary/10 text-primary font-medium"
                    : "border-border bg-background hover:border-primary/40"
                }`}
              >
                {o}
              </button>
            );
          })}
        </div>
      );
    case "multiselect": {
      const arr = Array.isArray(value) ? (value as string[]) : [];
      const toggle = (opt: string) => {
        if (arr.includes(opt)) onChange(arr.filter((x) => x !== opt));
        else onChange([...arr, opt]);
      };
      return (
        <div className="flex flex-wrap gap-1.5">
          {field.options?.map((o) => {
            const active = arr.includes(o);
            return (
              <button
                key={o}
                type="button"
                onClick={() => toggle(o)}
                className={`text-[11px] px-2 py-1 rounded-full border transition ${
                  active
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border bg-background text-muted-foreground hover:border-primary/40"
                }`}
              >
                {o}
              </button>
            );
          })}
        </div>
      );
    }
    case "slider":
      return (
        <input
          type="range"
          className="w-full accent-[color:var(--color-primary)]"
          min={field.min ?? 0}
          max={field.max ?? 100}
          step={field.step ?? 1}
          value={Number(value ?? field.default ?? 0)}
          onChange={(e) => onChange(Number(e.target.value))}
        />
      );
    case "file": {
      const filename = typeof value === "string" ? value : "";
      return (
        <label className="flex items-center gap-2 px-3 py-3 rounded-md border border-dashed border-border bg-background hover:border-primary cursor-pointer text-[11.5px] text-muted-foreground">
          <UploadCloud size={14} />
          <div className="flex-1 truncate">
            {filename ? <span className="text-foreground">{filename}</span> : "Click to upload or drag and drop"}
          </div>
          <input
            type="file"
            className="hidden"
            onChange={(e) => onChange(e.target.files?.[0]?.name ?? "")}
          />
        </label>
      );
    }
    case "tags": {
      const arr = Array.isArray(value) ? (value as string[]) : [];
      const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
        const target = e.currentTarget;
        if (e.key === "Enter" && target.value.trim()) {
          e.preventDefault();
          onChange([...arr, target.value.trim()]);
          target.value = "";
        }
      };
      return (
        <div className="space-y-1.5">
          <div className="flex flex-wrap gap-1">
            {arr.map((t, i) => (
              <span key={`${t}-${i}`} className="inline-flex items-center gap-1 text-[11px] px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                {t}
                <button
                  type="button"
                  className="opacity-70 hover:opacity-100"
                  onClick={() => onChange(arr.filter((_, idx) => idx !== i))}
                >
                  <X size={10} />
                </button>
              </span>
            ))}
          </div>
          <div className="flex items-center gap-1">
            <input
              className={baseInput}
              placeholder="Type and press Enter"
              onKeyDown={onKey}
            />
            <Plus size={14} className="text-muted-foreground" />
          </div>
        </div>
      );
    }
    default:
      return null;
  }
}
