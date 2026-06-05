import { createFileRoute, Link, Navigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { MessageSquare, Plus, Workflow } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { Topbar } from "@/components/layout/Topbar";
import { ReactFlowProvider } from "@xyflow/react";
import { WorkflowPresentationProvider } from "@/context/WorkflowPresentationContext";
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

function BuilderEmptyState() {
  return (
    <AppShell>
      <Topbar
        title="Workflow Builder"
        subtitle="Architecture canvas from Agent Launchpad"
      />
      <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8 text-center">
        <div className="max-w-md space-y-2">
          <h2 className="text-lg font-semibold">No workflow open yet</h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Complete an Agent Launchpad chat and generate an architecture plan, or
            open a saved workflow from your workspace.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/interview"
            search={{ fresh: "1" }}
            className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:opacity-90"
          >
            <Plus size={16} aria-hidden />
            Start new chat
          </Link>
          <Link
            to="/workflows"
            className="inline-flex h-10 items-center gap-2 rounded-md border border-border bg-background px-4 text-sm font-medium hover:bg-muted"
          >
            <Workflow size={16} aria-hidden />
            Open saved workflow
          </Link>
          <Link
            to="/interview"
            className="inline-flex h-10 items-center gap-2 rounded-md border border-border bg-background px-4 text-sm font-medium hover:bg-muted"
          >
            <MessageSquare size={16} aria-hidden />
            Continue interview
          </Link>
        </div>
      </main>
    </AppShell>
  );
}

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

  return <BuilderEmptyState />;
}
