import type { MouseEvent, PointerEvent } from "react";
import { useStore, useStoreApi } from "@xyflow/react";
import { Maximize2, Minimize2, Minus, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useWorkflowPresentation } from "@/context/WorkflowPresentationContext";
import { workflowZoomConfig } from "@/utils/flowEdgeStyles";

function stopEvent(e: MouseEvent | PointerEvent) {
  e.preventDefault();
  e.stopPropagation();
}

/**
 * Zoom toolbar rendered **outside** the React Flow pane so clicks are never
 * swallowed by pan/zoom handlers. Uses panZoom from the store directly.
 */
export function WorkflowCanvasControls({
  onFitAll,
}: {
  onFitAll: () => void;
}) {
  const store = useStoreApi();
  const zoom = useStore((s) => s.transform[2]);
  const zoomPct = Math.round(zoom * 100);
  const presentation = useWorkflowPresentation();
  const isPresentation = presentation?.isPresentation ?? false;

  const zoomIn = () => {
    const { panZoom } = store.getState();
    if (panZoom) {
      void panZoom.scaleBy(workflowZoomConfig.zoomFactor, { duration: 150 });
    }
  };

  const zoomOut = () => {
    const { panZoom } = store.getState();
    if (panZoom) {
      void panZoom.scaleBy(1 / workflowZoomConfig.zoomFactor, { duration: 150 });
    }
  };

  const setZoomLevel = (level: number) => {
    const { panZoom } = store.getState();
    const target = Math.max(workflowZoomConfig.minZoom, level);
    if (panZoom) {
      void panZoom.scaleTo(target, { duration: 200 });
    }
  };

  return (
    <>
      <div
        className="workflow-canvas-controls workflow-canvas-controls--top"
        onPointerDown={stopEvent}
        onMouseDown={stopEvent}
      >
        {isPresentation ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-9 gap-1.5 font-semibold bg-surface shadow-md"
            onClick={() => presentation?.exitPresentation()}
          >
            <Minimize2 size={15} />
            Exit
          </Button>
        ) : null}
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-9 w-9 p-0 bg-surface shadow-md"
          title="Zoom out"
          aria-label="Zoom out"
          onClick={zoomOut}
        >
          <Minus size={16} />
        </Button>
        <span className="workflow-zoom-readout bg-surface shadow-md rounded-md px-2 py-1.5">
          {zoomPct}%
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-9 w-9 p-0 bg-surface shadow-md"
          title="Zoom in"
          aria-label="Zoom in"
          onClick={zoomIn}
        >
          <Plus size={16} />
        </Button>
        <div className="h-6 w-px bg-border mx-0.5" aria-hidden />
        {workflowZoomConfig.presetLevels.map((level) => (
          <Button
            key={level}
            type="button"
            variant={Math.abs(zoom - level) < 0.04 ? "default" : "outline"}
            size="sm"
            className="h-9 min-w-[2.75rem] px-2 text-xs font-semibold bg-surface shadow-md"
            title={`${Math.round(level * 100)}%`}
            onClick={() => setZoomLevel(level)}
          >
            {Math.round(level * 100)}%
          </Button>
        ))}
        <Button
          type="button"
          variant={isPresentation ? "secondary" : "default"}
          size="sm"
          className="h-9 gap-1.5 font-semibold shadow-md"
          title="Full screen and fit workflow"
          onClick={onFitAll}
        >
          <Maximize2 size={15} />
          Fit all
        </Button>
      </div>

      <div
        className="workflow-canvas-controls workflow-canvas-controls--bottom"
        onPointerDown={stopEvent}
        onMouseDown={stopEvent}
      >
        <button
          type="button"
          className="workflow-zoom-btn bg-surface shadow-md"
          title="Zoom out"
          aria-label="Zoom out"
          onClick={zoomOut}
        >
          <Minus size={20} strokeWidth={2.5} />
        </button>
        <span className="workflow-zoom-readout bg-surface shadow-md rounded-md px-2 py-1">
          {zoomPct}%
        </span>
        <button
          type="button"
          className="workflow-zoom-btn bg-surface shadow-md"
          title="Zoom in"
          aria-label="Zoom in"
          onClick={zoomIn}
        >
          <Plus size={20} strokeWidth={2.5} />
        </button>
      </div>
    </>
  );
}
