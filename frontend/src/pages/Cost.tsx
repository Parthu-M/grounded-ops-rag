import {
  ArrowDownRight,
  Calculator,
  CircleDollarSign,
  Cloud,
  Database,
  Info,
  Server,
} from "lucide-react";
import type { Reports } from "../types";

const money = (value: unknown) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(Number(value ?? 0));

const vectorLabel = (value: unknown) => {
  const count = Number(value ?? 0);
  if (count >= 1_000_000) return `${count / 1_000_000}M`;
  return `${count / 1_000}K`;
};

export function Cost({ reports }: { reports: Reports }) {
  const rows = reports.cost.rows;
  const max = Math.max(
    ...rows.flatMap((row) => [
      Number(row.chroma_total_usd_month),
      Number(row.pinecone_serverless_standard_usd_month),
      Number(row.pinecone_legacy_p1_usd_month),
    ]),
  );

  return (
    <div className="page">
      <section className="page-heading-row">
        <div>
          <span className="section-kicker">Cost model</span>
          <h1>Cheap where it counts.</h1>
          <p>Direct infrastructure comparison with every assumption exposed.</p>
        </div>
        <div className="model-scope">
          <Calculator size={17} />
          <span>
            Scenario
            <strong>100K queries / month</strong>
          </span>
        </div>
      </section>

      <section className="cost-hero-grid">
        <article className="cost-highlight dark">
          <div className="cost-highlight-head">
            <span className="cost-icon">
              <Database size={20} />
            </span>
            <span>Chroma self-hosted</span>
          </div>
          <strong>$13.06</strong>
          <p>per month at 100K vectors</p>
          <div className="savings-pill">
            <ArrowDownRight size={15} />
            74% below current managed minimum
          </div>
        </article>
        <article className="cost-highlight">
          <div className="cost-highlight-head">
            <span className="cost-icon muted">
              <Cloud size={20} />
            </span>
            <span>Serverless managed</span>
          </div>
          <strong>$50.00</strong>
          <p>monthly Standard minimum</p>
          <div className="neutral-pill">Operations included</div>
        </article>
        <article className="cost-highlight">
          <div className="cost-highlight-head">
            <span className="cost-icon muted">
              <Server size={20} />
            </span>
            <span>Legacy pods</span>
          </div>
          <strong>$85.72</strong>
          <p>one always-on pod equivalent</p>
          <div className="neutral-pill">Predictable capacity</div>
        </article>
      </section>

      <section className="panel cost-chart-panel">
        <div className="panel-heading">
          <div>
            <span className="section-kicker">Scale comparison</span>
            <h2>Monthly direct infrastructure cost</h2>
          </div>
          <div className="chart-legend">
            <span>
              <i className="legend-chroma" />
              Chroma
            </span>
            <span>
              <i className="legend-serverless" />
              Serverless
            </span>
            <span>
              <i className="legend-pods" />
              Legacy pods
            </span>
          </div>
        </div>
        <div className="cost-bars">
          {rows.map((row) => (
            <div className="cost-scale-row" key={String(row.vectors)}>
              <strong>{vectorLabel(row.vectors)} vectors</strong>
              <div className="cost-series">
                {[
                  ["chroma", row.chroma_total_usd_month],
                  ["serverless", row.pinecone_serverless_standard_usd_month],
                  ["pods", row.pinecone_legacy_p1_usd_month],
                ].map(([name, raw]) => {
                  const value = Number(raw);
                  return (
                    <div className="cost-bar-row" key={String(name)}>
                      <span>{money(value)}</span>
                      <div>
                        <i
                          className={`bar-${name}`}
                          style={{
                            width: `${Math.max(2, (value / max) * 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="cost-lower-grid">
        <article className="panel assumption-card">
          <div className="panel-heading compact">
            <div>
              <span className="section-kicker">Model inputs</span>
              <h2>Explicit assumptions</h2>
            </div>
            <CircleDollarSign size={20} />
          </div>
          <dl>
            <div>
              <dt>Embedding dimensions</dt>
              <dd>768 float32</dd>
            </div>
            <div>
              <dt>Metadata per record</dt>
              <dd>1 KB</dd>
            </div>
            <div>
              <dt>Queries per month</dt>
              <dd>100,000</dd>
            </div>
            <div>
              <dt>Replication</dt>
              <dd>None</dd>
            </div>
          </dl>
        </article>
        <article className="panel cost-truth-card">
          <Info size={21} />
          <span className="section-kicker">The honest conclusion</span>
          <h2>Self-hosting does not always win.</h2>
          <p>
            Chroma is compelling at 100K, near parity at 1M, and more expensive
            than current serverless at 10M in this scenario. Add even a few
            engineer-hours of monthly operations and the managed crossover
            happens earlier.
          </p>
        </article>
      </section>
    </div>
  );
}
