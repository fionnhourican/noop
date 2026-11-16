import { useEffect, useRef, useState } from "react";
import { LiveWebSocketMessage } from "../types";

export interface LiveStreamState {
  connectionState: "connected" | "connecting" | "disconnected";
  latestBpm: number | null;
  latestTimestamp: string | null;
  batteryLevel: number | null;
  isCharging: boolean | null;
  bpmHistory: { time: string; bpm: number }[];
}

export function useLiveStream(): LiveStreamState {
  const [connectionState, setConnectionState] = useState<"connected" | "connecting" | "disconnected">("connecting");
  const [latestBpm, setLatestBpm] = useState<number | null>(null);
  const [latestTimestamp, setLatestTimestamp] = useState<string | null>(null);
  const [batteryLevel, setBatteryLevel] = useState<number | null>(null);
  const [isCharging, setIsCharging] = useState<boolean | null>(null);
  const [bpmHistory, setBpmHistory] = useState<{ time: string; bpm: number }[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);

  useEffect(() => {
    let unmounted = false;

    function connect() {
      if (unmounted) return;

      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host || "127.0.0.1:8080";
      const wsUrl = `${protocol}//${host}/ws/live`;

      setConnectionState("connecting");
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (unmounted) return;
        setConnectionState("connected");
        // Start keepalive ping
        pingIntervalRef.current = window.setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send("ping");
          }
        }, 15000);
      };

      ws.onmessage = (event) => {
        if (unmounted) return;
        try {
          const msg: LiveWebSocketMessage = JSON.parse(event.data);
          if (msg.type === "pong") return;

          if (msg.type === "heart_rate" && typeof msg.bpm === "number") {
            const timeStr = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : new Date().toLocaleTimeString();
            setLatestBpm(msg.bpm);
            setLatestTimestamp(msg.timestamp || new Date().toISOString());
            setBpmHistory((prev) => [...prev.slice(-30), { time: timeStr, bpm: msg.bpm! }]);
          } else if (msg.type === "battery" && typeof msg.battery_level === "number") {
            setBatteryLevel(msg.battery_level);
            if (typeof msg.is_charging === "boolean") {
              setIsCharging(msg.is_charging);
            }
          }
        } catch {
          // Ignore unparseable frames
        }
      };

      ws.onclose = () => {
        if (unmounted) return;
        setConnectionState("disconnected");
        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        // Exponential reconnect after 3 seconds
        reconnectTimeoutRef.current = window.setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      unmounted = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    connectionState,
    latestBpm,
    latestTimestamp,
    batteryLevel,
    isCharging,
    bpmHistory,
  };
}
