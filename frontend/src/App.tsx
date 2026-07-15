import { useState, useEffect } from 'react'
import Login from './components/Login'
import ThreadList from './components/ThreadList'
import DocumentList from './components/DocumentList'
import SearchPanel from './components/SearchPanel'
import ChatPanel from './components/ChatPanel'
import type { Thread } from './api/client'
import './App.css'

function App() {
  const [token, setToken] = useState<string | null>(null)
  const [selectedThread, setSelectedThread] = useState<Thread | null>(null)
  const [dark, setDark] = useState(
    () => window.matchMedia('(prefers-color-scheme: dark)').matches
  )

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
  }, [dark])

  if (!token) {
    return <Login onLogin={setToken} dark={dark} onToggleTheme={() => setDark(!dark)} />
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h2>Agentic RAG</h2>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn-ghost" onClick={() => setDark(!dark)}>
            {dark ? 'Light mode' : 'Dark mode'}
          </button>
          <button className="btn-ghost" onClick={() => setToken(null)}>Log out</button>
        </div>
      </header>
      <main className="app-body">
        <ThreadList
          token={token}
          selectedThreadId={selectedThread?.id ?? null}
          onSelectThread={setSelectedThread}
        />
        {selectedThread ? (
          <ChatPanel
            key={selectedThread.id}
            token={token}
            threadId={selectedThread.id}
            threadTitle={selectedThread.title}
          />
        ) : (
          <div className="empty-state">
            <p>Select or create a thread to start chatting.</p>
          </div>
        )}
        <DocumentList token={token} />
        <SearchPanel token={token} />
      </main>
    </div>
  )
}

export default App
