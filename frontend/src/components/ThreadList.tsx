import { useState, useEffect } from 'react'
import { getThreads, createThread } from '../api/client'
import type { Thread } from '../api/client'

interface Props {
  token: string
}

function ThreadList({ token }: Props) {
  const [threads, setThreads] = useState<Thread[]>([])
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getThreads(token)
      .then(setThreads)
      .catch(() => setError('Failed to load threads'))
      .finally(() => setLoading(false))
  }, [token])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    try {
      const thread = await createThread(token, title)
      setThreads([thread, ...threads])
      setTitle('')
    } catch {
      setError('Failed to create thread')
    }
  }

  return (
    <div>
      <div className="threads-header">
        <h1>Your threads</h1>
        <p>Start a new conversation or continue an existing one</p>
      </div>

      <form className="create-form" onSubmit={handleCreate}>
        <input
          type="text"
          placeholder="New thread title..."
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <button className="btn-primary" type="submit">New thread</button>
      </form>

      {error && <p className="error-msg">{error}</p>}

      {loading && <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Loading...</p>}

      {!loading && threads.length === 0 && (
        <div className="empty-state">
          <p>No threads yet.</p>
          <p>Create one above to get started.</p>
        </div>
      )}

      <ul className="thread-list">
        {threads.map((thread) => (
          <li key={thread.id} className="thread-item">
            <span className="thread-title">{thread.title ?? 'Untitled'}</span>
            <span className="thread-date">
              {new Date(thread.created_at).toLocaleDateString()}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default ThreadList
