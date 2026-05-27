import { useReactFlow } from "@xyflow/react";
import { useEffect } from "react";

/** Re-measure custom nodes when content grows so text is not clipped. */
export function WorkflowNodeMeasureEffect({
  nodeIds,
}: {
  nodeIds: string[];
}) {
  const { updateNodeInternals } = useReactFlow();

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      for (const nodeId of nodeIds) {
        updateNodeInternals(nodeId);
      }
    });
    return () => cancelAnimationFrame(id);
  }, [nodeIds, updateNodeInternals]);

  return null;
}
