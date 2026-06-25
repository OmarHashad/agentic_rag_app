import { useState, useEffect, useRef } from 'react'
import {
  uploadViaBackend,
  uploadDirect,
  requestPresignedUrl,
  confirmUpload,
  getDocuments,
  getDownloadUrl,
} from '../api/client'
import type { Document } from '../api/client'

interface Props {
  token: string
}

type UploadMethod = 'A' | 'B'

function formatSize(bytes: number | null): string {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
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

  useEffect(() => {
    getDocuments(token)
      .then(setDocuments)
      .catch(() => setListError('Failed to load documents'))
      .finally(() => setLoading(false))
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
      // Step 1: get presigned URL + pending row from backend
      const { document_id, upload_url } = await requestPresignedUrl(
        token,
        selectedFile.name,
        selectedFile.type
      )

      // Step 2: PUT file directly to MinIO — backend never sees the bytes
      await uploadDirect(upload_url, selectedFile, setProgress)

      // Step 3: tell backend to verify and flip status to ready
      const doc = await confirmUpload(token, document_id)
      setDocuments((prev) => [doc, ...prev])
      clearFile()
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
            <div>
              <div className="thread-title">{doc.filename}</div>
              <div className="doc-meta">
                {formatSize(doc.size)} · {new Date(doc.created_at).toLocaleDateString()}
              </div>
            </div>
            <button
              className="btn-ghost"
              style={{ fontSize: '13px', whiteSpace: 'nowrap' }}
              onClick={() => handleDownload(doc)}
            >
              Download
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default DocumentList
