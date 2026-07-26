import type {
  Context,
  DocumentSummary,
  Health,
  QueryResponse,
  Reports,
} from "./types";

export const questions = [
  "How quickly is a Priority One incident acknowledged?",
  "What encryption protects stored customer data?",
  "Which algorithm signs webhook requests?",
  "When does a subscription upgrade take effect?",
];

export const demoHealth: Health = {
  status: "demo",
  vectors: 12,
  store: "chroma",
  embedding_model: "local/hash-hybrid-ngram-v1",
  embedding_dim: 768,
  chunk_size_words: 120,
  chunk_overlap_words: 25,
  max_upload_mb: 15,
  max_upload_files: 10,
};

export const demoDocuments: DocumentSummary[] = [
  {
    source: "identity.md",
    source_id: "s_c695789aa61f5646",
    doc_type: "md",
    topic: "identity & access",
    chunks: 2,
    content_sha256: "09ba57251025c948",
    managed_upload: false,
  },
  {
    source: "billing.md",
    source_id: "s_8fd6293ef863b04e",
    doc_type: "md",
    topic: "plans & billing",
    chunks: 2,
    content_sha256: "2aa2f4f29c4905ef",
    managed_upload: false,
  },
  {
    source: "reliability.md",
    source_id: "s_b0ec22704d551a4d",
    doc_type: "md",
    topic: "reliability & support",
    chunks: 2,
    content_sha256: "552f5df7c48aaea2",
    managed_upload: false,
  },
  {
    source: "data-governance.md",
    source_id: "s_d2998b3f919bc883",
    doc_type: "md",
    topic: "data governance",
    chunks: 2,
    content_sha256: "e4ddf77b338c2cfb",
    managed_upload: false,
  },
  {
    source: "deployment.md",
    source_id: "s_ce4786b3f2ccf906",
    doc_type: "md",
    topic: "deployment workflow",
    chunks: 2,
    content_sha256: "d5adb332585853fb",
    managed_upload: false,
  },
  {
    source: "integrations.html",
    source_id: "s_e52c369b05a40b64",
    doc_type: "html",
    topic: "integrations",
    chunks: 2,
    content_sha256: "141755e0bd659e67",
    managed_upload: false,
  },
];

export const demoReports: Reports = {
  rag: {
    run: {
      store: "chroma",
      vector_count: 12,
      embedding_dimensionality: 768,
      question_count: 20,
      k: 3,
    },
    retrieval: {
      "recall@3": 1,
      hit_rate: 1,
      mrr: 0.9722,
      "ndcg@3": 0.9795,
      context_precision: 0.5185,
    },
    answer: {
      faithfulness: 1,
      answer_relevance: 0.9955,
      exact_match: 0.95,
      token_f1: 0.9955,
    },
    no_answer_accuracy: 1,
    latency_ms: {
      retrieval_p50: 2.085,
      retrieval_p95: 2.469,
      retrieval_min: 1.431,
      retrieval_max: 4.641,
    },
    cases: [],
  },
  judge: {
    run: {
      mode: "pairwise-reference-based",
      case_count: 12,
      repeats: 2,
    },
    comparison: {
      config_a: "prompt-v2-grounded",
      config_b: "prompt-v1-generic",
      declared_winner: "A",
      wins: { A: 8, B: 3, TIE: 1 },
      mean_overall_score: { A: 4.4656, B: 4.1001 },
      pass_rate: { A: 0.9167, B: 0.8333 },
    },
    bias: {
      position_flip_rate: 0,
      test_retest_flip_rate: 0,
      self_enhancement_guard: "passed",
    },
    audit: {
      judge_calls: 48,
      total_tokens: 48444,
      fallback_parse_count: 16,
    },
    cases: [],
  },
  validation: {
    agreement_rate: 1,
    cohen_kappa: 1,
    position_flip_rate: 0,
    test_retest_flip_rate: 0,
    adversarial_probes: { count: 4, success_rate: 1 },
  },
  cost: {
    assumptions: {
      embedding_dimensions: 768,
      queries_per_month: 100000,
      metadata_bytes_per_record: 1024,
    },
    rows: [
      {
        vectors: 100000,
        chroma_total_usd_month: 13.06,
        pinecone_serverless_standard_usd_month: 50,
        pinecone_legacy_p1_usd_month: 85.72,
      },
      {
        vectors: 1000000,
        chroma_total_usd_month: 51.46,
        pinecone_serverless_standard_usd_month: 50,
        pinecone_legacy_p1_usd_month: 85.72,
      },
      {
        vectors: 10000000,
        chroma_total_usd_month: 320.73,
        pinecone_serverless_standard_usd_month: 79.05,
        pinecone_legacy_p1_usd_month: 857.2,
      },
    ],
  },
};

const demoAnswers = [
  {
    terms: ["priority", "incident", "acknowledged"],
    answer:
      "The on-call engineer acknowledges Priority One incidents within 15 minutes.",
    source: "reliability.md",
    chunk: "c_9fcb117d8b441d45",
    text: "The on-call engineer acknowledges Priority One incidents within 15 minutes. Nimbus publishes an initial customer update within 30 minutes of confirming a Priority One incident. Subsequent updates are posted every 60 minutes until mitigation.",
  },
  {
    terms: ["encryption", "encrypted", "stored", "customer", "data"],
    answer:
      "Nimbus encrypts stored customer data with AES-256 and encrypts network traffic with TLS 1.3.",
    source: "data-governance.md",
    chunk: "c_33b2facd37d78a5d",
    text: "Nimbus encrypts stored customer data with AES-256 and encrypts network traffic with TLS 1.3. Production backups are created every six hours. Backups are retained for 30 days.",
  },
  {
    terms: ["algorithm", "signs", "webhook", "signature"],
    answer:
      "Every webhook request includes an X-Nimbus-Signature header computed with HMAC-SHA256.",
    source: "integrations.html",
    chunk: "c_3537509368fed839",
    text: "Every webhook request includes an X-Nimbus-Signature header computed with HMAC-SHA256. Receivers should calculate the signature over the unmodified request body and compare it using a constant-time function.",
  },
  {
    terms: ["subscription", "upgrade", "effect"],
    answer:
      "Subscription upgrades take effect immediately and the remaining billing period is prorated.",
    source: "billing.md",
    chunk: "c_3b7911083ed3cda0",
    text: "Subscription upgrades take effect immediately and the remaining billing period is prorated. Downgrades take effect at the start of the next billing cycle.",
  },
];

export function demoQuery(question: string): QueryResponse {
  const normalized = question.toLowerCase();
  const matched = [...demoAnswers]
    .map((item) => ({
      item,
      score: item.terms.filter((term) => normalized.includes(term)).length,
    }))
    .sort((a, b) => b.score - a.score)[0];
  const noContext = !matched || matched.score === 0;
  const item = noContext ? null : matched.item;
  const context: Context[] = item
    ? [
        {
          chunk_id: item.chunk,
          score: 0.91,
          text: item.text,
          metadata: {
            source: item.source,
            doc_type: item.source.endsWith(".html") ? "html" : "md",
            topic: item.source.replace(/\.(md|html)$/, ""),
            chunk_index: 0,
          },
        },
      ]
    : [];
  return {
    request_id: `demo-${Date.now()}`,
    answer: item
      ? `${item.answer} [${item.chunk}]`
      : "I don't have enough relevant context in the indexed documents to answer.",
    citations: item ? [item.chunk] : [],
    contexts: context,
    usage: {
      input_tokens: Math.max(12, Math.ceil(question.length / 4) + 42),
      output_tokens: item ? Math.ceil(item.answer.length / 4) : 17,
      total_tokens: item
        ? Math.ceil((question.length + item.answer.length) / 4) + 42
        : 29,
      estimated: true,
    },
    latency_ms: { retrieval: 2.14, generation: 0.38, total: 2.52 },
  };
}
