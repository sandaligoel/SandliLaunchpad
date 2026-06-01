import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  generateArchitecture,
  getSession,
} from "@/api/affine/client";
import {
  loadBuilderWorkflowAsync,
  saveBuilderWorkflowAsync,
  type SavedBuilderWorkflow,
} from "@/api/affine/builderStorage";
import type { ArchitecturePlan } from "@/api/affine/types";
import { ArchitectureCanvas } from "@/components/builder/ArchitectureCanvas";
import { BuilderArchitectureRail } from "@/components/builder/BuilderArchitectureRail";
import { LaunchpadAgentPalette } from "@/components/canvas/LaunchpadAgentPalette";
import { Button } from "@/components/ui/button";
import { sanitizeArchitecturePlan } from "@/utils/sanitizePlan";
import { useWorkflowPresentation } from "@/context/WorkflowPresentationContext";
import { Loader2, Pencil } from "lucide-react";
import { useAgents } from "@/api/hooks";
import { hydratePlanStepMetadata } from "@/utils/stepIo";
import { updatePlanStep } from "@/utils/planFlowSync";

const SAVE_DEBOUNCE_MS = 400;

export function LaunchpadBuilder({ sessionId }: { sessionId: string }) {
  const [plan, setPlan] = useState<ArchitecturePlan | null>(null);
  const [problemStatement, setProblemStatement] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [positionOverrides, setPositionOverrides] = useState<
    Record<string, { x: number; y: number }>
  >({});
  const [savedHint, setSavedHint] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const presentation = useWorkflowPresentation();
  const isPresentation = presentation?.isPresentation ?? false;
  const { data: catalogAgents = [] } = useAgents();

  useEffect(() => {
    if (!plan || catalogAgents.length === 0) return;
    setPlan((prev) => {
      if (!prev) return prev;
      const hydrated = hydratePlanStepMetadata(prev, catalogAgents);
      return hydrated;
    });
  }, [catalogAgents.length, sessionId, plan?.graph.edges.length, plan?.graph.nodes.length]);

  useEffect(() => {
    if (!isPresentation) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [isPresentation]);

  const persistLocal = useCallback(
    (nextPlan: ArchitecturePlan, selected: string | null) => {
      const payload: SavedBuilderWorkflow = {
        sessionId,
        plan: nextPlan,
        nodePositions: positionOverrides,
        selectedNodeId: selected,
        title: problemStatement.slice(0, 72) + (problemStatement.length > 72 ? "…" : ""),
        problemStatement,
        savedAt: new Date().toISOString(),
      };
      void saveBuilderWorkflowAsync(payload)
        .then(() => setSavedHint(true))
        .catch((e) => {
          setError(
            e instanceof Error ? e.message : "Failed to save workflow to server",
          );
        });
    },
    [sessionId, problemStatement, positionOverrides],
  );

  const schedulePersist = useCallback(
    (nextPlan: ArchitecturePlan, selected: string | null) => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => {
        void persistLocal(nextPlan, selected);
      }, SAVE_DEBOUNCE_MS);
    },
    [persistLocal],
  );

  useEffect(() => {
    let cancelled = false;
    const applySaved = (saved: SavedBuilderWorkflow) => {
      const cleaned = sanitizeArchitecturePlan(saved.plan);
      setPlan(cleaned);
      setPositionOverrides(saved.nodePositions ?? {});
      setSelectedNodeId(saved.selectedNodeId ?? null);
      if (saved.problemStatement) setProblemStatement(saved.problemStatement);
      setSavedHint(true);
    };

    const snapshotPlan = (
      nextPlan: ArchitecturePlan,
      ps: string,
      overrides: Record<string, { x: number; y: number }> = {},
      selected: string | null = null,
    ) => {
      void saveBuilderWorkflowAsync({
        sessionId,
        plan: nextPlan,
        nodePositions: overrides,
        selectedNodeId: selected,
        problemStatement: ps,
        title: ps.slice(0, 72) + (ps.length > 72 ? "…" : ""),
        savedAt: new Date().toISOString(),
      });
    };

    (async () => {
      setLoading(true);
      setError(null);
      try {
        const { session } = await getSession(sessionId);
        if (cancelled) return;
        const ps = session.spec.problem_statement;
        setProblemStatement(ps);

        const saved = await loadBuilderWorkflowAsync(sessionId);
        if (saved?.plan?.graph?.nodes?.length) {
          applySaved(saved);
          return;
        }

        if (session.architecture_plan?.graph?.nodes?.length) {
          const cleaned = sanitizeArchitecturePlan(session.architecture_plan);
          setPlan(cleaned);
          setPositionOverrides({});
          snapshotPlan(cleaned, ps);
          return;
        }

        const canPlan = session.spec.status === "ready";
        if (!canPlan) {
          setError(
            "Finish the Agent Launchpad chat first, then return here to edit your workflow.",
          );
          return;
        }
        const { plan: p } = await generateArchitecture(sessionId, false);
        if (!cancelled) {
          const cleaned = sanitizeArchitecturePlan(p);
          setPlan(cleaned);
          setPositionOverrides({});
          snapshotPlan(cleaned, ps);
        }
      } catch (e) {
        if (cancelled) return;
        const fallback = await loadBuilderWorkflowAsync(sessionId);
        if (fallback?.plan?.graph?.nodes?.length) {
          applySaved(fallback);
          return;
        }
        setError(
          e instanceof Error ? e.message : "Failed to load architecture",
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const focusNode = useCallback(
    (nodeId: string) => {
      setSelectedNodeId(nodeId);
      window.dispatchEvent(
        new CustomEvent("launchpad:select-node", { detail: { nodeId } }),
      );
      if (plan) schedulePersist(plan, nodeId);
    },
    [plan, schedulePersist],
  );

  const patchPlan = useCallback(
    (nextPlan: ArchitecturePlan) => {
      setPlan(nextPlan);
      schedulePersist(nextPlan, selectedNodeId);
    },
    [selectedNodeId, schedulePersist],
  );

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3 p-8">
        <Loader2 className="animate-spin text-primary" size={28} />
        <p className="text-sm text-muted-foreground">
          Building your architecture from the chat… (30–60s)
        </p>
      </div>
    );
  }

  if (error || !plan) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 p-8 max-w-md text-center">
        <p className="text-sm text-destructive">
          {error ?? "No architecture plan"}
        </p>
        <Link to="/interview" className="text-sm text-primary underline">
          Back to Agent Launchpad
        </Link>
      </div>
    );
  }

  const title =
    problemStatement.slice(0, 48) +
    (problemStatement.length > 48 ? "…" : "");

  return (
    <>
      {!isPresentation ? (
      <div className="h-14 border-b border-border bg-surface px-4 flex items-center gap-3 shrink-0">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold truncate">
            {title || "Launchpad workflow"}
          </div>
          <div className="text-[11px] text-muted-foreground flex items-center gap-2">
            <span>
              {plan.graph.nodes.length} steps ·{" "}
              {
                plan.reuse_decisions.filter(
                  (d) => d.decision === "reuse" || d.decision === "adapt",
                ).length
              }{" "}
              reuse ·{" "}
              {plan.reuse_decisions.filter((d) => d.decision === "build").length}{" "}
              build
            </span>
            <span className="inline-flex items-center gap-1 text-primary">
              <Pencil size={11} />
              Edit flow
            </span>
            {savedHint ? (
              <span className="text-muted-foreground">· Saved to server</span>
            ) : null}
          </div>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link to="/interview" search={{ sessionId, view: "chat" }}>
            Chat history
          </Link>
        </Button>
      </div>
      ) : null}
      <div
        className={
          isPresentation
            ? "fixed inset-0 z-[300] architecture-flow-scope"
            : "flex-1 flex min-h-0"
        }
      >
        {!isPresentation ? (
          <LaunchpadAgentPalette plan={plan} onFocusNode={focusNode} />
        ) : null}
        <ArchitectureCanvas plan={plan} catalogAgents={catalogAgents} />
        {!isPresentation ? (
          <BuilderArchitectureRail
            plan={plan}
            catalogAgents={catalogAgents}
            onIoJsonChange={(nodeId, patch) => {
              setPlan((prev) => {
                if (!prev) return prev;
                const next = updatePlanStep(prev, nodeId, patch);
                schedulePersist(next, selectedNodeId);
                return next;
              });
            }}
          />
        ) : null}
      </div>
    </>
  );
}
