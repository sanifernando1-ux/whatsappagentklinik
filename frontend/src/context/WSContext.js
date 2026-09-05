import React, { createContext, useContext, useEffect, useRef } from "react";

const WSCtx = createContext(null);

export function WSProvider({ children }) {
  const subs = useRef(new Set());

  useEffect(() => {
    const token = localStorage.getItem("kf_token");
    if (!token) return;
    const base = process.env.REACT_APP_BACKEND_URL.replace(/^http/, "ws");
    let ws, closed = false, retry;
    const connect = () => {
      ws = new WebSocket(`${base}/api/ws?token=${token}`);
      ws.onmessage = (ev) => {
        try {
          const d = JSON.parse(ev.data);
          subs.current.forEach((fn) => { try { fn(d); } catch (e) { /* noop */ } });
        } catch (e) { /* noop */ }
      };
      ws.onclose = () => { if (!closed) retry = setTimeout(connect, 4000); };
      ws.onerror = () => { try { ws.close(); } catch (e) { /* noop */ } };
    };
    connect();
    return () => { closed = true; clearTimeout(retry); try { ws && ws.close(); } catch (e) { /* noop */ } };
  }, []);

  const subscribe = (fn) => { subs.current.add(fn); return () => subs.current.delete(fn); };

  return <WSCtx.Provider value={{ subscribe }}>{children}</WSCtx.Provider>;
}

export const useWS = () => useContext(WSCtx);
