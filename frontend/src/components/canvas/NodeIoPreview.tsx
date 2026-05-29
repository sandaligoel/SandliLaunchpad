/** Compact inputs/outputs preview on workflow canvas nodes. */
export function NodeIoPreview({
  inputs = [],
  outputs = [],
  maxEach = 2,
}: {
  inputs?: string[];
  outputs?: string[];
  maxEach?: number;
}) {
  const inList = inputs.filter((s) => s.trim());
  const outList = outputs.filter((s) => s.trim());
  if (!inList.length && !outList.length) return null;

  const renderList = (label: string, items: string[], tone: string) => {
    if (!items.length) {
      return (
        <div className={tone}>
          <span className="font-semibold uppercase tracking-wide text-[9px] opacity-80">
            {label}
          </span>
          <span className="block mt-0.5 italic opacity-70">—</span>
        </div>
      );
    }
    const shown = items.slice(0, maxEach);
    const rest = items.length - shown.length;
    return (
      <div className={tone}>
        <span className="font-semibold uppercase tracking-wide text-[9px] opacity-80">
          {label}
        </span>
        <ul className="mt-0.5 space-y-0.5 list-none">
          {shown.map((item, i) => (
            <li key={`${label}-${i}`} className="line-clamp-2 break-words">
              {item}
            </li>
          ))}
          {rest > 0 ? (
            <li className="opacity-70">+{rest} more</li>
          ) : null}
        </ul>
      </div>
    );
  };

  return (
    <div className="mt-2.5 pt-2 border-t border-slate-100/90 grid grid-cols-2 gap-2 text-[10px] leading-snug text-slate-600">
      {renderList("In", inList, "min-w-0")}
      {renderList("Out", outList, "min-w-0 border-l border-slate-100 pl-2")}
    </div>
  );
}
