<<<<<<< HEAD
import { startTransition, useEffect, useState } from 'react'
import './App.css'
import SimulatorPage from './components/SimulatorPage'
import MainPage from './pages/MainPage'

type ShellView = 'simulator' | 'planner'

function readViewFromHash(): ShellView {
  return window.location.hash === '#planner' ? 'planner' : 'simulator'
}

function writeViewHash(view: ShellView) {
  const nextHash = view === 'planner' ? '#planner' : '#simulator'
  if (window.location.hash === nextHash) {
    return
  }
  window.history.replaceState(
    null,
    '',
    `${window.location.pathname}${window.location.search}${nextHash}`,
  )
}

function App() {
  const [view, setView] = useState<ShellView>(() => readViewFromHash())

  useEffect(() => {
    const onHashChange = () => setView(readViewFromHash())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const handleViewChange = (nextView: ShellView) => {
    writeViewHash(nextView)
    startTransition(() => {
      setView(nextView)
    })
  }

  return (
    <div className="app-shell">
      <header className="shell-nav">
        <div className="shell-brand">
          <p className="eyebrow">A2A MCP Frontend</p>
          <h1>Simulator-first corridor shell</h1>
        </div>
        <div className="shell-nav-actions">
          <button
            className={`shell-nav-button ${view === 'simulator' ? 'active' : ''}`}
            type="button"
            onClick={() => handleViewChange('simulator')}
          >
            Simulator
          </button>
          <button
            className={`shell-nav-button ${view === 'planner' ? 'active' : ''}`}
            type="button"
            onClick={() => handleViewChange('planner')}
          >
            Planner
          </button>
        </div>
      </header>

      <main className="surface-shell">
        {view === 'simulator' ? <SimulatorPage /> : <MainPage />}
      </main>
    </div>
=======
import './App.css'
import MainPage from './pages/MainPage'

function App() {
  return (
    <MainPage />
>>>>>>> origin/main
  )
}

export default App
