import { useState } from 'react'
import { searchDocuments } from '../api/client'
import type { SearchResult } from '../api/client'

interface Props {
  token: string
}

function SearchPanel({ token }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await searchDocuments(token, query.trim())
      setResults(data)
    } catch {
      setError('Search failed — is the worker running and have you uploaded documents?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ marginTop: '40px' }}>
      <div className="threads-header">
        <h1>Semantic Search</h1>
        <p>Search across your embedded documents by meaning</p>
      </div>

      <form onSubmit={handleSearch} style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question or describe what you're looking for…"
          style={{
            flex: 1,
            padding: '8px 12px',
            borderRadius: '6px',
            border: '1px solid var(--border)',
            background: 'var(--input-bg, var(--bg-surface))',
            color: 'var(--text)',
            fontSize: '14px',
          }}
        />
        <button className="btn-primary" type="submit" disabled={loading || !query.trim()}>
          {loading ? 'Searching…' : 'Search'}
        </button>
      </form>

      {error && <p className="error-msg" style={{ marginTop: '12px' }}>{error}</p>}

      {results !== null && results.length === 0 && (
        <div className="empty-state" style={{ marginTop: '24px' }}>
          <p>No results found.</p>
          <p>Try different keywords or upload and embed more documents first.</p>
        </div>
      )}

      {results && results.length > 0 && (
        <ul className="thread-list" style={{ marginTop: '16px' }}>
          {results.map((r, i) => (
            <li key={i} className="thread-item" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>
                  {r.filename} · chunk {r.chunk_index + 1}
                </span>
                <span style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  color: r.score > 0.7 ? '#16a34a' : r.score > 0.4 ? '#d97706' : 'var(--text-muted)',
                  background: 'var(--bg-surface)',
                  padding: '2px 7px',
                  borderRadius: '4px',
                  border: '1px solid var(--border)',
                }}>
                  {Math.round(r.score * 100)}% match
                </span>
              </div>
              <p style={{ margin: 0, fontSize: '14px', lineHeight: '1.5', color: 'var(--text)' }}>
                {r.text}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default SearchPanel
