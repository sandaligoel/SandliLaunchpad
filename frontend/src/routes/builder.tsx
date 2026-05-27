import { createFileRoute, Link, Navigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { ReactFlowProvider } from "@xyflow/react";
import { WorkflowPresentationProvider } from "@/context/WorkflowPresentationContext";
import { AgentPalette } from "@/components/canvas/AgentPalette";
import { CanvasEditor } from "@/components/canvas/CanvasEditor";
import { ConfigPanel } from "@/components/canvas/ConfigPanel";
import { Console } from "@/components/canvas/Console";
import { BuilderToolbar } from "@/components/canvas/BuilderToolbar";
import { LaunchpadBuilder } from "@/components/builder/LaunchpadBuilder";
import { resolveBuilderSessionIdAsync } from "@/api/affine/builderStorage";

type BuilderSearch = {
  sessionId?: string;
};

export const Route = createFileRoute("/builder")({
  validateSearch: (search: Record<string, unknown>): BuilderSearch => ({
    sessionId:
      typeof search.sessionId === "string" ? search.sessionId : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Workflow Builder — AgentForge" },
      {
        name: "description",
        content: "Visual graph editor for AI agent workflows.",
      },
    ],
  }),
  component: Builder,
});

function Builder() {
  const { sessionId: urlSessionId } = Route.useSearch();
  const [resolvedId, setResolvedId] = useState<string | undefined>(
    urlSessionId,
  );
  const [resolving, setResolving] = useState(!urlSessionId);

  useEffect(() => {
    if (urlSessionId) {
      setResolvedId(urlSessionId);
      setResolving(false);
      return;
    }
    let cancelled = false;
    setResolving(true);
    void resolveBuilderSessionIdAsync().then((id) => {
      if (!cancelled) {
        setResolvedId(id);
        setResolving(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [urlSessionId]);

  if (resolving) {
    return (
      <AppShell>
        <p className="p-6 text-sm text-muted-foreground">Loading workflow…</p>
      </AppShell>
    );
  }

  if (!urlSessionId && resolvedId && resolvedId !== urlSessionId) {
    return (
      <Navigate to="/builder" search={{ sessionId: resolvedId }} replace />
    );
  }

  if (resolvedId) {
    return (
      <AppShell>
        <ReactFlowProvider>
          <WorkflowPresentationProvider>
            <LaunchpadBuilder sessionId={resolvedId} />
          </WorkflowPresentationProvider>
        </ReactFlowProvider>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <ReactFlowProvider>
        <WorkflowPresentationProvider>
        <BuilderToolbar />
        <div className="flex-1 flex min-h-0">
          <AgentPalette />
          <div className="flex-1 flex flex-col min-w-0">
            <CanvasEditor />
            <Console />
          </div>
          <ConfigPanel />
        </div>
        <p className="text-center text-sm text-muted-foreground py-4">
          Complete an{" "}
          <Link to="/interview" className="text-primary underline">
            Agent Launchpad
          </Link>{" "}
          interview first, or open a saved workflow from{" "}
          <Link to="/workflows" className="text-primary underline">
            Workflows
          </Link>
          .
        </p>
        </WorkflowPresentationProvider>
      </ReactFlowProvider>
    </AppShell>
  );
}
