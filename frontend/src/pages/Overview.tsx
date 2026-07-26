import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock3,
  Database,
  Gauge,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { Health, Page, Reports } from "../types";
import { MetricCard } from "../components/MetricCard";

interface OverviewProps {
  health: Health;
  reports: Reports;
  onNavigate: (page: Page) => void;
}

export function Overview({ health, reports, onNavigate }: OverviewProps) {
  const retrieval = reports.rag.retrieval;
  const answer = reports.rag.answer;
  const latency = reports.rag.latency_ms;

  return (
    <div className="page">
      <section className="page-hero overview-hero">
        <div>
          <div className="eyebrow">
            <Sparkles size={14} />
            Grounded AI workspace
          </div>
          <h1>
            Know what your
            <br />
            system <em>actually</em> knows.
          </h1>
          <p>
            One operational view for retrieval quality, cited answers, judge
            behavior, latency, and infrastructure cost.
          </p>
          <div className="hero-actions">
            <button
              className="button button-primary"
              onClick={() => onNavigate("playground")}
            >
              Ask the knowledge base
              <ArrowRight size={17} />
            </button>
            <button
              className="button button-secondary"
              onClick={() => onNavigate("evaluations")}
            >
              View evaluation
            </button>
          </div>
        </div>
        <div className="hero-system-card">
          <div className="system-card-head">
            <span>System status</span>
            <span className="live-pill">
              <i />
              Ready
            </span>
          </div>
          <div className="system-orbit">
            <div className="orbit-ring orbit-one" />
            <div className="orbit-ring orbit-two" />
            <div className="orbit-core">
              <Database size={25} />
            </div>
            <span className="orbit-chip chip-one">Retrieve</span>
            <span className="orbit-chip chip-two">Ground</span>
            <span className="orbit-chip chip-three">Evaluate</span>
          </div>
          <div className="system-card-foot">
            <div>
              <strong>{health.vectors}</strong>
              <span>vectors</span>
            </div>
            <div>
              <strong>{health.embedding_dim}</strong>
              <span>dimensions</span>
            </div>
            <div>
              <strong>top-3</strong>
              <span>retrieval</span>
            </div>
          </div>
        </div>
      </section>

      <section className="metric-grid">
        <MetricCard
          label="Retrieval hit rate"
          value={`${((retrieval.hit_rate ?? 0) * 100).toFixed(0)}%`}
          detail="18 of 18 answerable questions"
          icon={Gauge}
          tone="violet"
        />
        <MetricCard
          label="Faithfulness"
          value={`${((answer.faithfulness ?? 0) * 100).toFixed(0)}%`}
          detail="Claims supported by cited context"
          icon={ShieldCheck}
          tone="green"
        />
        <MetricCard
          label="Retrieval p95"
          value={`${Number(latency.retrieval_p95 ?? 0).toFixed(2)} ms`}
          detail="1,000 warmed local samples"
          icon={Clock3}
          tone="amber"
        />
        <MetricCard
          label="Indexed corpus"
          value={`${health.vectors} chunks`}
          detail={`Persistent ${health.store} collection`}
          icon={BookOpen}
          tone="ink"
        />
      </section>

      <section className="overview-lower-grid">
        <article className="panel evaluation-snapshot">
          <div className="panel-heading">
            <div>
              <span className="section-kicker">Quality snapshot</span>
              <h2>Evaluation at a glance</h2>
            </div>
            <button
              className="text-button"
              onClick={() => onNavigate("evaluations")}
            >
              Full report
              <ArrowRight size={15} />
            </button>
          </div>
          <div className="snapshot-row">
            {[
              ["Recall@3", retrieval["recall@3"]],
              ["MRR", retrieval.mrr],
              ["nDCG@3", retrieval["ndcg@3"]],
              ["Answer F1", answer.token_f1],
            ].map(([label, raw]) => {
              const value = Number(raw);
              return (
                <div className="snapshot-item" key={String(label)}>
                  <div className="ring-score">
                    <svg viewBox="0 0 44 44">
                      <circle cx="22" cy="22" r="18" />
                      <circle
                        className="ring-progress"
                        cx="22"
                        cy="22"
                        r="18"
                        pathLength="100"
                        strokeDasharray={`${value * 100} 100`}
                      />
                    </svg>
                    <strong>{(value * 100).toFixed(0)}</strong>
                  </div>
                  <span>{label}</span>
                </div>
              );
            })}
          </div>
          <div className="snapshot-note">
            <CheckCircle2 size={18} />
            <div>
              <strong>
                All answerable questions retrieved relevant context.
              </strong>
              <span>
                Context precision remains the clearest optimization target at{" "}
                {(Number(retrieval.context_precision) * 100).toFixed(1)}%.
              </span>
            </div>
          </div>
        </article>

        <article className="panel principle-panel">
          <div className="principle-number">01</div>
          <span className="section-kicker">Operating principle</span>
          <h2>Evidence first. Fluency second.</h2>
          <p>
            Every answer is paired with the chunks that earned it. No evidence
            means a clear abstention—not a plausible invention.
          </p>
          <div className="principle-rule" />
          <div className="principle-meta">
            <span>Grounded generation</span>
            <span>Exact chunk citations</span>
            <span>Measured abstention</span>
          </div>
        </article>
      </section>
    </div>
  );
}
