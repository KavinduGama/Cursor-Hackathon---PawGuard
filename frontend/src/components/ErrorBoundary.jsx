import React from 'react';

/**
 * Catches unhandled JS errors during the demo and shows a friendly
 * recovery screen instead of a white page.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('[PawGuard] Unhandled error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100dvh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '2rem',
            background: 'var(--bg, #f8fbfb)',
            color: 'var(--text, #1a2a2a)',
            textAlign: 'center',
            fontFamily: 'var(--font, system-ui)',
          }}
        >
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🐾</div>
          <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.25rem' }}>
            Something went wrong
          </h2>
          <p style={{ opacity: 0.7, marginBottom: '1.5rem', maxWidth: '20rem' }}>
            PawGuard hit an unexpected error. Tap below to restart.
          </p>
          <button
            onClick={() => window.location.replace('/')}
            style={{
              padding: '0.75rem 2rem',
              borderRadius: '12px',
              border: 'none',
              background: 'var(--green, #149191)',
              color: '#fff',
              fontWeight: 700,
              fontSize: '1rem',
              cursor: 'pointer',
            }}
          >
            Restart PawGuard
          </button>
          {this.state.error && (
            <pre
              style={{
                marginTop: '1.5rem',
                fontSize: '0.7rem',
                opacity: 0.5,
                maxWidth: '90vw',
                overflow: 'auto',
                textAlign: 'left',
              }}
            >
              {String(this.state.error)}
            </pre>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
