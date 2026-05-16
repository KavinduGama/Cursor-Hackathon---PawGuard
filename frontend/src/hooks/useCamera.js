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
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.muted = true;
          videoRef.current.playsInline = true;
          await videoRef.current.play().catch(() => {});
        }
        setState({ status: 'ready', error: null });
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
      const stream = streamRef.current;
      if (stream) stream.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, [facingMode, enabled]);

  // Stable across renders so consumers can safely list it in effect deps.
  const captureFrame = useCallback((quality = 0.65) => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) return null;
    const w = video.videoWidth;
    const h = video.videoHeight;
    if (!w || !h) return null;

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
