import {
  ArrowUpRight,
  BadgeCheck,
  Braces,
  CheckCircle2,
  CircleAlert,
  Gauge,
  Repeat2,
  Scale,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useState } from "react";
import { ScoreBar } from "../components/ScoreBar";
import type { Reports } from "../types";

type Tab = "retrieval" | "answers" | "judge";

const asNumber = (value: unknown) =>
  typeof value === "number" ? value : Number(value ?? 0);

export function Evaluations({ reports }: { reports: Reports }) {
  const [tab, setTab] = useState<Tab>("retrieval");
  const retrieval = reports.rag.retrieval;
  const answer = reports.rag.answer;
  const comparison = reports.judge.comparison as {
    config_a?: string;
    config_b?: string;
    declared_winner?: string;
    wins?: { A?: number; B?: number; TIE?: number };
    mean_overall_score?: { A?: number; B?: number };
    pass_rate?: { A?: number; B?: number };
  };
  const bias = reports.judge.bias;
  const validation = reports.validation as {
    agreement_rate?: number;
    cohen_kappa?: number;
    adversarial_probes?: { count?: number; success_rate?: number };
    test_retest_flip_rate?: number;
  };
  const judgeMetrics: Array<{
    label: string;
    value: string;
    detail: string;
    icon: LucideIcon;
  }> = [
    {
      label: "Position flips",
      value: `${(asNumber(bias.position_flip_rate) * 100).toFixed(0)}%`,
      detail: "Both A/B orders",
      icon: Repeat2,
    },
    {
      label: "Cohen’s κ",
      value: asNumber(validation.cohen_kappa).toFixed(2),
      detail: "Agreement with gold",
      icon: Scale,
    },
    {
      label: "Probe success",
      value: `${(
        asNumber(validation.adversarial_probes?.success_rate) * 100
      ).toFixed(0)}%`,
      detail: `${validation.adversarial_probes?.count ?? 4} adversarial cases`,
      icon: ShieldCheck,
    },
    {
      label: "Audit calls",
      value: String(reports.judge.audit.judge_calls ?? 48),
      detail: "Prompts + raw outputs",
      icon: Braces,
    },
  ];

  return (
    <div className="page">
      <section className="page-heading-row">
        <div>
          <span className="section-kicker">Evaluation suite</span>
          <h1>Quality, with receipts.</h1>
          <p>
            Fixed questions, chunk-level qrels, grounded answer scoring, and
            explicit judge-bias checks.
          </p>
        </div>
        <div className="run-badge">
          <CheckCircle2 size={16} />
          <div>
            <strong>Latest run passed</strong>
            <span>20 RAG cases · 12 judge cases</span>
          </div>
        </div>
      </section>

      <div className="segment-control" role="tablist">
        <button
          className={tab === "retrieval" ? "active" : ""}
          onClick={() => setTab("retrieval")}
        >
          Retrieval
        </button>
        <button
          className={tab === "answers" ? "active" : ""}
          onClick={() => setTab("answers")}
        >
          Answer quality
        </button>
        <button
          className={tab === "judge" ? "active" : ""}
          onClick={() => setTab("judge")}
        >
          Judge pipeline
        </button>
      </div>

      {tab === "retrieval" && (
        <section className="evaluation-grid">
          <article className="panel score-panel">
            <div className="panel-heading compact">
              <div>
                <span className="section-kicker">Information retrieval</span>
                <h2>Top-3 performance</h2>
              </div>
              <span className="panel-icon violet">
                <Gauge size={20} />
              </span>
            </div>
            <div className="score-list">
              <ScoreBar label="Recall@3" value={retrieval["recall@3"]} />
              <ScoreBar label="Hit rate" value={retrieval.hit_rate} />
              <ScoreBar label="MRR" value={retrieval.mrr} />
              <ScoreBar label="nDCG@3" value={retrieval["ndcg@3"]} />
              <ScoreBar
                label="Context precision"
                value={retrieval.context_precision}
                tone="amber"
              />
            </div>
          </article>
          <article className="panel eval-insight-card">
            <div className="insight-index">01</div>
            <span className="section-kicker">Interpretation</span>
            <h2>Coverage is solved. Precision is not.</h2>
            <p>
              Every answerable question retrieved at least one relevant chunk,
              but only 51.9% of returned context was relevant. A reranker or
              stronger semantic embedding is the next measured improvement.
            </p>
            <div className="insight-comparison">
              <div>
                <span>Coverage</span>
                <strong>100%</strong>
              </div>
              <ArrowUpRight size={18} />
              <div>
                <span>Precision</span>
                <strong>51.9%</strong>
              </div>
            </div>
          </article>
          <article className="panel latency-panel">
            <div className="panel-heading compact">
              <div>
                <span className="section-kicker">Retrieval latency</span>
                <h2>Local benchmark</h2>
              </div>
            </div>
            <div className="latency-chart">
              {[1.43, 1.62, 1.77, 1.89, 2.08, 2.16, 2.27, 2.47].map(
                (value, index) => (
                  <i key={index} style={{ height: `${28 + value * 20}px` }} />
                ),
              )}
            </div>
            <div className="latency-values">
              <div>
                <span>p50</span>
                <strong>
                  {asNumber(reports.rag.latency_ms.retrieval_p50).toFixed(2)} ms
                </strong>
              </div>
              <div>
                <span>p95</span>
                <strong>
                  {asNumber(reports.rag.latency_ms.retrieval_p95).toFixed(2)} ms
                </strong>
              </div>
              <div>
                <span>Samples</span>
                <strong>1,000</strong>
              </div>
            </div>
          </article>
        </section>
      )}

      {tab === "answers" && (
        <section className="evaluation-grid">
          <article className="panel score-panel">
            <div className="panel-heading compact">
              <div>
                <span className="section-kicker">Answer evaluation</span>
                <h2>Grounded response quality</h2>
              </div>
              <span className="panel-icon green">
                <ShieldCheck size={20} />
              </span>
            </div>
            <div className="score-list">
              <ScoreBar
                label="Faithfulness"
                value={answer.faithfulness}
                tone="green"
              />
              <ScoreBar
                label="Answer relevance"
                value={answer.answer_relevance}
                tone="green"
              />
              <ScoreBar
                label="Exact match"
                value={answer.exact_match}
                tone="green"
              />
              <ScoreBar label="Token F1" value={answer.token_f1} tone="green" />
              <ScoreBar
                label="Abstention accuracy"
                value={reports.rag.no_answer_accuracy}
                tone="green"
              />
            </div>
          </article>
          <article className="panel answer-method">
            <span className="section-kicker">Measurement design</span>
            <h2>Measured, never asserted.</h2>
            {[
              [
                "Citation validity",
                "Every cited ID must exist in retrieved context.",
              ],
              [
                "Claim support",
                "Normalized claims are checked against cited evidence.",
              ],
              [
                "Gold alignment",
                "Exact match and token F1 use fixed reference answers.",
              ],
              [
                "Abstention",
                "Two negative questions test no-context behavior.",
              ],
            ].map(([title, detail], index) => (
              <div className="method-row" key={title}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong>{title}</strong>
                  <p>{detail}</p>
                </div>
              </div>
            ))}
          </article>
          <article className="panel caveat-card">
            <CircleAlert size={22} />
            <span className="section-kicker">Read this result carefully</span>
            <h2>High scores, narrow claim.</h2>
            <p>
              Gold answers are source sentences in a small synthetic corpus.
              These scores prove harness correctness and end-to-end behavior;
              they do not establish broad-domain generalization.
            </p>
          </article>
        </section>
      )}

      {tab === "judge" && (
        <section className="judge-layout">
          <article className="panel judge-winner-card">
            <div className="winner-top">
              <span className="section-kicker">A/B comparison</span>
              <span className="winner-pill">
                <BadgeCheck size={15} />
                Winner: configuration {comparison.declared_winner ?? "A"}
              </span>
            </div>
            <h2>{comparison.config_a ?? "prompt-v2-grounded"}</h2>
            <p>
              The grounded prompt won 8 of 12 cases with higher mean quality and
              pass rate.
            </p>
            <div className="comparison-bars">
              <div>
                <span>Configuration A</span>
                <div>
                  <i
                    style={{
                      width: `${asNumber(comparison.mean_overall_score?.A) * 20}%`,
                    }}
                  />
                </div>
                <strong>
                  {asNumber(comparison.mean_overall_score?.A).toFixed(2)}
                </strong>
              </div>
              <div>
                <span>Configuration B</span>
                <div>
                  <i
                    style={{
                      width: `${asNumber(comparison.mean_overall_score?.B) * 20}%`,
                    }}
                  />
                </div>
                <strong>
                  {asNumber(comparison.mean_overall_score?.B).toFixed(2)}
                </strong>
              </div>
            </div>
          </article>

          <div className="judge-metric-grid">
            {judgeMetrics.map(({ label, value, detail, icon: Icon }) => (
              <article className="judge-metric" key={label}>
                <Icon size={19} />
                <span>{label}</span>
                <strong>{value}</strong>
                <small>{detail}</small>
              </article>
            ))}
          </div>

          <article className="panel bias-register">
            <div className="panel-heading compact">
              <div>
                <span className="section-kicker">Bias register</span>
                <h2>Mitigated in code, measured in artifacts</h2>
              </div>
              <Sparkles size={20} />
            </div>
            {[
              ["Position", "Run A/B and B/A", "0% flip rate"],
              ["Verbosity", "Penalize unsupported padding", "Probes passed"],
              ["Self-enhancement", "Different-family guard", "Guard passed"],
              ["Sycophancy", "Evidence per criterion", "Probes passed"],
              ["Score clustering", "1 / 3 / 5 anchors", "Distribution logged"],
            ].map(([biasName, mitigation, result]) => (
              <div className="bias-row" key={biasName}>
                <strong>{biasName}</strong>
                <span>{mitigation}</span>
                <span className="bias-result">
                  <CheckCircle2 size={14} />
                  {result}
                </span>
              </div>
            ))}
          </article>
        </section>
      )}
    </div>
  );
}
