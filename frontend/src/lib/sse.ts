/** SSE stream handler with reconnection and event parsing. */

import type { SSEEvent } from "@/types/schema";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SSEOptions {
  onEvent: (event: SSEEvent) => void;
  onError?: (error: Error) => void;
  onClose?: () => void;
  maxRetries?: number;
}

/**
 * Connect to an SSE stream for a job and process events.
 * Implements exponential backoff on disconnect.
 */
export function connectSSE(jobId: string, options: SSEOptions): () => void {
  const { onEvent, onError, onClose, maxRetries = 5 } = options;
  let retryCount = 0;
  let controller: AbortController | null = null;
  let stopped = false;

  async function connect() {
    if (stopped) return;

    controller = new AbortController();
    const url = `${API_BASE}/api/status/${jobId}/stream`;

    try {
      const response = await fetch(url, {
        signal: controller.signal,
        headers: { Accept: "text/event-stream" },
      });

      if (!response.ok) {
        throw new Error(`SSE connection failed: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No readable stream");
      }

      const decoder = new TextDecoder();
      let buffer = "";
      retryCount = 0; // Reset on successful connect

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        let currentData = "";

        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            currentData = line.slice(5).trim();
          } else if (line === "" && currentData) {
            // End of event
            try {
              const parsedData = JSON.parse(currentData);
              const sseEvent: SSEEvent = {
                event: currentEvent as SSEEvent["event"],
                data: parsedData,
              };
              onEvent(sseEvent);

              // Terminal events
              if (currentEvent === "done" || currentEvent === "error") {
                stopped = true;
                onClose?.();
                return;
              }
            } catch (e) {
              // Skip unparseable events
            }
            currentEvent = "";
            currentData = "";
          }
        }
      }
    } catch (error) {
      if (stopped) return;

      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }

      if (retryCount < maxRetries) {
        retryCount++;
        const delay = Math.min(1000 * Math.pow(2, retryCount), 30000);
        setTimeout(connect, delay);
      } else {
        onError?.(error instanceof Error ? error : new Error(String(error)));
      }
    }
  }

  connect();

  // Return disconnect function
  return () => {
    stopped = true;
    controller?.abort();
    onClose?.();
  };
}
