import {
  ArrowUp,
  Check,
  ChevronRight,
  Clipboard,
  Clock3,
  FileText,
  Filter,
  Hash,
  Layers3,
  LoaderCircle,
  MessageSquareText,
  RotateCcw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import { queryRag } from "../api";
import { questions } from "../data";
import type { QueryResponse } from "../types";

interface PlaygroundProps {
  onNotify: (type: "success" | "error", message: string) => void;
}

export function Playground({ onNotify }: PlaygroundProps) {
  const [question, setQuestion] = useState(questions[0]);
  const [k, setK] = useState(3);
  const [docType, setDocType] = useState("all");
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedChunk, setSelectedChunk] = useState<string | null>(null);

  const cleanAnswer = useMemo(
    () => response?.answer.replace(/\s*\[c_[a-f0-9]{16}\]/g, "") ?? "",
    [response],
  );

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length < 2) return;
    setLoading(true);
    setResponse(null);
    setSelectedChunk(null);
    try {
      const result = await queryRag(trimmed, k, docType);
      setResponse(result);
      setSelectedChunk(result.contexts[0]?.chunk_id ?? null);
    } catch (error) {
      onNotify(
        "error",
        error instanceof Error ? error.message : "Unable to query the backend.",
      );
    } finally {
      setLoading(false);
    }
  };

  const copyAnswer = async () => {
    await navigator.clipboard.writeText(cleanAnswer);
    onNotify("success", "Answer copied to clipboard.");
  };

  return (
    <div className="page">
      <section className="page-heading-row">
        <div>
          <span className="section-kicker">RAG playground</span>
          <h1>Ask. Inspect. Trust.</h1>
          <p>
            Query the corpus and review every chunk that contributed to the
            answer.
          </p>
        </div>
        <button
          className="button button-secondary"
          onClick={() => {
            setQuestion("");
            setResponse(null);
          }}
        >
          <RotateCcw size={16} />
          Clear session
        </button>
      </section>

      <section className="playground-layout">
        <div className="playground-main">
          <article className="composer-panel">
            <form onSubmit={submit}>
              <div className="composer-label">
                <MessageSquareText size={16} />
                Your question
              </div>
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (
                    event.key === "Enter" &&
                    (event.metaKey || event.ctrlKey)
                  ) {
                    submit();
                  }
                }}
                placeholder="Ask a precise question about the indexed corpus…"
                rows={4}
              />
              <div className="composer-foot">
                <span>⌘ / Ctrl + Enter to run</span>
                <button
                  className="send-button"
                  type="submit"
                  disabled={loading || question.trim().length < 2}
                  aria-label="Run query"
                >
                  {loading ? (
                    <LoaderCircle className="spin" size={18} />
                  ) : (
                    <ArrowUp size={18} />
                  )}
                </button>
              </div>
            </form>
          </article>

          <div className="suggestion-row">
            {questions.slice(1).map((item) => (
              <button
                key={item}
                onClick={() => {
                  setQuestion(item);
                  setResponse(null);
                }}
              >
                {item}
              </button>
            ))}
          </div>

          {loading && (
            <article className="answer-panel answer-loading">
              <div className="answer-head">
                <span className="answer-avatar">
                  <Sparkles size={18} />
                </span>
                <div>
                  <strong>Grounding answer</strong>
                  <span>Retrieving the most relevant evidence…</span>
                </div>
              </div>
              <div className="skeleton skeleton-wide" />
              <div className="skeleton skeleton-medium" />
              <div className="skeleton skeleton-short" />
            </article>
          )}

          {!loading && !response && (
            <article className="answer-empty">
              <div className="empty-illustration">
                <Layers3 size={25} />
                <span />
                <span />
              </div>
              <h2>Your grounded answer will appear here</h2>
              <p>
                Run a question to see the answer, exact citations, evidence
                ranking, latency, and estimated token usage.
              </p>
            </article>
          )}

          {response && (
            <article className="answer-panel">
              <div className="answer-head">
                <span className="answer-avatar">
                  <Sparkles size={18} />
                </span>
                <div>
                  <strong>Grounded answer</strong>
                  <span>
                    {response.citations.length
                      ? `${response.citations.length} cited chunk${response.citations.length === 1 ? "" : "s"}`
                      : "System abstained"}
                  </span>
                </div>
                <button
                  className="icon-button answer-copy"
                  onClick={copyAnswer}
                  aria-label="Copy answer"
                >
                  <Clipboard size={17} />
                </button>
              </div>
              <div className="answer-copy-text">
                <p>{cleanAnswer}</p>
                {response.citations.length > 0 && (
                  <div className="inline-citations">
                    {response.citations.map((citation, index) => (
                      <button
                        key={citation}
                        onClick={() => setSelectedChunk(citation)}
                      >
                        <span>{index + 1}</span>
                        {citation.slice(0, 10)}…
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div className="answer-stats">
                <span>
                  <Clock3 size={14} />
                  {response.latency_ms.total.toFixed(2)} ms total
                </span>
                <span>
                  <Hash size={14} />
                  {response.usage.total_tokens} tokens
                  {response.usage.estimated ? " est." : ""}
                </span>
                <span>
                  <ShieldCheck size={14} />
                  {response.contexts.length
                    ? "Evidence verified"
                    : "No relevant context"}
                </span>
              </div>
            </article>
          )}
        </div>

        <aside className="playground-aside">
          <article className="panel settings-card">
            <div className="aside-title">
              <Filter size={16} />
              Retrieval settings
            </div>
            <label>
              <span>
                Top-k chunks
                <strong>{k}</strong>
              </span>
              <input
                type="range"
                min="1"
                max="8"
                value={k}
                onChange={(event) => setK(Number(event.target.value))}
              />
              <div className="range-labels">
                <span>Precise</span>
                <span>Broad</span>
              </div>
            </label>
            <label>
              <span>Document type</span>
              <select
                value={docType}
                onChange={(event) => setDocType(event.target.value)}
              >
                <option value="all">All documents</option>
                <option value="md">Markdown only</option>
                <option value="html">HTML only</option>
                <option value="pdf">PDF only</option>
              </select>
            </label>
            <div className="settings-note">
              <Check size={15} />
              Metadata filters are applied before final ranking.
            </div>
          </article>

          <article className="panel evidence-card">
            <div className="aside-title">
              <Layers3 size={16} />
              Retrieved evidence
              {response && <span>{response.contexts.length}</span>}
            </div>
            {!response && (
              <p className="aside-empty">
                Evidence will appear here after a query.
              </p>
            )}
            {response?.contexts.map((context, index) => (
              <button
                className={`evidence-item ${
                  selectedChunk === context.chunk_id ? "active" : ""
                }`}
                key={context.chunk_id}
                onClick={() =>
                  setSelectedChunk(
                    selectedChunk === context.chunk_id
                      ? null
                      : context.chunk_id,
                  )
                }
              >
                <div className="evidence-item-head">
                  <span className="source-icon">
                    <FileText size={15} />
                  </span>
                  <div>
                    <strong>{context.metadata.source}</strong>
                    <span>Chunk {context.metadata.chunk_index + 1}</span>
                  </div>
                  <span className="rank-badge">#{index + 1}</span>
                </div>
                <div className="relevance-row">
                  <span>Relevance</span>
                  <div>
                    <i
                      style={{
                        width: `${Math.max(8, context.score * 100)}%`,
                      }}
                    />
                  </div>
                  <strong>{(context.score * 100).toFixed(0)}%</strong>
                </div>
                {selectedChunk === context.chunk_id && (
                  <p className="evidence-text">{context.text}</p>
                )}
                <ChevronRight size={15} className="evidence-chevron" />
              </button>
            ))}
          </article>
        </aside>
      </section>
    </div>
  );
}
