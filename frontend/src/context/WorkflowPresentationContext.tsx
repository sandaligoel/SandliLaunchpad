import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

type WorkflowPresentationContextValue = {
  isPresentation: boolean;
  enterPresentation: () => void;
  exitPresentation: () => void;
};

const WorkflowPresentationContext =
  createContext<WorkflowPresentationContextValue | null>(null);

export function WorkflowPresentationProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [isPresentation, setIsPresentation] = useState(false);

  const enterPresentation = useCallback(() => {
    setIsPresentation(true);
    void document.documentElement.requestFullscreen?.().catch(() => {
      /* fixed overlay still works without browser fullscreen */
    });
  }, []);

  const exitPresentation = useCallback(() => {
    setIsPresentation(false);
    if (document.fullscreenElement) {
      void document.exitFullscreen?.().catch(() => undefined);
    }
  }, []);

  useEffect(() => {
    const onFullscreenChange = () => {
      if (!document.fullscreenElement) {
        setIsPresentation(false);
      }
    };
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () =>
      document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, []);

  useEffect(() => {
    if (!isPresentation) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        exitPresentation();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isPresentation, exitPresentation]);

  const value = useMemo(
    () => ({ isPresentation, enterPresentation, exitPresentation }),
    [isPresentation, enterPresentation, exitPresentation],
  );

  return (
    <WorkflowPresentationContext.Provider value={value}>
      {children}
    </WorkflowPresentationContext.Provider>
  );
}

export function useWorkflowPresentation() {
  return useContext(WorkflowPresentationContext);
}
