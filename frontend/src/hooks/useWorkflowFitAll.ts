import { useCallback } from "react";
import { useReactFlow } from "@xyflow/react";
import { useWorkflowPresentation } from "@/context/WorkflowPresentationContext";
import { fitWorkflowToView } from "@/utils/flowEdgeStyles";

export function useWorkflowFitAll() {
  const { fitView } = useReactFlow();
  const presentation = useWorkflowPresentation();

  return useCallback(() => {
    if (presentation?.isPresentation) {
      requestAnimationFrame(() => {
        setTimeout(() => fitWorkflowToView(fitView, true), 80);
      });
      return;
    }
    presentation?.enterPresentation();
    requestAnimationFrame(() => {
      setTimeout(() => fitWorkflowToView(fitView, true), 150);
    });
  }, [fitView, presentation]);
}
