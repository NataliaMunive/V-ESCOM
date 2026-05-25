// FRONTEND/src/pages/CamarasStream.jsx
import { useState, useEffect, useRef } from 'react'
import { getCamaras } from '../services/api'
import axios from 'axios'
import './CamarasStream.css'

const api = axios.create({ baseURL: '/api' })
api.interceptors.request.use((c) => {
  const t = localStorage.getItem('vescom_token')
  if (t) c.headers.Authorization = `Bearer ${t}`
  return c
})

const detenerStream  = (id) => api.delete(`/rtsp/detener/${id}`)
const estadoStreams   = ()   => api.get('/rtsp/estado')

const tipoColor = (tipo) =>
  tipo === 'Autorizado' ? 'var(--verde-ok)' : tipo === 'No Autorizado' ? 'var(--rojo-alerta)' : 'var(--texto-muted)'

const hace = (ts) => {
  if (!ts) return '—'
  const diff = Math.floor(Date.now() / 1000 - ts)
  if (diff < 60) return `hace ${diff}s`
  return `hace ${Math.floor(diff / 60)}m`
}

// ── Visor MJPEG continuo ────────────────────────────────────────────────────
function SnapshotViewer({ idCamara, activo, ultimoFrameTs }) {
  const token = localStorage.getItem('vescom_token')
  const [nonce, setNonce] = useState(0)
  const staleRef = useRef(null)

  useEffect(() => {
    if (!activo) {
      setNonce(0)
      if (staleRef.current) {
        clearTimeout(staleRef.current)
        staleRef.current = null
      }
      return undefined
    }

    if (staleRef.current) {
      clearTimeout(staleRef.current)
      staleRef.current = null
    }

    staleRef.current = setTimeout(() => {
      setNonce((value) => value + 1)
    }, 12000)

    return () => {
      if (staleRef.current) {
        clearTimeout(staleRef.current)
        staleRef.current = null
      }
    }
  }, [activo, idCamara, ultimoFrameTs])

  const baseUrl = `${window.location.protocol}//${window.location.hostname}:8000`
  const mjpegUrl = `${baseUrl}/rtsp/mjpeg/${idCamara}?token=${encodeURIComponent(token || '')}&v=${nonce}`

  if (!activo) return (
    <div className="snapshot-placeholder">
      <span>◈</span>
      <p>Stream inactivo</p>
    </div>
  )

  return (
    <div className="snapshot-wrap">
      <img
        key={`${idCamara}-${nonce}`}
        src={mjpegUrl}
        alt="Vista de cámara"
        className="snapshot-img"
        onError={() => {}}
      />
      <div className="snapshot-badge">EN VIVO</div>
    </div>
  )
}

// ── Componente principal ────────────────────────────────────────────────────
export default function CamarasStream() {
  const [camaras, setCamaras]         = useState([])
  const [workers, setWorkers]         = useState([])
  const [cargando, setCargando]       = useState(true)
  const [accionando, setAccionando]   = useState(null)
  const pollRef                       = useRef(null)

  useEffect(() => {
    cargarTodo()
    pollRef.current = setInterval(refrescarWorkers, 4000)
    return () => clearInterval(pollRef.current)
  }, [])

  const cargarTodo = async () => {
    setCargando(true)
    try {
      const [camRes, wRes] = await Promise.all([getCamaras(), estadoStreams()])
      setCamaras(camRes.data)
      setWorkers(wRes.data)
    } catch {}
    finally { setCargando(false) }
  }

  const refrescarWorkers = async () => {
    try { const r = await estadoStreams(); setWorkers(r.data) } catch {}
  }

  const workerDe = (id) => workers.find(w => w.id_camara === id)
  const camarasOrdenadas = [...camaras].sort((a, b) => {
    const activoA = workerDe(a.id_camara)?.activo === true ? 1 : 0
    const activoB = workerDe(b.id_camara)?.activo === true ? 1 : 0
    if (activoA !== activoB) return activoB - activoA

    const habilitadaA = a.activa ? 1 : 0
    const habilitadaB = b.activa ? 1 : 0
    if (habilitadaA !== habilitadaB) return habilitadaB - habilitadaA

    return String(a.nombre || '').localeCompare(String(b.nombre || ''))
  })

  const handleDetener = async (id) => {
    setAccionando(id)
    try { await detenerStream(id); setTimeout(refrescarWorkers, 600) }
    catch {}
    finally { setAccionando(null) }
  }

  const activos = workers.filter(w => w.activo).length

  return (
    <div className="stream-page">
      <div className="stream-header">
        <div>
          <h1 className="stream-title">Streams en Vivo</h1>
          <p className="stream-sub">Captura continua RTSP · MERCUSYS MC210 · Puerto 554</p>
        </div>
        <span className={`stream-badge ${activos > 0 ? 'badge-on' : 'badge-off'}`}>
          <span className="badge-pulse" />
          {activos} activo{activos !== 1 ? 's' : ''} / {camaras.length} cámaras
        </span>
      </div>

      <div className="rtsp-info-card">
        <div className="rtsp-info-icon">
          <img src="/icons/red.svg" alt="" />
        </div>
        <div>
          <p className="rtsp-info-titulo">MERCUSYS MC210 — Formato RTSP</p>
          <code className="rtsp-info-url">
            rtsp://adminadmin:12345678@192.168.1.137:554/stream2
          </code>
          <p className="rtsp-info-hint">
            <strong>stream2</strong> = 720p recomendado para análisis ·
            <strong> stream1</strong> = 2K · Puerto ONVIF: 2020
          </p>
        </div>
      </div>

      {cargando ? (
        <div className="stream-loading">Cargando cámaras...</div>
      ) : camaras.length === 0 ? (
        <div className="stream-empty">No hay cámaras registradas.</div>
      ) : (
        <div className="stream-grid">
          {camarasOrdenadas.map(cam => {
            const w    = workerDe(cam.id_camara)
            const vivo = w?.activo === true
            const res  = w?.ultimo_resultado
            const tipo = res?.tipo_acceso
            return (
              <div key={cam.id_camara}
                className={`stream-card ${vivo ? 'stream-card-on' : ''} ${!cam.activa ? 'stream-card-disabled' : ''}`}>

                {/* Vista de cámara */}
                <SnapshotViewer
                  idCamara={cam.id_camara}
                  activo={vivo}
                  ultimoFrameTs={w?.ultimo_frame_ts}
                />

                {/* Info */}
                <div className="sc-body">
                  <div className="sc-head">
                    <div className="sc-cam-icon">◈</div>
                    <div className="sc-info">
                      <span className="sc-nombre">{cam.nombre}</span>
                      <span className="sc-meta">
                        #{cam.id_camara}
                        {cam.id_cubiculo && ` · Cubículo ${cam.id_cubiculo}`}
                        {cam.direccion_ip && ` · ${cam.direccion_ip}`}
                      </span>
                    </div>
                    <div className={`sc-status-dot ${vivo ? 'dot-on' : 'dot-off'}`} />
                  </div>

                  {/* Último resultado */}
                  <div className={`sc-resultado ${tipo === 'Autorizado' ? 'res-ok' : tipo === 'No Autorizado' ? 'res-alerta' : 'res-vacio'}`}>
                    {res ? (
                      <>
                        <span className="res-icon">{tipo === 'Autorizado' ? '✓' : '⚠'}</span>
                        <div className="res-datos">
                          <span className="res-tipo" style={{ color: tipoColor(tipo) }}>{tipo}</span>
                          <span className="res-nombre">
                            {res.nombre ? `${res.nombre} ${res.apellidos || ''}` : 'Desconocido'}
                          </span>
                          <span className="res-sim">
                            {res.similitud != null ? `${(res.similitud * 100).toFixed(1)}%` : '—'}
                            &nbsp;·&nbsp;{hace(w?.ultimo_frame_ts)}
                          </span>
                        </div>
                      </>
                    ) : (
                      <span className="res-espera">
                        {vivo ? 'Esperando detección...' : 'Stream inactivo'}
                      </span>
                    )}
                  </div>

                  {/* Botones */}
                  <div className="sc-acciones">
                    {vivo ? (
                      <button className="sc-btn sc-btn-stop"
                        onClick={() => handleDetener(cam.id_camara)}
                        disabled={accionando === cam.id_camara}>
                        {accionando === cam.id_camara ? '...' : '⏹ Detener'}
                      </button>
                    ) : (
                      <div className="stream-note">
                        Inicia la cámara desde <strong>Cámaras</strong> para verla aquí.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}