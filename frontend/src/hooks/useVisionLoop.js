import { useEffect, useRef, useState } from 'react';
import { api } from '../lib/api.js';
import { safeParseAnalysis } from '../lib/geo.js';

/**
 * Drives the background vision loop:
 *   1. every captureInterval ms, snap a frame and POST to /vision/analyze
 *   2. every pollInterval ms, GET /vision/observations/{id} for the cached analysis
 *
 * The loop is fire-and-forget so a slow Gemini call never blocks the UI.
 *
 * NOTE: `captureFrame` is stashed in a ref so a fresh function identity from
 * the parent doesn't tear down the intervals on every render. Only
 * `sessionId` and `active` should restart the loop.
 */
export function useVisionLoop({
  sessionId,
  captureFrame,
  active = true,
  captureInterval = 2500,
  pollInterval = 1500,
}) {
  const [observation, setObservation] = useState(null);
  const [frameCount, setFrameCount] = useState(0);
  const inflightRef = useRef(false);
  const captureRef = useRef(captureFrame);
  const captureIntervalRef = useRef(captureInterval);
  const pollIntervalRef = useRef(pollInterval);

  useEffect(() => {
    captureRef.current = captureFrame;
  }, [captureFrame]);

  useEffect(() => {
    captureIntervalRef.current = captureInterval;
    pollIntervalRef.current = pollInterval;
  }, [captureInterval, pollInterval]);

  useEffect(() => {
    if (!sessionId || !active) return undefined;

    const captureId = setInterval(async () => {
      if (inflightRef.current) return;
      const grab = captureRef.current;
      const frame = grab ? grab() : null;
      if (!frame) return;
      inflightRef.current = true;
      try {
        await api.analyzeFrame(sessionId, frame);
      } catch (err) {
        console.warn('analyzeFrame failed:', err);
      } finally {
        inflightRef.current = false;
      }
    }, captureIntervalRef.current);

    const pollId = setInterval(async () => {
      try {
        const data = await api.getObservations(sessionId);
        const parsed = safeParseAnalysis(data.analysis);
        setObservation({
          raw: data.analysis,
          parsed,
          severity: data.severity || parsed?.severity || 'UNKNOWN',
          updatedAt: data.updated_at,
        });
        setFrameCount(data.frame_count || 0);
      } catch (err) {
        // Session not yet started — silent retry.
      }
    }, pollIntervalRef.current);

    return () => {
      clearInterval(captureId);
      clearInterval(pollId);
    };
  }, [sessionId, active]);

  return { observation, frameCount };
}
