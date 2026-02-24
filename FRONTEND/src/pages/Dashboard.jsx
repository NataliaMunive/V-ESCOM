import { useState, useEffect, useRef } from 'react'
import { getEventos, getCamaras, identificarRostro } from '../services/api'
import './Dashboard.css'

export default function Dashboard() {
  const [eventos, setEventos] = useState([])
  const [camaras, setCamaras] = useState([])
  const [stats, setStats] = useState({ total: 0, autorizados: 0, no_autorizados: 0 })
  const [resultado, setResultado] = useState(null)
  const [identificando, setIdentificando] = useState(false)
  const [preview, setPreview] = useState(null)
  const fileRef = useRef()

  useEffect(() => {
    cargarDatos()
  }, [])

  const cargarDatos = async () => {
    try {
      const [evRes, camRes] = await Promise.all([
        getEventos({ limit: 10 }),
        getCamaras()
      ])
      const evs = evRes.data
      setEventos(evs)
      setCamaras(camRes.data)
      setStats({
        total: evs.length,
        autorizados: evs.filter(e => e.tipo_acceso === 'Autorizado').length,
        no_autorizados: evs.filter(e => e.tipo_acceso === 'No Autorizado').length,
      })
    } catch {}
  }

  const handleFile = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setResultado(null)
  }

  const handleIdentificar = async () => {
    const file = fileRef.current.files[0]
    if (!file) return
    setIdentificando(true)
    setResultado(null)
    try {
      const res = await identificarRostro(file)
      setResultado(res.data)
      cargarDatos()
    } catch (err) {
      setResultado({ error: err.response?.data?.detail || 'Error al procesar la imagen' })
    } finally {
      setIdentificando(false)
    }
  }

  const formatHora = (fecha, hora) => {
    if (!fecha) return '—'
    return `${fecha} ${hora || ''}`
  }

  return (
    <div className="dashboard">
      <div className="page-header">
        <div>
          <h1 className="page-title">Panel de Control</h1>
          <p className="page-sub">Monitoreo en tiempo real · ESCOM-IPN</p>
        </div>
        <div className="header-badge">
          <span className="badge-dot" />
          Sistema activo
        </div>
      </div>

      {/* ── Stats ── */}
      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-icon">◎</span>
          <div>
            <p className="stat-valor">{stats.total}</p>
            <p className="stat-label">Eventos recientes</p>
          </div>
        </div>
        <div className="stat-card stat-ok">
          <span className="stat-icon">✓</span>
          <div>
            <p className="stat-valor">{stats.autorizados}</p>
            <p className="stat-label">Autorizados</p>
          </div>
        </div>
        <div className="stat-card stat-alerta">
          <span className="stat-icon">⚠</span>
          <div>
            <p className="stat-valor">{stats.no_autorizados}</p>
            <p className="stat-label">No autorizados</p>
          </div>
        </div>
        <div className="stat-card">
          <span className="stat-icon">◈</span>
          <div>
            <p className="stat-valor">{camaras.length}</p>
            <p className="stat-label">Cámaras</p>
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* ── Identificador ── */}
        <div className="card identificador">
          <div className="card-header">
            <h2 className="card-title">Identificar rostro</h2>
            <span className="mono tag">ArcFace</span>
          </div>

          <div
            className="drop-zone"
            onClick={() => fileRef.current.click()}
            style={preview ? { padding: 0, overflow: 'hidden' } : {}}
          >
            {preview ? (
              <img src={preview} alt="Preview" className="preview-img" />
            ) : (
              <>
                <div className="drop-icon">⊕</div>
                <p>Clic para subir imagen o frame de cámara</p>
                <span className="drop-hint">JPEG · PNG · máx. 5MB</span>
              </>
            )}
          </div>
          <input
            type="file"
            ref={fileRef}
            accept="image/*"
            onChange={handleFile}
            style={{ display: 'none' }}
          />

          <div className="id-actions">
            {preview && (
              <button className="btn-secondary" onClick={() => { setPreview(null); setResultado(null); fileRef.current.value = '' }}>
                Limpiar
              </button>
            )}
            <button
              className="btn-primary"
              onClick={handleIdentificar}
              disabled={!preview || identificando}
            >
              {identificando ? 'Procesando...' : 'Identificar'}
            </button>
          </div>

          {resultado && !resultado.error && (
            <div className={`resultado ${resultado.tipo_acceso === 'Autorizado' ? 'resultado-ok' : 'resultado-alerta'}`}>
              <div className="resultado-tipo">
                {resultado.tipo_acceso === 'Autorizado' ? '✓' : '⚠'}
                {resultado.tipo_acceso}
              </div>
              {resultado.nombre && (
                <p className="resultado-nombre">{resultado.nombre} {resultado.apellidos}</p>
              )}
              <p className="resultado-sim">
                Similitud: <strong>{(resultado.similitud * 100).toFixed(1)}%</strong>
              </p>
              <p className="resultado-evento mono">Evento #{resultado.id_evento}</p>
            </div>
          )}

          {resultado?.error && (
            <div className="resultado resultado-alerta">
              <div className="resultado-tipo">✕ Error</div>
              <p>{resultado.error}</p>
            </div>
          )}
        </div>

        {/* ── Eventos recientes ── */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Últimos eventos</h2>
            <a href="/eventos" className="ver-todo">Ver todos →</a>
          </div>
          <div className="eventos-lista">
            {eventos.length === 0 && (
              <p className="empty-msg">Sin eventos registrados</p>
            )}
            {eventos.map(ev => (
              <div key={ev.id_evento} className="evento-row">
                <span className={`evento-badge ${ev.tipo_acceso === 'Autorizado' ? 'badge-ok' : 'badge-alerta'}`}>
                  {ev.tipo_acceso === 'Autorizado' ? '✓' : '⚠'}
                </span>
                <div className="evento-info">
                  <span className="evento-tipo">{ev.tipo_acceso}</span>
                  <span className="evento-meta mono">
                    {ev.fecha} {ev.hora?.slice(0,5)} · Cám {ev.id_camara ?? '—'}
                  </span>
                </div>
                <span className="evento-sim">
                  {ev.similitud != null ? `${(ev.similitud * 100).toFixed(0)}%` : '—'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}