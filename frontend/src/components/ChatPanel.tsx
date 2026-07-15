import { useState, useEffect, useRef } from 'react'
import { getActiveTurn, getMessages, startChatTurn, streamTurn } from '../api/client'
import type { ChatMessage, ChatStreamEvent } from '../api/client'

interface Props {
  token: string
  threadId: number
  threadTitle: string | null
}

interface LiveMessage extends ChatMessage {
  generating?: boolean
  toolStatus?: string | null
  streamError?: string | null
}

function ChatPanel({ token, threadId, threadTitle }: Props) {
  const [messages, setMessages] = useState<LiveMessage[]>([])
  const [input, setInput] = useState('')
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const isGenerating = messages.some((m) => m.generating)

  function applyStreamEvent(event: ChatStreamEvent) {
    setMessages((prev) => {
      const next = [...prev]
      const last = next[next.length - 1]
      if (!last || last.role !== 'assistant') return prev

      switch (event.event_type) {
        case 'text_delta':
          next[next.length - 1] = {
            ...last,
            content: last.content + event.data.delta,
            toolStatus: null,
          }
          break
        case 'tool_call_started':
          next[next.length - 1] = { ...last, toolStatus: 'Searching documents…' }
          break
        case 'tool_call_finished':
          next[next.length - 1] = { ...last, toolStatus: null }
          break
        case 'turn_complete':
          next[next.length - 1] = {
            ...last,
            content: event.data.answer,
            citations: event.data.citations,
            generating: false,
            toolStatus: null,
          }
          break
        case 'turn_failed':
          next[next.length - 1] = {
            ...last,
            generating: false,
            toolStatus: null,
            streamError: event.data.error,
          }
          break
      }
      return next
    })
  }

  async function attachToTurn(turnId: string, signal: AbortSignal) {
    setMessages((prev) => [
      ...prev,
      { role: 'assistant', content: '', citations: [], generating: true },
    ])
    try {
      await streamTurn(token, threadId, turnId, applyStreamEvent, { signal })
    } catch {
      if (!signal.aborted) {
        setMessages((prev) => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last?.generating) {
            next[next.length - 1] = {
              ...last,
              generating: false,
              streamError: 'Lost connection to the response stream.',
            }
          }
          return next
        })
      }
    }
  }

  useEffect(() => {
    const controller = new AbortController()

    async function init() {
      setLoadingHistory(true)
      setError(null)
      try {
        const history = await getMessages(token, threadId)
        setMessages(history)

        const active = await getActiveTurn(token, threadId)
        if (active.turn_id && !controller.signal.aborted) {
          await attachToTurn(active.turn_id, controller.signal)
        }
      } catch {
        if (!controller.signal.aborted) setError('Failed to load conversation history')
      } finally {
        if (!controller.signal.aborted) setLoadingHistory(false)
      }
    }

    init()
    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, threadId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend(e: React.FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || isGenerating) return

    setError(null)
    setMessages((prev) => [...prev, { role: 'user', content: text, citations: [] }])
    setInput('')

    const controller = new AbortController()
    try {
      const { turn_id } = await startChatTurn(token, threadId, text)
      await attachToTurn(turn_id, controller.signal)
    } catch {
      setError('Failed to start a response. Please try again.')
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h1>{threadTitle ?? 'Untitled thread'}</h1>
      </div>

      <div className="chat-messages">
        {loadingHistory && <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Loading...</p>}

        {!loadingHistory && messages.length === 0 && (
          <div className="empty-state">
            <p>No messages yet.</p>
            <p>Ask something about your documents to get started.</p>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`chat-message chat-message-${m.role}`}>
            <div className="chat-bubble">
              {m.content}
              {m.generating && !m.content && !m.toolStatus && <span>…</span>}
            </div>
            {m.toolStatus && (
              <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>{m.toolStatus}</p>
            )}
            {m.streamError && <p className="error-msg">{m.streamError}</p>}
            {m.role === 'assistant' && !m.generating && !m.streamError && (
              m.citations.length > 0 ? (
                <div className="chat-citations">
                  <span className="chat-citations-label">Sources:</span>
                  <ul>
                    {m.citations.map((c, j) => (
                      <li key={j}>
                        {c.filename ?? 'Unknown document'}
                        {c.chunk_index !== null ? ` (chunk ${c.chunk_index})` : ''}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="chat-citations chat-citations-none">No sources used for this answer.</div>
              )
            )}
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      {error && <p className="error-msg">{error}</p>}

      <form className="chat-input-form" onSubmit={handleSend}>
        <input
          type="text"
          placeholder="Ask a question..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isGenerating}
        />
        <button className="btn-primary" type="submit" disabled={isGenerating || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}

export default ChatPanel
