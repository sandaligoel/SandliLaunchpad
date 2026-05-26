import { createFileRoute, Link, Navigate } from "@tanstack/react-router";
import { AppShell } from "@/components/layout/AppShell";
import { ReactFlowProvider } from "@xyflow/react";
import { AgentPalette } from "@/components/canvas/AgentPalette";
import { CanvasEditor } from "@/components/canvas/CanvasEditor";
import { ConfigPanel } from "@/components/canvas/ConfigPanel";
import { Console } from "@/components/canvas/Console";
import { BuilderToolbar } from "@/components/canvas/BuilderToolbar";
import { LaunchpadBuilder } from "@/components/builder/LaunchpadBuilder";
import { resolveBuilderSessionId } from "@/api/affine/builderStorage";

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
  const resolvedId = urlSessionId ?? resolveBuilderSessionId();

  if (!urlSessionId && resolvedId) {
    return (
      <Navigate to="/builder" search={{ sessionId: resolvedId }} replace />
    );
  }

  if (resolvedId) {
    return (
      <AppShell>
        <ReactFlowProvider>
          <LaunchpadBuilder sessionId={resolvedId} />
        </ReactFlowProvider>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <ReactFlowProvider>
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
      </ReactFlowProvider>
    </AppShell>
  );
}
