import { useCallback, useEffect, useState } from "react";
import { getConnectionMode, getDocuments, getHealth, getReports } from "./api";
import { Shell } from "./components/Shell";
import { Toast, type ToastState } from "./components/Toast";
import { demoDocuments, demoHealth, demoReports } from "./data";
import { Cost } from "./pages/Cost";
import { Evaluations } from "./pages/Evaluations";
import { Knowledge } from "./pages/Knowledge";
import { Overview } from "./pages/Overview";
import { Playground } from "./pages/Playground";
import { Settings } from "./pages/Settings";
import type { DocumentSummary, Health, Page, Reports } from "./types";

const validPages: Page[] = [
  "overview",
  "playground",
  "knowledge",
  "evaluations",
  "cost",
  "settings",
];

const initialPage = (): Page => {
  if (typeof window === "undefined") return "overview";
  const hash = window.location.hash.replace("#/", "") as Page;
  return validPages.includes(hash) ? hash : "overview";
};

export default function App() {
  const [page, setPage] = useState<Page>("overview");
  const [health, setHealth] = useState<Health>(demoHealth);
  const [reports, setReports] = useState<Reports>(demoReports);
  const [documents, setDocuments] = useState<DocumentSummary[]>(demoDocuments);
  const [connection, setConnection] = useState<"online" | "demo" | "offline">(
    "demo",
  );
  const [toast, setToast] = useState<ToastState | null>(null);

  const notify = useCallback((type: "success" | "error", message: string) => {
    setToast({ type, message });
    window.setTimeout(() => setToast(null), 4200);
  }, []);

  const refresh = useCallback(async (): Promise<boolean> => {
    const mode = getConnectionMode();
    try {
      const [nextHealth, nextReports, nextDocuments] = await Promise.all([
        getHealth(),
        getReports(),
        getDocuments(),
      ]);
      setHealth(nextHealth);
      setReports(nextReports);
      setDocuments(nextDocuments);
      setConnection(mode === "demo" ? "demo" : "online");
      return true;
    } catch {
      setConnection("offline");
      return false;
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const onHash = () => setPage(initialPage());
    onHash();
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const navigate = (next: Page) => {
    window.location.hash = `/${next}`;
    setPage(next);
  };

  return (
    <>
      <Shell page={page} onNavigate={navigate} connection={connection}>
        {page === "overview" && (
          <Overview health={health} reports={reports} onNavigate={navigate} />
        )}
        {page === "playground" && <Playground onNotify={notify} />}
        {page === "knowledge" && (
          <Knowledge
            documents={documents}
            health={health}
            connection={connection}
            onRefresh={async () => {
              await refresh();
            }}
            onOpenSettings={() => navigate("settings")}
            onNotify={notify}
          />
        )}
        {page === "evaluations" && <Evaluations reports={reports} />}
        {page === "cost" && <Cost reports={reports} />}
        {page === "settings" && (
          <Settings onReconnect={refresh} onNotify={notify} />
        )}
      </Shell>
      <Toast toast={toast} onClose={() => setToast(null)} />
    </>
  );
}
