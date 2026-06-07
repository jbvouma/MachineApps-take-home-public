import { useReset } from '../hooks/useReset'

interface ErrorBannerProps {
  state: string
  errorMessage?: string
  // Extra transient errors (e.g. failed RPC / network) surfaced from elsewhere.
  extraError?: string | null
}

const ErrorBanner = ({ state, errorMessage, extraError }: ErrorBannerProps) => {
  const reset = useReset()
  const isFault = state === 'fault' || Boolean(errorMessage)

  if (!isFault && !extraError) return null

  return (
    <div className="error-banner" role="alert">
      <div className="error-banner__body">
        <strong className="error-banner__title">
          {isFault ? 'Robot fault' : 'Connection error'}
        </strong>
        <span className="error-banner__message">
          {errorMessage || extraError || 'The robot is in a fault state.'}
        </span>
      </div>
      {isFault && (
        <button
          type="button"
          className="btn btn--danger"
          onClick={() => reset.mutate()}
          disabled={reset.isPending}
        >
          {reset.isPending ? 'Resetting...' : 'Reset fault'}
        </button>
      )}
    </div>
  )
}

export default ErrorBanner
