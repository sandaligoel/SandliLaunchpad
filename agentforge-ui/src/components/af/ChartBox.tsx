import { useEffect, useState, type ReactElement } from "react";
import { ResponsiveContainer } from "recharts";

/**
 * Recharts needs a sized parent. SSR and first paint often have 0×0 layout,
 * which spams "width(-1) and height(-1)" in the terminal.
 */
export function ChartBox({
  children,
  className = "h-64 px-4 pb-4",
}: {
  children: ReactElement;
  className?: string;
}) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(true);
  }, []);

  return (
    <div className={`min-w-0 w-full ${className}`}>
      {ready ? (
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={200}>
          {children}
        </ResponsiveContainer>
      ) : (
        <div className="h-full min-h-[200px] w-full rounded-md bg-muted/30" />
      )}
    </div>
  );
}
