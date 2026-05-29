import type { FlowNodeData } from "@/architecture-flow/types/plan";
import { ReuseBadge } from "@/architecture-flow/components/nodes/shared";

function JsonBlock({ title, data }: { title: string; data?: Record<string, unknown> }) {
  if (!data || !Object.keys(data).length) {
    return (
      <div>
        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500 mb-1">{title}</p>
        <p className="text-xs text-slate-500">—</p>
      </div>
    );
  }
  return (
    <div>
      <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500 mb-1">{title}</p>
      <pre className="max-h-40 overflow-auto rounded-md border border-white/10 bg-black/30 p-2 text-[10px] leading-relaxed text-slate-300 font-mono">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

export function NodeDetailPanel({ node }: { node: FlowNodeData | null }) {
  if (!node) {
    return (
      <p className="text-sm text-slate-500">Select a node to inspect inputs, outputs, and metadata.</p>
    );
  }

  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <h4 className="font-semibold text-white leading-snug">{node.label}</h4>
        {node.reuse && <ReuseBadge reuse={node.reuse} />}
      </div>
      {node.description && (
        <p className="text-xs text-slate-400 leading-relaxed">{node.description}</p>
      )}
      <dl className="grid grid-cols-2 gap-2 text-xs">
        <dt className="text-slate-500">Lane</dt>
        <dd className="text-slate-300 capitalize">{node.lane}</dd>
        <dt className="text-slate-500">Status</dt>
        <dd className="text-slate-300 capitalize">{node.runtime.status}</dd>
        {node.runtime.retries > 0 && (
          <>
            <dt className="text-slate-500">Retries</dt>
            <dd className="text-slate-300">{node.runtime.retries}</dd>
          </>
        )}
      </dl>
      <JsonBlock title="Input (JSON)" data={node.runtime.inputJson} />
      <JsonBlock title="Output (JSON)" data={node.runtime.outputJson} />
      <div>
        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500 mb-1">Tools</p>
        <ul className="flex flex-wrap gap-1">
          {node.runtime.tools.map((t) => (
            <li
              key={t}
              className="rounded bg-white/5 px-2 py-0.5 text-[10px] text-slate-300"
            >
              {t}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
