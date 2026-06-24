import { useState } from 'react'
import Login from './components/Login'
import ThreadList from './components/ThreadList'

function App() {
  const [token, setToken] = useState<string | null>(null)

  if (!token) {
    return <Login onLogin={setToken} />
  }

  return (
    <div>
      <button onClick={() => setToken(null)}>Log out</button>
      <ThreadList token={token} />
    </div>
  )
}

export default App
