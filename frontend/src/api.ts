import { demoDocuments, demoHealth, demoQuery, demoReports } from "./data";
import type {
  DeleteDocumentResponse,
  DocumentSummary,
  Health,
  IngestResponse,
  QueryResponse,
  Reports,
} from "./types";

const STORAGE_KEY = "grounded-ops-api-base";
const MODE_KEY = "grounded-ops-mode-v2";

export type ConnectionMode = "live" | "demo";

export function getConnectionMode(): ConnectionMode {
  if (typeof window === "undefined") return "demo";
  const stored = localStorage.getItem(MODE_KEY);
  if (stored === "live" || stored === "demo") return stored;
  return import.meta.env.VITE_DEFAULT_API_MODE === "live" ? "live" : "demo";
}

export function setConnectionMode(mode: ConnectionMode): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(MODE_KEY, mode);
}

export function getApiBase(): string {
  if (typeof window === "undefined") return "";
  const configured = (
    localStorage.getItem(STORAGE_KEY) ||
    import.meta.env.VITE_API_BASE_URL ||
    ""
  ).trim();
  if (!configured) return "";
  try {
    const parsed = new URL(configured, window.location.origin);
    parsed.hash = "";
    parsed.search = "";
    return parsed.toString().replace(/\/$/, "");
  } catch {
    return configured.split(/[?#]/, 1)[0].replace(/\/$/, "");
  }
}

export function setApiBase(value: string): void {
  if (typeof window === "undefined") return;
  const configured = value.trim();
  if (!configured) {
    localStorage.setItem(STORAGE_KEY, "");
    return;
  }
  try {
    const parsed = new URL(configured, window.location.origin);
    parsed.hash = "";
    parsed.search = "";
    localStorage.setItem(
      STORAGE_KEY,
      parsed.toString().replace(/\/$/, ""),
    );
  } catch {
    localStorage.setItem(
      STORAGE_KEY,
      configured.split(/[?#]/, 1)[0].replace(/\/$/, ""),
    );
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  const isFormData =
    typeof FormData !== "undefined" && init?.body instanceof FormData;
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers,
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      // Keep the HTTP status fallback.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export async function getHealth(): Promise<Health> {
  if (getConnectionMode() === "demo") return demoHealth;
  return request<Health>("/health", { cache: "no-store" });
}

export async function queryRag(
  question: string,
  k: number,
  docType: string,
): Promise<QueryResponse> {
  if (getConnectionMode() === "demo") {
    await new Promise((resolve) => setTimeout(resolve, 520));
    return demoQuery(question);
  }
  return request<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify({
      question,
      k,
      metadata_filter: docType === "all" ? null : { doc_type: docType },
    }),
  });
}

export async function getDocuments(): Promise<DocumentSummary[]> {
  if (getConnectionMode() === "demo") return demoDocuments;
  const response = await request<{ documents: DocumentSummary[] }>(
    "/documents",
    { cache: "no-store" },
  );
  return response.documents;
}

export async function deleteDocument(
  sourceId: string,
): Promise<DeleteDocumentResponse> {
  if (getConnectionMode() === "demo") {
    throw new Error(
      "Demo mode cannot delete documents. Open Settings and select Live FastAPI service.",
    );
  }
  return request<DeleteDocumentResponse>(
    `/documents/${encodeURIComponent(sourceId)}/delete`,
    { method: "POST" },
  );
}

export async function getReports(): Promise<Reports> {
  if (getConnectionMode() === "demo") return demoReports;
  return request<Reports>("/reports");
}

export async function ingestPath(path: string): Promise<IngestResponse> {
  if (getConnectionMode() === "demo") {
    throw new Error(
      "Demo mode cannot index files. Open Settings and select Live FastAPI service.",
    );
  }
  return request<IngestResponse>("/ingest", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

export async function uploadDocuments(
  files: File[],
  onProgress: (percent: number) => void,
): Promise<IngestResponse> {
  if (getConnectionMode() === "demo") {
    throw new Error(
      "Demo mode cannot upload files. Open Settings and select Live FastAPI service.",
    );
  }

  const formData = new FormData();
  files.forEach((file) => formData.append("files", file, file.name));

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${getApiBase()}/upload`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.min(95, Math.round((event.loaded / event.total) * 95)));
      }
    };
    xhr.onerror = () =>
      reject(new Error("Upload failed. Check the API connection."));
    xhr.onload = () => {
      const payload =
        typeof xhr.response === "object" && xhr.response
          ? xhr.response
          : JSON.parse(xhr.responseText || "{}");
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(
          new Error(
            typeof payload.detail === "string"
              ? payload.detail
              : `Upload failed (${xhr.status}).`,
          ),
        );
        return;
      }
      onProgress(100);
      resolve(payload as IngestResponse);
    };
    xhr.send(formData);
  });
}
