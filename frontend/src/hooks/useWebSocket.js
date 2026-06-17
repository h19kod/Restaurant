import { useEffect, useRef, useCallback } from 'react'

export function useWebSocket(path, onMessage) {
  const wsRef     = useRef(null)
  const timerRef  = useRef(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const host     = window.location.host
    const url      = `${protocol}://${host}${path}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)) } catch {}
    }

    ws.onclose = () => {
      if (mountedRef.current) {
        timerRef.current = setTimeout(connect, 3000)
      }
    }

    ws.onerror = () => ws.close()
  }, [path, onMessage])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, [connect])
}
