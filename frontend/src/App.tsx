import { useState, useEffect } from 'react'
import Login from './components/Login'
import ThreadList from './components/ThreadList'
import DocumentList from './components/DocumentList'
import './App.css'

function App() {
  const [token, setToken] = useState<string | null>(null)
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
        <ThreadList token={token} />
        <DocumentList token={token} />
      </main>
    </div>
  )
}

export default App
