import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  checkAffineHealth,
  type AffineHealthResponse,
} from "@/api/affine/client";

export type AffineHealthState = {
  loading: boolean;
  apiOk: boolean | null;
  health: AffineHealthResponse | null;
  message: string | null;
  blobUnreachable: boolean;
  localStorageOnly: boolean;
  refresh: () => void;
};

const AffineHealthContext = createContext<AffineHealthState | null>(null);

function describeStorage(health: AffineHealthResponse): string {
  const st = health.storage;
  if (!st) return "Storage status unknown.";
  if (st.backend === "azure_blob" && st.reachable) {
    const n = st.session_blob_count ?? 0;
    return `Azure Blob connected (${st.account}/${st.container}) — ${n} saved chat(s).`;
  }
  if (st.backend === "azure_blob") {
    return "Azure Blob is configured but not reachable — check backend/.env credentials.";
  }
  return "Using local disk only (backend/data/blob_mirror). Add AZURE_STORAGE_* for shared Azure persistence.";
}

export function AffineHealthProvider({
  children,
  pollMs = 20_000,
}: {
  children: ReactNode;
  pollMs?: number;
}) {
  const [loading, setLoading] = useState(true);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [health, setHealth] = useState<AffineHealthResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const probe = useCallback(async () => {
    try {
      const h = await checkAffineHealth();
      setApiOk(true);
      setHealth(h);
      setMessage(describeStorage(h));
    } catch {
      setApiOk(false);
      setHealth(null);
      setMessage(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const run = () => {
      if (!cancelled) void probe();
    };
    run();
    const id = window.setInterval(run, pollMs);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [probe, pollMs]);

  const st = health?.storage;
  const value = useMemo(
    (): AffineHealthState => ({
      loading,
      apiOk,
      health,
      message,
      blobUnreachable:
        apiOk === true && st?.backend === "azure_blob" && st.reachable !== true,
      localStorageOnly: apiOk === true && st?.backend === "local",
      refresh: probe,
    }),
    [loading, apiOk, health, message, st, probe],
  );

  return (
    <AffineHealthContext.Provider value={value}>
      {children}
    </AffineHealthContext.Provider>
  );
}

export function useAffineHealth(): AffineHealthState {
  const ctx = useContext(AffineHealthContext);
  if (!ctx) {
    throw new Error("useAffineHealth must be used within AffineHealthProvider");
  }
  return ctx;
}
