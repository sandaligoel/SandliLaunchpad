import { useState, type KeyboardEvent } from "react";
import { Plus, X } from "lucide-react";

interface Props {
  label: string;
  items: string[];
  onChange: (items: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function EditableStringList({
  label,
  items,
  onChange,
  placeholder = "Type and press Enter",
  disabled = false,
}: Props) {
  const [draft, setDraft] = useState("");

  const addItem = (raw: string) => {
    const text = raw.trim();
    if (!text || items.some((i) => i.toLowerCase() === text.toLowerCase())) return;
    onChange([...items, text]);
    setDraft("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addItem(draft);
    }
  };

  return (
    <div className="space-y-1.5">
      <label className="text-[11px] text-muted-foreground block">{label}</label>
      {items.length > 0 ? (
        <ul className="space-y-1">
          {items.map((item, index) => (
            <li
              key={`${item}-${index}`}
              className="flex items-start gap-1.5 text-[12px] rounded-md border border-border bg-background px-2 py-1.5"
            >
              <span className="flex-1 min-w-0 break-words">{item}</span>
              <button
                type="button"
                disabled={disabled}
                className="shrink-0 h-5 w-5 grid place-items-center rounded hover:bg-muted text-muted-foreground disabled:opacity-40"
                aria-label={`Remove ${item}`}
                onClick={() => onChange(items.filter((_, i) => i !== index))}
              >
                <X size={12} />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-[11px] text-muted-foreground italic">None defined yet</p>
      )}
      <div className="flex items-center gap-1">
        <input
          type="text"
          disabled={disabled}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          className="flex-1 text-xs bg-background border border-border rounded-md px-2.5 py-1.5 outline-none focus:ring-2 ring-primary/30 disabled:opacity-50"
        />
        <button
          type="button"
          disabled={disabled || !draft.trim()}
          className="h-8 w-8 shrink-0 grid place-items-center rounded-md border border-border hover:bg-muted disabled:opacity-40"
          aria-label={`Add ${label.toLowerCase()}`}
          onClick={() => addItem(draft)}
        >
          <Plus size={14} />
        </button>
      </div>
    </div>
  );
}
