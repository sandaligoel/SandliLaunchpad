import { AffineHealthProvider } from "@/context/AffineHealthContext";
import { Sidebar } from "./Sidebar";
import { StorageStatusBanner } from "./StorageStatusBanner";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <AffineHealthProvider>
      <div className="flex min-h-screen w-full bg-background text-foreground">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <StorageStatusBanner />
          {children}
        </div>
      </div>
    </AffineHealthProvider>
  );
}
