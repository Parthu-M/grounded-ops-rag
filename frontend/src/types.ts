export type Page =
  | "overview"
  | "playground"
  | "knowledge"
  | "evaluations"
  | "cost"
  | "settings";

export interface Health {
  status: string;
  vectors: number;
  store: string;
  embedding_model: string;
  embedding_dim: number;
  chunk_size_words: number;
  chunk_overlap_words: number;
  max_upload_mb: number;
  max_upload_files: number;
}

export interface Context {
  chunk_id: string;
  score: number;
  text: string;
  metadata: {
    source: string;
    doc_type: string;
    topic: string;
    chunk_index: number;
    [key: string]: string | number;
  };
}

export interface QueryResponse {
  request_id: string;
  answer: string;
  citations: string[];
  contexts: Context[];
  usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    estimated: boolean;
  };
  latency_ms: {
    retrieval: number;
    generation: number;
    total: number;
  };
}

export interface DocumentSummary {
  source: string;
  source_id: string;
  doc_type: string;
  topic: string;
  chunks: number;
  content_sha256: string;
  managed_upload: boolean;
}

export interface DeleteDocumentResponse {
  source_id: string;
  chunks_deleted: number;
  file_deleted: boolean;
  total_vectors: number;
}

export interface IngestedDocument {
  source: string;
  source_id: string;
  content_sha256: string;
  chunks_written: number;
  original_name?: string;
  stored_name?: string;
  size_bytes?: number;
}

export interface IngestResponse {
  documents: number;
  chunks_written: number;
  total_vectors: number;
  results?: IngestedDocument[];
  simulated?: boolean;
}

export interface Reports {
  rag: {
    run: Record<string, string | number>;
    retrieval: Record<string, number>;
    answer: Record<string, number>;
    no_answer_accuracy: number;
    latency_ms: Record<string, number>;
    cases: Array<Record<string, unknown>>;
  };
  judge: {
    run: Record<string, unknown>;
    comparison: Record<string, unknown>;
    bias: Record<string, unknown>;
    audit: Record<string, unknown>;
    cases: Array<Record<string, unknown>>;
  };
  validation: Record<string, unknown>;
  cost: {
    assumptions: Record<string, unknown>;
    rows: Array<Record<string, string | number>>;
  };
}
