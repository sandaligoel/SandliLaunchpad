import { useCallback, useState } from "react";
import { startSession, submitTurn } from "./api";
import { ChatPanel } from "./components/ChatPanel";
import { SpecificationPanel } from "./components/SpecificationPanel";
import type { InterviewSession } from "./types";
import "./App.css";

export default function App() {
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = useCallback(async (problemStatement: string) => {
    setLoading(true);
    setError(null);
    try {
      const { session: s } = await startSession(problemStatement);
      setSession(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start session");
    } finally {
      setLoading(false);
    }
  }, []);

  const handleAnswer = useCallback(
    async (answer: string) => {
      if (!session) return;
      setLoading(true);
      setError(null);
      try {
        const { session: s } = await submitTurn(session.id, answer);
        setSession(s);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to submit answer");
      } finally {
        setLoading(false);
      }
    },
    [session],
  );

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__brand">
          <span className="app-header__logo" aria-hidden>
            ◆
          </span>
          <div>
            <h1>Affine Agent Launchpad</h1>
            <p>Phase 2 — Smart requirements interview</p>
          </div>
        </div>
      </header>

      <main className="app-main">
        <ChatPanel
          session={session}
          loading={loading}
          error={error}
          onStart={handleStart}
          onAnswer={handleAnswer}
        />
        {session ? (
          <SpecificationPanel spec={session.spec} />
        ) : (
          <aside className="spec-panel spec-panel--placeholder">
            <h2>Specification</h2>
            <p>
              Start the interview to see fields move from <em>Pending…</em> to
              confirmed values. The panel reads the same spec object the chatbot
              updates each turn.
            </p>
          </aside>
        )}
      </main>
    </div>
  );
}
