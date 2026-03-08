"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { JobEvent } from "@/types";

interface UseSSEOptions {
  url: string;
  enabled?: boolean;
  onEvent?: (event: JobEvent) => void;
}

export function useSSE({ url, enabled = true, onEvent }: UseSSEOptions) {
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const disconnect = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
      setConnected(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      disconnect();
      return;
    }

    const source = new EventSource(url);
    sourceRef.current = source;

    source.onopen = () => {
      setConnected(true);
      setError(null);
    };

    source.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as JobEvent;
        setEvents((prev) => [...prev, event]);
        onEventRef.current?.(event);
      } catch {
        // ignore malformed events
      }
    };

    source.onerror = () => {
      setConnected(false);
      setError("SSE connection lost");
      source.close();
    };

    return () => {
      source.close();
      sourceRef.current = null;
      setConnected(false);
    };
  }, [url, enabled, disconnect]);

  const reset = useCallback(() => {
    setEvents([]);
    setError(null);
  }, []);

  return { events, connected, error, disconnect, reset };
}
