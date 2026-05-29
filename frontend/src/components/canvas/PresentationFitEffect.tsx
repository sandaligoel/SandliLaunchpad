import { useEffect } from "react";
import { useReactFlow } from "@xyflow/react";
import { useWorkflowPresentation } from "@/context/WorkflowPresentationContext";
import { fitWorkflowToView } from "@/utils/flowEdgeStyles";

/** Re-fits the graph when entering full-screen presentation. */
export function PresentationFitEffect() {
  const presentation = useWorkflowPresentation();
  const { fitView } = useReactFlow();

  useEffect(() => {
    if (!presentation?.isPresentation) return;
    const timer = setTimeout(() => fitWorkflowToView(fitView, true), 180);
    return () => clearTimeout(timer);
  }, [presentation?.isPresentation, fitView]);

  return null;
}
