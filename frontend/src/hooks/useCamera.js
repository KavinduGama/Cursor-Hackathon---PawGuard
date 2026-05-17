import { useCallback, useEffect, useRef, useState } from 'react';

export function useCamera({ facingMode = 'environment', enabled = true } = {}) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [state, setState] = useState({
    status: 'idle', // idle | starting | ready | error | denied
    error: null,
  });

  useEffect(() => {
    if (!enabled) {
      const stream = streamRef.current;
      if (stream) stream.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      if (videoRef.current) videoRef.current.srcObject = null;
      setState({ status: 'idle', error: null });
      return undefined;
    }
    let cancelled = false;
    let videoEl = null;
    /** Removes video listeners + sized poll guard. */
    let teardownCameraSetup = null;

    async function start() {
      setState({ status: 'starting', error: null });
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: facingMode },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false, // ElevenLabs widget will request mic separately
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        videoEl = videoRef.current;
        if (!videoEl) {
          streamRef.current.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
          setState({
            status: 'error',
            error: 'Video element not mounted — reload the session.',
          });
          return;
        }

        let sizedPollId = null;

        const tryReady = () => {
          if (cancelled || !videoEl) return;
          const w = videoEl.videoWidth;
          const h = videoEl.videoHeight;
          if (w && h) {
            if (sizedPollId != null) {
              clearInterval(sizedPollId);
              sizedPollId = null;
            }
            setState({ status: 'ready', error: null });
          }
        };

        videoEl.srcObject = stream;
        videoEl.muted = true;
        videoEl.playsInline = true;

        /** Safari/WebKit reports 0×0 until loadedmetadata / playing / resize. */
        const onSized = () => tryReady();

        videoEl.addEventListener('loadedmetadata', onSized);
        videoEl.addEventListener('resize', onSized);
        videoEl.addEventListener('playing', onSized);
        videoEl.addEventListener('loadeddata', onSized);

        /** Some WebKit builds miss sizing events — poll until dims appear. */
        sizedPollId = setInterval(() => tryReady(), 200);

        teardownCameraSetup = () => {
          if (videoEl) {
            videoEl.removeEventListener('loadedmetadata', onSized);
            videoEl.removeEventListener('resize', onSized);
            videoEl.removeEventListener('playing', onSized);
            videoEl.removeEventListener('loadeddata', onSized);
          }
          if (sizedPollId != null) {
            clearInterval(sizedPollId);
            sizedPollId = null;
          }
          teardownCameraSetup = null;
        };

        await videoEl.play().catch(() => {});
        if (cancelled) return;

        tryReady();

        /** Ref may populate one frame later (strict mode / mount edge). */
        requestAnimationFrame(() => {
          if (!cancelled) tryReady();
        });
      } catch (err) {
        const isDenied =
          err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError';
        setState({
          status: isDenied ? 'denied' : 'error',
          error: err?.message || String(err),
        });
      }
    }

    start();
    return () => {
      cancelled = true;
      if (teardownCameraSetup) teardownCameraSetup();
      videoEl = null;
      const stream = streamRef.current;
      if (stream) stream.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, [facingMode, enabled]);

  // Stable across renders so consumers can safely list it in effect deps.
  const captureFrame = useCallback((quality = 0.65) => {
    const video = videoRef.current;
    if (!video) return null;
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (!w || !h) return null;

    /*
     * tryReady gates on dims only; Safari often keeps readyState === HAVE_METADATA
     * longer than Blink while pixels are already drawable — requiring >= CURRENT_DATA
     * made every capture return null forever.
     */
    if (video.readyState < HTMLMediaElement.HAVE_METADATA) return null;

    // Downscale large frames so uploads stay fast on mobile networks.
    const maxDim = 720;
    const scale = Math.min(1, maxDim / Math.max(w, h));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(w * scale);
    canvas.height = Math.round(h * scale);
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', quality);
  }, []);

  return { videoRef, state, captureFrame };
}
