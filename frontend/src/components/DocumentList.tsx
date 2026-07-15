import { useState, useEffect, useRef, useCallback } from 'react'
import {
  uploadViaBackend,
  uploadDirect,
  requestPresignedUrl,
  confirmUpload,
  getDocuments,
  getDownloadUrl,
  getDocumentStatus,
} from '../api/client'
import type { Document } from '../api/client'

interface Props {
  token: string
}

type UploadMethod = 'A' | 'B'

const TERMINAL_STATUSES = new Set(['embedded', 'failed'])
const POLL_INTERVAL_MS = 3000

function formatSize(bytes: number | null): string {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, React.CSSProperties> = {
    ready:      { background: '#2563eb22', color: '#2563eb' },
    processing: { background: '#d9770622', color: '#d97706' },
    embedded:   { background: '#16a34a22', color: '#16a34a' },
    failed:     { background: '#dc262622', color: '#dc2626' },
    pending:    { background: '#6b728022', color: '#6b7280' },
  }
  const style = styles[status] ?? styles.pending
  return (
    <span style={{
      ...style,
      fontSize: '11px',
      fontWeight: 600,
      padding: '2px 7px',
      borderRadius: '4px',
      textTransform: 'uppercase',
      letterSpacing: '0.04em',
    }}>
      {status === 'processing' ? '⏳ ' : ''}{status}
    </span>
  )
}

function DocumentList({ token }: Props) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState<string | null>(null)

  const [method, setMethod] = useState<UploadMethod>('A')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const startPolling = useCallback(
    (docIds: number[]) => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current)

      const poll = async () => {
        const activeIds = docIds.filter((id) => {
          const doc = documents.find((d) => d.id === id)
          return doc ? !TERMINAL_STATUSES.has(doc.status) : true
        })
        if (activeIds.length === 0) return

        const updates = await Promise.allSettled(
          activeIds.map((id) => getDocumentStatus(token, id))
        )

        let hasActive = false
        setDocuments((prev) => {
          const next = [...prev]
          updates.forEach((result, i) => {
            if (result.status !== 'fulfilled') return
            const { id, status } = result.value
            const idx = next.findIndex((d) => d.id === id)
            if (idx !== -1) {
              next[idx] = { ...next[idx], status }
              if (!TERMINAL_STATUSES.has(status)) hasActive = true
            }
          })
          return next
        })

        if (hasActive) {
          pollTimerRef.current = setTimeout(poll, POLL_INTERVAL_MS)
        }
      }

      pollTimerRef.current = setTimeout(poll, POLL_INTERVAL_MS)
    },
    [token, documents]
  )

  useEffect(() => {
    getDocuments(token)
      .then((docs) => {
        setDocuments(docs)
        const activeIds = docs
          .filter((d) => !TERMINAL_STATUSES.has(d.status))
          .map((d) => d.id)
        if (activeIds.length > 0) startPolling(activeIds)
      })
      .catch(() => setListError('Failed to load documents'))
      .finally(() => setLoading(false))

    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
    }
  }, [token])

  async function handleUploadA() {
    if (!selectedFile) return
    setUploading(true)
    setUploadError(null)
    setProgress(0)
    try {
      const doc = await uploadViaBackend(token, selectedFile, setProgress)
      setDocuments((prev) => [doc, ...prev])
      clearFile()
      startPolling([doc.id])
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }

  async function handleUploadB() {
    if (!selectedFile) return
    setUploading(true)
    setUploadError(null)
    setProgress(0)
    try {
      const { document_id, upload_url } = await requestPresignedUrl(
        token,
        selectedFile.name,
        selectedFile.type
      )
      await uploadDirect(upload_url, selectedFile, setProgress)
      const doc = await confirmUpload(token, document_id)
      setDocuments((prev) => [doc, ...prev])
      clearFile()
      startPolling([doc.id])
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }

  function clearFile() {
    setSelectedFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function handleDownload(doc: Document) {
    try {
      const url = await getDownloadUrl(token, doc.id)
      window.open(url, '_blank')
    } catch {
      setListError('Failed to get download link')
    }
  }

  function getUploadLabel() {
    if (!uploading) return 'Upload'
    if (method === 'A') return `Uploading ${progress}%`
    if (progress === 0) return 'Requesting URL…'
    if (progress === 100) return 'Confirming…'
    return `Sending ${progress}%`
  }

  return (
    <div style={{ marginTop: '40px' }}>
      <div className="threads-header">
        <h1>Documents</h1>
        <p>Upload files for RAG ingestion</p>
      </div>

      <div className="upload-method-toggle">
        <button
          className={method === 'A' ? 'btn-primary' : 'btn-ghost'}
          style={{ fontSize: '13px' }}
          onClick={() => setMethod('A')}
        >
          Via backend (A)
        </button>
        <button
          className={method === 'B' ? 'btn-primary' : 'btn-ghost'}
          style={{ fontSize: '13px' }}
          onClick={() => setMethod('B')}
        >
          Direct to MinIO (B)
        </button>
      </div>

      <div className="upload-row">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.doc,.docx"
          style={{ display: 'none' }}
          onChange={(e) => {
            setSelectedFile(e.target.files?.[0] ?? null)
            setUploadError(null)
          }}
        />
        <button
          className="btn-ghost file-pick-btn"
          onClick={() => fileInputRef.current?.click()}
        >
          {selectedFile ? selectedFile.name : 'Choose file…'}
        </button>
        <button
          className="btn-primary"
          onClick={method === 'A' ? handleUploadA : handleUploadB}
          disabled={!selectedFile || uploading}
        >
          {getUploadLabel()}
        </button>
      </div>

      {uploading && (
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
      )}

      {uploadError && <p className="error-msg" style={{ marginTop: '8px' }}>{uploadError}</p>}
      {listError && <p className="error-msg" style={{ marginTop: '8px' }}>{listError}</p>}

      {loading && (
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginTop: '24px' }}>Loading…</p>
      )}

      {!loading && documents.length === 0 && (
        <div className="empty-state">
          <p>No documents yet.</p>
          <p>Upload one above to get started.</p>
        </div>
      )}

      <ul className="thread-list" style={{ marginTop: '16px' }}>
        {documents.map((doc) => (
          <li key={doc.id} className="thread-item">
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="thread-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {doc.filename}
                </span>
                <StatusBadge status={doc.status} />
              </div>
              <div className="doc-meta">
                {formatSize(doc.size)} · {new Date(doc.created_at).toLocaleDateString()}
                {doc.status === 'failed' && (
                  <span style={{ color: '#dc2626', marginLeft: '8px' }}>Processing failed</span>
                )}
              </div>
            </div>
            {doc.status === 'embedded' && (
              <button
                className="btn-ghost"
                style={{ fontSize: '13px', whiteSpace: 'nowrap' }}
                onClick={() => handleDownload(doc)}
              >
                Download
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default DocumentList
