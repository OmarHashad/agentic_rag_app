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
      <h1>Your threads</h1>

      <form onSubmit={handleCreate}>
        <input
          type="text"
          placeholder="Thread title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <button type="submit">New thread</button>
      </form>

      {loading && <p>Loading...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {!loading && threads.length === 0 && (
        <p>No threads yet. Create one above.</p>
      )}

      <ul>
        {threads.map((thread) => (
          <li key={thread.id}>
            {thread.title ?? 'Untitled'} —{' '}
            {new Date(thread.created_at).toLocaleDateString()}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default ThreadList
