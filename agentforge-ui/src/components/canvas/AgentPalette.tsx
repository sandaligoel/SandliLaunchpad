import { AGENT_REGISTRY, TEMPLATES } from "@/mocks/data";
import type { AgentType } from "@/types/api";
import { Database, Table, ShieldCheck, Wand2, GitBranch, Wrench, Brain, Globe, UploadCloud, Sparkles, LayoutTemplate, Bookmark } from "lucide-react";

const ICONS = { Database, Table, ShieldCheck, Wand2, GitBranch, Wrench, Brain, Globe, UploadCloud, Sparkles } as const;

export function AgentPalette() {
  const onDragStart = (e: React.DragEvent, type: AgentType) => {
    e.dataTransfer.setData("application/agent-type", type);
    e.dataTransfer.effectAllowed = "move";
  };
  return (
    <aside className="w-64 shrink-0 border-r border-border bg-surface flex flex-col">
      <div className="px-4 py-3 border-b border-border">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Agents</h2>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
        {AGENT_REGISTRY.map((a) => {
          const Icon = ICONS[a.icon as keyof typeof ICONS] ?? Wrench;
          return (
            <div
              key={a.type}
              draggable
              onDragStart={(e) => onDragStart(e, a.type)}
              className="group flex items-center gap-2.5 p-2.5 rounded-lg border border-border bg-background hover:border-primary hover:shadow-sm cursor-grab active:cursor-grabbing transition"
            >
              <div
                className="w-8 h-8 rounded-md grid place-items-center text-white shrink-0"
                style={{ background: a.color }}
              >
                <Icon size={15} />
              </div>
              <div className="min-w-0">
                <div className="text-[12.5px] font-medium leading-tight">{a.name}</div>
                <div className="text-[10.5px] text-muted-foreground truncate">{a.description}</div>
              </div>
            </div>
          );
        })}

        <div className="pt-3 mt-3 border-t border-border">
          <div className="flex items-center gap-1.5 px-1 mb-2">
            <LayoutTemplate size={12} className="text-muted-foreground" />
            <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Templates</h3>
          </div>
          {TEMPLATES.slice(0, 4).map((t) => (
            <button key={t.id} className="w-full text-left px-2.5 py-2 rounded-md hover:bg-muted text-[12px]">
              <div className="font-medium">{t.name}</div>
              <div className="text-[10.5px] text-muted-foreground">{t.agents.length} agents · {t.category}</div>
            </button>
          ))}
        </div>

        <div className="pt-3 mt-3 border-t border-border">
          <div className="flex items-center gap-1.5 px-1 mb-2">
            <Bookmark size={12} className="text-muted-foreground" />
            <h3 className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Saved Blocks</h3>
          </div>
          <div className="px-2 py-3 rounded-md border border-dashed border-border text-[11px] text-muted-foreground text-center">
            No saved blocks yet
          </div>
        </div>
      </div>
    </aside>
  );
}
