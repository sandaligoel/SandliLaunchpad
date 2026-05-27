import { useEffect, useRef } from "react";
import { useReactFlow } from "@xyflow/react";
import { fitWorkflowToView } from "@/utils/flowEdgeStyles";

/**
 * Fits the graph once when it first loads (not on every layout tweak).
 */
export function FitWorkflowView({ nodeCount }: { nodeCount: number }) {
  const { fitView } = useReactFlow();
  const didFit = useRef(false);

  useEffect(() => {
    if (nodeCount === 0) {
      didFit.current = false;
      return;
    }
    if (didFit.current) return;
    didFit.current = true;
    const timer = setTimeout(() => fitWorkflowToView(fitView, false), 120);
    return () => clearTimeout(timer);
  }, [nodeCount, fitView]);

  return null;
}
