import { RefreshCw } from "lucide-react";
import { useAffineHealth } from "@/hooks/useAffineHealth";

const APP_BUILD =
  typeof import.meta.env.VITE_APP_BUILD === "string"
    ? import.meta.env.VITE_APP_BUILD
    : "dev";

export function StorageStatusBanner() {
  const { loading, apiOk, message, blobUnreachable, localStorageOnly } =
    useAffineHealth();

  if (loading) return null;

  if (apiOk === false) {
    return (
      <div
        role="alert"
        className="shrink-0 border-b border-destructive/40 bg-destructive/10 px-4 py-2 text-xs text-destructive"
      >
        <strong>API offline.</strong> Start the backend with{" "}
        <code className="rounded bg-destructive/10 px-1">./scripts/start-backend.sh</code>
        . If the UI looks outdated (old menu items), hard-refresh after the API is up:{" "}
        <kbd className="rounded border border-destructive/30 px-1">Cmd+Shift+R</kbd>.
        <span className="ml-2 text-destructive/70">UI build {APP_BUILD}</span>
      </div>
    );
  }

  if (blobUnreachable) {
    return (
      <div
        role="alert"
        className="shrink-0 border-b border-amber-500/40 bg-amber-500/10 px-4 py-2 text-xs text-amber-950 dark:text-amber-100"
      >
        <strong>Azure Blob unreachable.</strong> {message} Saved workflows and chats may not
        load until storage is fixed. Hard-refresh if the page still looks wrong:{" "}
        <kbd className="rounded border border-amber-500/40 px-1">Cmd+Shift+R</kbd>.
        <span className="ml-2 opacity-70">UI build {APP_BUILD}</span>
      </div>
    );
  }

  if (localStorageOnly) {
    return (
      <div
        role="status"
        className="shrink-0 border-b border-sky-500/30 bg-sky-500/10 px-4 py-2 text-xs text-sky-950 dark:text-sky-100"
      >
        <strong>Local storage mode.</strong> {message} Team data on Azure will not appear here.
        <span className="ml-2 opacity-70">UI build {APP_BUILD}</span>
      </div>
    );
  }

  return null;
}

export function StorageStatusRefreshHint() {
  const { apiOk } = useAffineHealth();
  if (apiOk !== true) return null;
  return (
    <button
      type="button"
      className="inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground"
      title="Reload latest UI from dev server"
      onClick={() => window.location.reload()}
    >
      <RefreshCw size={10} aria-hidden />
      Refresh UI
    </button>
  );
}
