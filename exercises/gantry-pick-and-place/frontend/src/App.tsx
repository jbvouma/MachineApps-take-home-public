import { useStatus } from './hooks/useStatus'
import Controls from './components/Controls'
import Dashboard from './components/Dashboard'
import ErrorBanner from './components/ErrorBanner'
import PositionForm from './components/PositionForm'
import StateBadge from './components/StateBadge'
import WorkspaceView from './components/WorkspaceView'
import './App.css'

const App = () => {
  const { data: status, isLoading, isError, error } = useStatus()

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <h1 className="app__title">Gantry Pick &amp; Place</h1>
          <p className="app__subtitle">Live robot dashboard</p>
        </div>
        {status && <StateBadge state={status.state} moving={status.moving} />}
      </header>

      <ErrorBanner
        state={status?.state ?? ''}
        errorMessage={status?.errorMessage}
        resumable={status?.resumable}
        extraError={isError ? (error as Error).message : null}
      />

      {isLoading && !status && (
        <p className="app__loading">Connecting to robot...</p>
      )}

      {status && (
        <main className="app__grid">
          <div className="app__col">
            <Dashboard status={status} />
            <section className="card operations">
              <h2 className="card__title">Operations</h2>
              <Controls
                state={status.state}
                moving={status.moving}
                resumable={status.resumable}
                home={status.home}
              />
              <PositionForm
                cubeStart={status.cubeStart}
                destination={status.destination}
                disabled={status.state !== 'ready' && status.state !== 'fault'}
              />
            </section>
          </div>
          <div className="app__col">
            <WorkspaceView status={status} />
          </div>
        </main>
      )}
    </div>
  )
}

export default App
