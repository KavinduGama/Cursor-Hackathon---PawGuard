import { forwardRef } from 'react';

/**
 * Camera card — shows the live video stream inside a rounded card.
 *
 * Renders one of three states:
 *   - "open"   : video element + close button + frame count overlay
 *   - "closed" : friendly placeholder with a "Turn on camera" button
 *   - "loading"/"error" : status overlay while the stream initialises
 *
 * The actual `getUserMedia` lifecycle lives in `useCamera` — the parent
 * passes `enabled` to that hook to start/stop the stream.
 */
const Camera = forwardRef(function Camera(
  { videoRef, status, isOpen, onToggle, frameCount = 0 },
  _ref
) {
  if (!isOpen) {
    return (
      <div className="camera-closed">
        <div className="icon" aria-hidden>
          📷
        </div>
        <div>
          <div style={{ fontWeight: 700, color: 'var(--text)' }}>
            Camera is off
          </div>
          <div style={{ fontSize: '0.82rem' }}>
            Vision triage is paused. PawGuard will keep listening.
          </div>
        </div>
        <button className="btn btn-primary" type="button" onClick={onToggle}>
          📷 Turn on camera
        </button>
      </div>
    );
  }

  return (
    <div className="camera-card">
      <video
        ref={videoRef}
        className="camera-video"
        autoPlay
        playsInline
        muted
      />

      <div className="camera-overlay-top">
        <span className="camera-frame-count">
          {frameCount} frame{frameCount === 1 ? '' : 's'}
        </span>
        <button
          className="camera-close"
          type="button"
          onClick={onToggle}
          aria-label="Close camera"
        >
          ✕
        </button>
      </div>

      {status === 'starting' && (
        <div className="camera-loading">Starting camera…</div>
      )}

      {status === 'denied' && (
        <div className="camera-error">
          Camera access blocked. Allow it in your browser settings and reload.
        </div>
      )}

      {status === 'error' && (
        <div className="camera-error">
          Couldn&apos;t start the camera. Try again or use another device.
        </div>
      )}
    </div>
  );
});

export default Camera;
