import { useCallback, useEffect, useMemo, useRef } from "react";
import { useReactFlow, type Node } from "@xyflow/react";
import type { FlowNodeData } from "@/architecture-flow/types/plan";
import type { LayoutMeta } from "@/architecture-flow/layout/calculateLayout";
import {
  computeGraphBounds,
  computeTranslateExtent,
  defaultFitViewOptions,
  nodesForFitMode,
  type FitMode,
  VIEWPORT,
} from "@/architecture-flow/layout/viewport";

export function useGraphViewport(
  nodes: Node<FlowNodeData>[],
  layoutLoading: boolean,
  layoutMeta: LayoutMeta | null
) {
  const { fitView, setCenter, getZoom } = useReactFlow();
  const initialFitDone = useRef(false);
  const lastPlanKey = useRef("");

  const bounds = useMemo(() => computeGraphBounds(nodes), [nodes]);

  const translateExtent = useMemo(
    () =>
      computeTranslateExtent(
        bounds,
        layoutMeta?.totalWidth,
        layoutMeta?.totalHeight
      ),
    [bounds, layoutMeta]
  );

  const applyFit = useCallback(
    async (mode: FitMode = "full", selectionIds?: string[]) => {
      const focusNodes = nodesForFitMode(nodes, mode, selectionIds);
      const fitOpts: any = { ...defaultFitViewOptions };
      // When focusNodes is undefined, "Fit all" should include the whole canvas.
      if (focusNodes) {
        fitOpts.nodes = focusNodes;
      }
      await fitView(fitOpts);
    },
    [fitView, nodes]
  );

  const focusNode = useCallback(
    (nodeId: string) => {
      const n = nodes.find((x) => x.id === nodeId);
      if (!n) return;
      const { w, h } = {
        w: Number(n.style?.width) || n.data.measuredWidth || 248,
        h: Number(n.style?.height) || n.data.measuredHeight || 84,
      };
      const cx = n.position.x + w / 2;
      const cy = n.position.y + h / 2;
      const zoom = Math.max(getZoom(), VIEWPORT.fitMinZoom);
      setCenter(cx, cy, { zoom: Math.min(zoom, 1.15), duration: 380 });
    },
    [nodes, setCenter, getZoom]
  );

  useEffect(() => {
    if (!nodes.length || layoutLoading) return;

    const planKey = `${nodes.length}_${bounds.width}_${bounds.height}`;
    if (planKey === lastPlanKey.current && initialFitDone.current) return;
    lastPlanKey.current = planKey;

    const run = () => {
      const isWide = bounds.width > 2200;
      void applyFit(isWide ? "orchestrator" : "full").then(() => {
        initialFitDone.current = true;
        if (import.meta.env.DEV) {
          console.info("[viewport] initial fit", {
            bounds,
            mode: isWide ? "orchestrator" : "full",
            zoom: getZoom(),
          });
        }
      });
    };

    requestAnimationFrame(() => requestAnimationFrame(run));
  }, [nodes.length, layoutLoading, bounds.width, bounds.height, applyFit, getZoom]);

  useEffect(() => {
    let t: ReturnType<typeof setTimeout> | undefined;
    const onResize = () => {
      if (!initialFitDone.current || layoutLoading) return;
      clearTimeout(t);
      t = setTimeout(() => void applyFit("full"), 280);
    };
    window.addEventListener("resize", onResize);
    return () => {
      clearTimeout(t);
      window.removeEventListener("resize", onResize);
    };
  }, [applyFit, layoutLoading]);

  return {
    bounds,
    translateExtent,
    applyFit,
    focusNode,
    viewportConfig: VIEWPORT,
    defaultFitViewOptions,
  };
}
