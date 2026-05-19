function construirUrlAlertas(token) {
  return `ws://localhost:8000/ws/alertas?token=${encodeURIComponent(token)}`
}

export function conectarAlertasWebSocket({ token, onMessage, onOpen, onClose, onError }) {
  const ws = new WebSocket(construirUrlAlertas(token))

  ws.onopen    = () => onOpen?.()
  ws.onclose   = (event) => onClose?.(event)
  ws.onerror   = (event) => onError?.(event)
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage?.(data)
    } catch {
      // Ignorar mensajes no JSON
    }
  }

  return ws 
}