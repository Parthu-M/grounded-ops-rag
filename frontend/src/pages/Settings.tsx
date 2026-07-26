import {
  CheckCircle2,
  Database,
  Globe2,
  LoaderCircle,
  PlugZap,
  Save,
  ShieldCheck,
  WifiOff,
} from "lucide-react";
import { useState } from "react";
import {
  getApiBase,
  getConnectionMode,
  setApiBase,
  setConnectionMode,
  type ConnectionMode,
} from "../api";

interface SettingsProps {
  onReconnect: () => Promise<boolean>;
  onNotify: (type: "success" | "error", message: string) => void;
}

export function Settings({ onReconnect, onNotify }: SettingsProps) {
  const [mode, setMode] = useState<ConnectionMode>(getConnectionMode());
  const [base, setBase] = useState(getApiBase());
  const [checking, setChecking] = useState(false);

  const save = async () => {
    setConnectionMode(mode);
    setApiBase(base);
    setChecking(true);
    const connected = await onReconnect();
    setChecking(false);
    if (mode === "demo" || connected) {
      onNotify(
        "success",
        mode === "demo"
          ? "Demo workspace enabled."
          : "Live API connection verified.",
      );
    } else {
      onNotify(
        "error",
        "Settings saved, but the API health check did not succeed.",
      );
    }
  };

  return (
    <div className="page settings-page">
      <section className="page-heading-row">
        <div>
          <span className="section-kicker">Settings</span>
          <h1>Connection & runtime</h1>
          <p>
            Switch between the safe demo workspace and your deployed FastAPI
            service.
          </p>
        </div>
      </section>

      <section className="settings-layout">
        <article className="panel connection-panel">
          <div className="panel-heading compact">
            <div>
              <span className="section-kicker">Data source</span>
              <h2>Connection mode</h2>
            </div>
            <PlugZap size={20} />
          </div>

          <div className="mode-options">
            <button
              className={mode === "demo" ? "active" : ""}
              onClick={() => setMode("demo")}
            >
              <span className="mode-icon">
                <Database size={20} />
              </span>
              <div>
                <strong>Demo workspace</strong>
                <span>
                  Preloaded evaluation data and sample grounded queries.
                </span>
              </div>
              {mode === "demo" && <CheckCircle2 size={18} />}
            </button>
            <button
              className={mode === "live" ? "active" : ""}
              onClick={() => setMode("live")}
            >
              <span className="mode-icon">
                <Globe2 size={20} />
              </span>
              <div>
                <strong>Live FastAPI service</strong>
                <span>Use your Chroma index, logs, and runtime reports.</span>
              </div>
              {mode === "live" && <CheckCircle2 size={18} />}
            </button>
          </div>

          <label className={`api-field ${mode === "demo" ? "disabled" : ""}`}>
            <span>API base URL</span>
            <div>
              <Globe2 size={17} />
              <input
                value={base}
                onChange={(event) => setBase(event.target.value)}
                disabled={mode === "demo"}
                placeholder="https://your-rag-api.example.com"
              />
            </div>
            <small>
              Leave empty when the frontend is served by FastAPI on the same
              origin.
            </small>
          </label>

          <button
            className="button button-primary save-settings"
            onClick={save}
          >
            {checking ? (
              <LoaderCircle className="spin" size={17} />
            ) : (
              <Save size={17} />
            )}
            Save and test connection
          </button>
        </article>

        <div className="settings-side">
          <article className="panel runtime-card">
            <span className="section-kicker">Expected backend</span>
            <h2>FastAPI contract</h2>
            {[
              ["GET", "/health", "Runtime status"],
              ["POST", "/query", "Grounded answer"],
              ["POST", "/upload", "Browser file upload"],
              ["POST", "/ingest", "Server-path ingestion"],
              ["GET", "/documents", "Corpus inventory"],
              ["POST", "/documents/{id}/delete", "Remove indexed document"],
              ["GET", "/reports", "Evaluation artifacts"],
            ].map(([method, path, detail]) => (
              <div className="endpoint-row" key={path}>
                <code>{method}</code>
                <strong>{path}</strong>
                <span>{detail}</span>
              </div>
            ))}
          </article>
          <article className="panel security-card">
            <ShieldCheck size={21} />
            <span className="section-kicker">Production note</span>
            <h2>Protect mutation routes.</h2>
            <p>
              The take-home API leaves ingestion unauthenticated for easy
              demonstration. Put <code>/ingest</code> behind an admin gateway or
              private network before indexing real customer documents.
            </p>
          </article>
          <article className="offline-hint">
            <WifiOff size={17} />
            <p>
              If a live backend is unavailable, the interface stays explorable
              in Demo mode without sending data anywhere.
            </p>
          </article>
        </div>
      </section>
    </div>
  );
}
