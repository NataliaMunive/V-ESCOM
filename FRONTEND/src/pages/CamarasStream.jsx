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

const iniciarStream  = (p)  => api.post('/rtsp/iniciar', p)
const detenerStream  = (id) => api.delete(`/rtsp/detener/${id}`)
const estadoStreams   = ()   => api.get('/rtsp/estado')
const getSnapshot    = (id) =>
  `${window.location.protocol}//${window.location.hostname}:8000/rtsp/snapshot/${id}?t=${Date.now()}&token=${localStorage.getItem('vescom_token')}`

const tipoColor = (tipo) =>
  tipo === 'Autorizado' ? 'var(--verde-ok)' : tipo === 'No Autorizado' ? 'var(--rojo-alerta)' : 'var(--texto-muted)'

const hace = (ts) => {
  if (!ts) return '—'
  const diff = Math.floor(Date.now() / 1000 - ts)
  if (diff < 60) return `hace ${diff}s`
  return `hace ${Math.floor(diff / 60)}m`
}

// ── Visor de snapshot con auto-refresh ──────────────────────────────────────
function SnapshotViewer({ idCamara, activo }) {
  const token = localStorage.getItem('vescom_token')
  const mjpegUrl = `http://localhost:8000/rtsp/mjpeg/${idCamara}?token=${token}`

  if (!activo) return (
    <div className="snapshot-placeholder">
      <span>◈</span>
      <p>Stream inactivo</p>
    </div>
  )

  return (
    <div className="snapshot-wrap">
      <img
        key={mjpegUrl}
        src={mjpegUrl}
        alt="Vista de cámara"
        className="snapshot-img"
        onError={(e) => {
          e.target.style.display = 'none'
        }}
      />
      <div className="snapshot-badge">EN VIVO</div>
    </div>
  )
}

// ── Componente principal ────────────────────────────────────────────────────
export default function CamarasStream() {
  const [camaras, setCamaras]         = useState([])
  const [workers, setWorkers]         = useState([])
  const [modal, setModal]             = useState(null)
  const [form, setForm]               = useState({ rtsp_user: 'adminadmin', rtsp_pass: '', stream: 'stream2' })
  const [cargando, setCargando]       = useState(true)
  const [accionando, setAccionando]   = useState(null)
  const [error, setError]             = useState('')
  const [mostrarPass, setMostrarPass] = useState(false)
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

  const abrirModal = (cam) => {
    setModal(cam.id_camara)
    setForm({ rtsp_user: 'adminadmin', rtsp_pass: '', stream: 'stream2' })
    setError('')
  }

  const handleIniciar = async () => {
    setAccionando(modal); setError('')
    try {
      await iniciarStream({ id_camara: modal, ...form })
      setModal(null)
      setTimeout(refrescarWorkers, 1200)
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al iniciar stream')
    } finally { setAccionando(null) }
  }

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
        <div className="rtsp-info-icon">📡</div>
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
          {camaras.map(cam => {
            const w    = workerDe(cam.id_camara)
            const vivo = w?.activo === true
            const res  = w?.ultimo_resultado
            const tipo = res?.tipo_acceso
            return (
              <div key={cam.id_camara}
                className={`stream-card ${vivo ? 'stream-card-on' : ''} ${!cam.activa ? 'stream-card-disabled' : ''}`}>

                {/* Vista de cámara */}
                <SnapshotViewer idCamara={cam.id_camara} activo={vivo} />

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
                      <button className="sc-btn sc-btn-start"
                        onClick={() => abrirModal(cam)}
                        disabled={!cam.activa || accionando === cam.id_camara}>
                        {accionando === cam.id_camara ? '...' : '▶ Iniciar stream'}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Modal */}
      {modal !== null && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Configurar stream RTSP</h3>
              <button className="modal-close" onClick={() => setModal(null)}>✕</button>
            </div>
            <div className="modal-body">
              {(() => {
                const cam = camaras.find(c => c.id_camara === modal)
                return cam ? (
                  <div className="modal-cam-info">
                    <span className="mci-nombre">{cam.nombre}</span>
                    {cam.direccion_ip && <code className="mci-ip">{cam.direccion_ip}:554</code>}
                  </div>
                ) : null
              })()}
              <div className="field">
                <label>Usuario de la cámara</label>
                <input value={form.rtsp_user}
                  onChange={e => setForm(f => ({ ...f, rtsp_user: e.target.value }))}
                  placeholder="adminadmin" />
              </div>
              <div className="field">
                <label>Contraseña RTSP</label>
                <div className="pass-wrap">
                  <input type={mostrarPass ? 'text' : 'password'}
                    value={form.rtsp_pass}
                    onChange={e => setForm(f => ({ ...f, rtsp_pass: e.target.value }))}
                    placeholder="Contraseña de la app MERCUSYS" />
                  <button type="button" className="pass-toggle"
                    onClick={() => setMostrarPass(v => !v)}>
                    {mostrarPass ? '🙈' : '👁️'}
                  </button>
                </div>
              </div>
              <div className="field">
                <label>Calidad del stream</label>
                <select value={form.stream}
                  onChange={e => setForm(f => ({ ...f, stream: e.target.value }))}>
                  <option value="stream2">stream2 — 720p (recomendado)</option>
                  <option value="stream1">stream1 — 2K 3MP</option>
                </select>
              </div>
              {(() => {
                const cam = camaras.find(c => c.id_camara === modal)
                if (!cam?.direccion_ip) return null
                const u = form.rtsp_pass
                  ? `rtsp://${form.rtsp_user}:****@${cam.direccion_ip}:554/${form.stream}`
                  : `rtsp://${cam.direccion_ip}:554/${form.stream}`
                return (
                  <div className="url-preview">
                    <span className="url-preview-label">URL resultante</span>
                    <code>{u}</code>
                  </div>
                )
              })()}
              {error && <div className="form-error">⚠ {error}</div>}
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setModal(null)}>Cancelar</button>
              <button className="btn-primary" onClick={handleIniciar}
                disabled={accionando === modal}>
                {accionando === modal ? 'Conectando...' : '▶ Iniciar captura'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}