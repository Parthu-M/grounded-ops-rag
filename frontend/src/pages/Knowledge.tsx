import {
  BookOpen,
  CheckCircle2,
  CloudUpload,
  FileCode2,
  FileText,
  FolderSync,
  Hash,
  LoaderCircle,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Trash2,
  X,
} from "lucide-react";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
  type KeyboardEvent,
} from "react";
import { deleteDocument, ingestPath, uploadDocuments } from "../api";
import type { DocumentSummary, Health } from "../types";

const SUPPORTED_EXTENSIONS = [".pdf", ".html", ".htm", ".md", ".markdown"];

interface KnowledgeProps {
  documents: DocumentSummary[];
  health: Health;
  connection: "online" | "demo" | "offline";
  onRefresh: () => Promise<void>;
  onOpenSettings: () => void;
  onNotify: (type: "success" | "error", message: string) => void;
}

type IngestMode = "upload" | "path";

function extensionOf(filename: string): string {
  const dot = filename.lastIndexOf(".");
  return dot >= 0 ? filename.slice(dot).toLowerCase() : "";
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function Knowledge({
  documents,
  health,
  connection,
  onRefresh,
  onOpenSettings,
  onNotify,
}: KnowledgeProps) {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [showIngest, setShowIngest] = useState(false);
  const [mode, setMode] = useState<IngestMode>("upload");
  const [path, setPath] = useState("data/corpus");
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [pendingDelete, setPendingDelete] =
    useState<DocumentSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [validationError, setValidationError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const visible = useMemo(
    () =>
      documents.filter((document) => {
        const matchesSearch = `${document.source} ${document.topic}`
          .toLowerCase()
          .includes(search.toLowerCase());
        const matchesType =
          typeFilter === "all" || document.doc_type === typeFilter;
        return matchesSearch && matchesType;
      }),
    [documents, search, typeFilter],
  );

  const resetModal = () => {
    setShowIngest(false);
    setFiles([]);
    setProgress(0);
    setValidationError("");
    setDragging(false);
  };

  const closeModal = () => {
    if (loading) return;
    resetModal();
  };

  useEffect(() => {
    if (!showIngest && !pendingDelete) return undefined;
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (showIngest) closeModal();
      if (pendingDelete && !deleting) setPendingDelete(null);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  const addFiles = (incoming: File[]) => {
    setValidationError("");
    const maxBytes = health.max_upload_mb * 1024 * 1024;
    const combined = [...files];
    const problems: string[] = [];

    for (const file of incoming) {
      const extension = extensionOf(file.name);
      if (!SUPPORTED_EXTENSIONS.includes(extension)) {
        problems.push(`${file.name}: unsupported file type`);
        continue;
      }
      if (file.size === 0) {
        problems.push(`${file.name}: file is empty`);
        continue;
      }
      if (file.size > maxBytes) {
        problems.push(`${file.name}: larger than ${health.max_upload_mb} MB`);
        continue;
      }
      const existingIndex = combined.findIndex(
        (item) => item.name.toLowerCase() === file.name.toLowerCase(),
      );
      if (existingIndex >= 0) {
        combined[existingIndex] = file;
      } else {
        combined.push(file);
      }
    }

    if (combined.length > health.max_upload_files) {
      problems.push(
        `Select no more than ${health.max_upload_files} files at once`,
      );
      combined.splice(health.max_upload_files);
    }
    setFiles(combined);
    if (problems.length) setValidationError(problems.join(". "));
  };

  const handleFileInput = (event: ChangeEvent<HTMLInputElement>) => {
    addFiles(Array.from(event.target.files ?? []));
    event.target.value = "";
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    addFiles(Array.from(event.dataTransfer.files));
  };

  const handleDropzoneKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInputRef.current?.click();
    }
  };

  const ingest = async () => {
    if (mode === "upload" && !files.length) return;
    if (mode === "path" && !path.trim()) return;
    setLoading(true);
    setProgress(0);
    setValidationError("");
    try {
      const result =
        mode === "upload"
          ? await uploadDocuments(files, setProgress)
          : await ingestPath(path.trim());
      await onRefresh();
      resetModal();
      onNotify(
        "success",
        result.simulated
          ? `Demo simulated ${result.documents} document upload. Select Live API to index real files.`
          : `Indexed ${result.documents} document${result.documents === 1 ? "" : "s"} into ${result.total_vectors} vectors.`,
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Ingestion failed.";
      setValidationError(message);
      onNotify("error", message);
    } finally {
      setLoading(false);
    }
  };

  const syncCorpus = async () => {
    if (connection !== "online") {
      onNotify(
        "error",
        "Connect the Live FastAPI service before syncing server files.",
      );
      onOpenSettings();
      return;
    }
    setSyncing(true);
    try {
      const result = await ingestPath("data/corpus");
      await onRefresh();
      onNotify(
        "success",
        `Synced ${result.documents} documents from data/corpus (${result.total_vectors} vectors total).`,
      );
    } catch (error) {
      onNotify(
        "error",
        error instanceof Error ? error.message : "Corpus sync failed.",
      );
    } finally {
      setSyncing(false);
    }
  };

  const confirmDelete = async () => {
    if (!pendingDelete || deleting) return;
    setDeleting(true);
    try {
      const result = await deleteDocument(pendingDelete.source_id);
      await onRefresh();
      onNotify(
        "success",
        result.file_deleted
          ? `Deleted ${pendingDelete.source} and ${result.chunks_deleted} indexed chunk${result.chunks_deleted === 1 ? "" : "s"}.`
          : `Removed ${pendingDelete.source} from the index. The source file was kept.`,
      );
      setPendingDelete(null);
    } catch (error) {
      onNotify(
        "error",
        error instanceof Error ? error.message : "Document deletion failed.",
      );
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="page">
      <section className="page-heading-row">
        <div>
          <span className="section-kicker">Knowledge</span>
          <h1>Corpus inventory</h1>
          <p>
            Upload documents, inspect content fingerprints, and trace every
            indexed chunk.
          </p>
        </div>
        <div className="page-heading-actions">
          <button
            className="button button-secondary"
            onClick={syncCorpus}
            disabled={syncing}
            title="Index supported files currently stored in data/corpus"
          >
            <RefreshCw className={syncing ? "spin" : ""} size={17} />
            {syncing ? "Syncing" : "Sync data/corpus"}
          </button>
          <button
            className="button button-primary"
            onClick={() => setShowIngest(true)}
          >
            <Plus size={17} />
            Add documents
          </button>
        </div>
      </section>

      {connection !== "online" && (
        <section className="knowledge-connection-warning" role="status">
          <div>
            <strong>
              {connection === "demo"
                ? "Demo mode does not save uploads."
                : "The live API is offline."}
            </strong>
            <span>
              Connect the FastAPI service to index PDFs and update this
              inventory.
            </span>
          </div>
          <button className="button button-secondary" onClick={onOpenSettings}>
            Open connection settings
          </button>
        </section>
      )}

      <section className="knowledge-summary">
        <div>
          <BookOpen size={19} />
          <span>Documents</span>
          <strong>{documents.length}</strong>
        </div>
        <div>
          <Hash size={19} />
          <span>Stored vectors</span>
          <strong>
            {documents.reduce((total, item) => total + item.chunks, 0)}
          </strong>
        </div>
        <div>
          <SlidersHorizontal size={19} />
          <span>Chunk size</span>
          <strong>{health.chunk_size_words} words</strong>
        </div>
        <div>
          <FolderSync size={19} />
          <span>Chunk overlap</span>
          <strong>{health.chunk_overlap_words} words</strong>
        </div>
      </section>

      <section className="panel document-panel">
        <div className="document-toolbar">
          <div className="document-search-controls">
            <div className="search-field">
              <Search size={17} />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search sources or topics"
                aria-label="Search indexed sources"
              />
            </div>
            <select
              className="type-filter"
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value)}
              aria-label="Filter sources by document type"
            >
              <option value="all">All types</option>
              <option value="pdf">PDF</option>
              <option value="html">HTML</option>
              <option value="md">Markdown</option>
            </select>
          </div>
          <span>
            {visible.length} of {documents.length} sources
          </span>
        </div>
        <div className="document-list">
          <div className="document-table-head">
            <span>Source</span>
            <span>Type</span>
            <span>Chunks</span>
            <span>Content fingerprint</span>
            <span>Status</span>
            <span aria-label="Actions" />
          </div>
          {visible.map((document) => (
            <article className="document-row" key={document.source_id}>
              <div className="document-source">
                <span className={`file-badge file-${document.doc_type}`}>
                  {document.doc_type === "html" ? (
                    <FileCode2 size={17} />
                  ) : (
                    <FileText size={17} />
                  )}
                </span>
                <div>
                  <strong>{document.source}</strong>
                  <span>{document.topic.replaceAll("-", " ")}</span>
                </div>
              </div>
              <span className="type-pill">{document.doc_type}</span>
              <strong>{document.chunks}</strong>
              <code>{document.content_sha256.slice(0, 12)}…</code>
              <span className="indexed-status">
                <CheckCircle2 size={15} />
                Indexed
              </span>
              <button
                className="document-delete-button"
                onClick={() => setPendingDelete(document)}
                disabled={connection !== "online"}
                aria-label={
                  document.managed_upload
                    ? `Delete uploaded document ${document.source}`
                    : `Remove ${document.source} from the index`
                }
                title={
                  document.managed_upload
                    ? "Delete upload and indexed vectors"
                    : "Remove from index; keep source file"
                }
              >
                <Trash2 size={16} />
              </button>
            </article>
          ))}
          {!visible.length && (
            <div className="document-empty">
              <Search size={20} />
              <strong>No matching sources</strong>
              <span>Clear the search or select a different document type.</span>
            </div>
          )}
        </div>
      </section>

      {showIngest && (
        <div className="modal-layer" role="presentation">
          <button
            className="modal-scrim"
            onClick={closeModal}
            aria-label="Close ingestion dialog"
          />
          <div
            className="modal-card ingestion-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="ingest-title"
          >
            <div className="modal-title-row">
              <div className="modal-icon">
                <CloudUpload size={22} />
              </div>
              <button
                className="icon-button"
                onClick={closeModal}
                disabled={loading}
                aria-label="Close ingestion dialog"
              >
                <X size={19} />
              </button>
            </div>
            <span className="section-kicker">Idempotent ingestion</span>
            <h2 id="ingest-title">Add knowledge sources</h2>
            <p>
              Upload documents from this device or index a path that already
              exists on the API server.
            </p>

            <div
              className="ingest-tabs"
              role="tablist"
              aria-label="Ingestion method"
            >
              <button
                role="tab"
                aria-selected={mode === "upload"}
                className={mode === "upload" ? "active" : ""}
                onClick={() => setMode("upload")}
                disabled={loading}
              >
                <CloudUpload size={16} />
                Upload files
              </button>
              <button
                role="tab"
                aria-selected={mode === "path"}
                className={mode === "path" ? "active" : ""}
                onClick={() => setMode("path")}
                disabled={loading}
              >
                <FolderSync size={16} />
                Server path
              </button>
            </div>

            {mode === "upload" ? (
              <div className="upload-workspace">
                <input
                  ref={fileInputRef}
                  className="visually-hidden"
                  type="file"
                  accept=".pdf,.html,.htm,.md,.markdown"
                  multiple
                  onChange={handleFileInput}
                />
                <div
                  className={`upload-dropzone ${dragging ? "is-dragging" : ""}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => fileInputRef.current?.click()}
                  onKeyDown={handleDropzoneKey}
                  onDragEnter={(event) => {
                    event.preventDefault();
                    setDragging(true);
                  }}
                  onDragOver={(event) => event.preventDefault()}
                  onDragLeave={() => setDragging(false)}
                  onDrop={handleDrop}
                  aria-label="Choose or drop PDF, HTML, or Markdown documents"
                >
                  <span className="dropzone-icon">
                    <CloudUpload size={24} />
                  </span>
                  <strong>Drop documents here</strong>
                  <span>
                    or <u>browse your device</u> · PDF, HTML, Markdown
                  </span>
                  <small>
                    Up to {health.max_upload_files} files ·{" "}
                    {health.max_upload_mb} MB each
                  </small>
                </div>

                {!!files.length && (
                  <div className="selected-files" aria-live="polite">
                    <div className="selected-files-head">
                      <strong>
                        {files.length} file{files.length === 1 ? "" : "s"} ready
                      </strong>
                      <span>
                        {formatBytes(
                          files.reduce((total, file) => total + file.size, 0),
                        )}
                      </span>
                    </div>
                    {files.map((file) => (
                      <div
                        className="selected-file-row"
                        key={`${file.name}-${file.lastModified}`}
                      >
                        <span className="selected-file-icon">
                          {[".html", ".htm"].includes(
                            extensionOf(file.name),
                          ) ? (
                            <FileCode2 size={16} />
                          ) : (
                            <FileText size={16} />
                          )}
                        </span>
                        <div>
                          <strong>{file.name}</strong>
                          <span>{formatBytes(file.size)}</span>
                        </div>
                        <button
                          onClick={() =>
                            setFiles((current) =>
                              current.filter((item) => item !== file),
                            )
                          }
                          disabled={loading}
                          aria-label={`Remove ${file.name}`}
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="path-workspace">
                <label className="modal-field">
                  <span>File or directory path</span>
                  <input
                    value={path}
                    onChange={(event) => setPath(event.target.value)}
                    placeholder="data/corpus"
                    autoFocus
                    disabled={loading}
                  />
                </label>
                <div className="modal-note">
                  Advanced option for bulk imports and Docker volumes. Paths are
                  restricted to the configured project root and directories are
                  scanned recursively.
                </div>
              </div>
            )}

            {validationError && (
              <div className="upload-error" role="alert">
                {validationError}
              </div>
            )}

            {connection !== "online" && (
              <div className="upload-error" role="alert">
                Files cannot be indexed while the workspace is{" "}
                {connection === "demo" ? "in Demo mode" : "offline"}. Open
                Settings and connect the Live FastAPI service.
              </div>
            )}

            {loading && mode === "upload" && (
              <div className="upload-progress">
                <div>
                  <span>Uploading and indexing</span>
                  <strong>{progress}%</strong>
                </div>
                <div
                  className="progress-track"
                  role="progressbar"
                  aria-label="Upload progress"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={progress}
                >
                  <span style={{ width: `${progress}%` }} />
                </div>
              </div>
            )}

            <div className="ingestion-assurance">
              <ShieldCheck size={17} />
              <span>
                Re-uploading the same filename replaces its previous chunks;
                duplicate vectors are not created.
              </span>
            </div>

            <div className="modal-actions">
              <button
                className="button button-secondary"
                onClick={closeModal}
                disabled={loading}
              >
                Cancel
              </button>
              <button
                className="button button-primary"
                onClick={ingest}
                disabled={
                  loading ||
                  connection !== "online" ||
                  (mode === "upload" ? !files.length : !path.trim())
                }
              >
                {loading ? (
                  <LoaderCircle className="spin" size={17} />
                ) : mode === "upload" ? (
                  <CloudUpload size={17} />
                ) : (
                  <Plus size={17} />
                )}
                {loading
                  ? "Processing"
                  : mode === "upload"
                    ? `Upload ${files.length || ""} document${files.length === 1 ? "" : "s"}`
                    : "Ingest path"}
              </button>
            </div>
          </div>
        </div>
      )}

      {pendingDelete && (
        <div className="modal-layer" role="presentation">
          <button
            className="modal-scrim"
            onClick={() => !deleting && setPendingDelete(null)}
            aria-label="Cancel document deletion"
          />
          <div
            className="modal-card delete-modal"
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="delete-document-title"
            aria-describedby="delete-document-description"
          >
            <div className="delete-modal-icon">
              <Trash2 size={21} />
            </div>
            <span className="section-kicker">
              {pendingDelete.managed_upload
                ? "Delete uploaded document"
                : "Remove indexed document"}
            </span>
            <h2 id="delete-document-title">{pendingDelete.source}</h2>
            <p id="delete-document-description">
              {pendingDelete.managed_upload
                ? `This permanently deletes the stored upload and all ${pendingDelete.chunks} indexed chunks. This action cannot be undone.`
                : `This removes all ${pendingDelete.chunks} chunks from Chroma. The original file stays in data/corpus and can be restored with Sync data/corpus.`}
            </p>
            <div className="modal-actions">
              <button
                className="button button-secondary"
                onClick={() => setPendingDelete(null)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                className="button button-danger"
                onClick={confirmDelete}
                disabled={deleting}
              >
                {deleting ? (
                  <LoaderCircle className="spin" size={17} />
                ) : (
                  <Trash2 size={17} />
                )}
                {deleting
                  ? "Deleting"
                  : pendingDelete.managed_upload
                    ? "Delete permanently"
                    : "Remove from index"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
