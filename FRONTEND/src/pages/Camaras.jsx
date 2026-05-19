import { useState, useEffect } from 'react'
import { getCamaras, crearCamara, actualizarCamara, desactivarCamara } from '../services/api'
import api from '../services/api'
import './Camaras.css'

const FORM_VACIO = { nombre: '', direccion_ip: '', ubicacion: '', id_cubiculo: '', activa: true }

export default function Camaras() {
  const [camaras, setCamaras]           = useState([])
  const [cargando, setCargando]         = useState(true)
  const [modal, setModal]               = useState(null)
  const [seleccionada, setSeleccionada] = useState(null)
  const [form, setForm]                 = useState(FORM_VACIO)
  const [guardando, setGuardando]       = useState(false)
  const [error, setError]               = useState('')
  const [monitoreando, setMonitoreando] = useState({}) // { id_camara: bool }
  const [cargandoStream, setCargandoStream] = useState({}) // { id_camara: bool }
  const [modalStream, setModalStream] = useState(null) // { camara }
  const [formStream, setFormStream]   = useState({ rtsp_user: 'adminadmin', rtsp_pass: '', stream: 'stream2' })
  const [mostrarPassStream, setMostrarPassStream] = useState(false)

  const normalizarError = (detail, fallback) => {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map(item => item?.msg || item?.message || JSON.stringify(item))
        .join(' | ')
    }
    if (detail && typeof detail === 'object') {
      return detail.msg || detail.message || JSON.stringify(detail)
    }
    return fallback
  }

  useEffect(() => {
    cargar()
    cargarEstadoStreams()
  }, [])

  const cargar = async () => {
    setCargando(true)
    try { const r = await getCamaras(); setCamaras(r.data) }
    catch {}
    finally { setCargando(false) }
  }

  // Consulta al backend qué cámaras están siendo monitoreadas actualmente
  const cargarEstadoStreams = async () => {
    try {
      const r = await api.get('/rtsp/estado')
      const estado = {}
      r.data.forEach(w => { if (w.activo) estado[w.id_camara] = true })
      setMonitoreando(estado)
    } catch {}
  }

  const handleIniciarStream = async (credenciales) => {
    const cam = modalStream
    setModalStream(null)
    setCargandoStream(s => ({ ...s, [cam.id_camara]: true }))
    try {
      await api.post('/rtsp/iniciar', {
        id_camara:  cam.id_camara,
        rtsp_user:  credenciales.rtsp_user,
        rtsp_pass:  credenciales.rtsp_pass,
        stream:     credenciales.stream,
      })
      setMonitoreando(m => ({ ...m, [cam.id_camara]: true }))
    } catch (err) {
      alert(normalizarError(err.response?.data?.detail, 'No se pudo abrir el stream'))
    } finally {
      setCargandoStream(s => ({ ...s, [cam.id_camara]: false }))
    }
  }

  const handleDetenerStream = async (c) => {
    setCargandoStream(s => ({ ...s, [c.id_camara]: true }))
    try {
      await api.delete(`/rtsp/detener/${c.id_camara}`)
      setMonitoreando(m => ({ ...m, [c.id_camara]: false }))
    } catch (err) {
      alert(normalizarError(err.response?.data?.detail, 'Error al detener monitoreo'))
    } finally {
      setCargandoStream(s => ({ ...s, [c.id_camara]: false }))
    }
  }

  const abrirCrear = () => { setForm(FORM_VACIO); setError(''); setModal('crear') }

  const abrirEditar = (c) => {
    setSeleccionada(c)
    setForm({
      nombre:       c.nombre      || '',
      direccion_ip: c.direccion_ip || '',
      ubicacion:    c.ubicacion   || '',
      id_cubiculo:  c.id_cubiculo || '',
      activa:       c.activa,
    })
    setError(''); setModal('editar')
  }

  const cerrar = () => { setModal(null); setSeleccionada(null); setError('') }

  const handleChange = (e) => {
    const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    setForm(f => ({ ...f, [e.target.name]: val }))
  }

  const handleGuardar = async (e) => {
    e.preventDefault(); setGuardando(true); setError('')
    try {
      const payload = {
        ...form,
        id_cubiculo: form.id_cubiculo ? parseInt(form.id_cubiculo) : null
      }
      if (modal === 'crear') await crearCamara(payload)
      else await actualizarCamara(seleccionada.id_camara, payload)
      cerrar(); cargar()
    } catch (err) { setError(normalizarError(err.response?.data?.detail, 'Error al guardar')) }
    finally { setGuardando(false) }
  }

  const handleDesactivar = async (c) => {
    if (!confirm(`¿Desactivar la cámara "${c.nombre}"?`)) return
    try { await desactivarCamara(c.id_camara); cargar() }
    catch (err) { alert(normalizarError(err.response?.data?.detail, 'Error al desactivar')) }
  }

  const inactivas = camaras.filter(c => !c.activa).length
  const enMonitoreo = Object.values(monitoreando).filter(Boolean).length
  const sinConexion = camaras.length - enMonitoreo

  return (
    <div className="camaras-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Gestión de Cámaras</h1>
          <p className="page-sub">{camaras.length} cámaras · {enMonitoreo} en vivo · {sinConexion} sin conexión</p>
        </div>
        <button className="btn-primary" onClick={abrirCrear}>+ Nueva cámara</button>
      </div>

      <div className="cam-stats">
        <div className="cam-stat">
          <span className="cam-stat-val">{camaras.length}</span>
          <span className="cam-stat-label">Total</span>
        </div>
        <div className="cam-stat cam-stat-ok">
          <span className="cam-stat-val">{enMonitoreo}</span>
          <span className="cam-stat-label">En vivo</span>
        </div>
        <div className="cam-stat cam-stat-off">
          <span className="cam-stat-val">{sinConexion}</span>
          <span className="cam-stat-label">Sin conexión</span>
        </div>
      </div>

      {/* Banner informativo si hay cámaras activas */}
      {enMonitoreo > 0 && (
        <div style={{
          marginBottom: 16,
          padding: '10px 16px',
          borderRadius: 8,
          background: 'rgba(0,194,224,0.08)',
          border: '1px solid rgba(0,194,224,0.25)',
          fontSize: 13,
          color: 'var(--acento)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}>
          <span style={{ fontSize: 16 }}>◈</span>
          {enMonitoreo} cámara{enMonitoreo > 1 ? 's' : ''} procesando frames con ArcFace en tiempo real.
          Las alertas aparecerán automáticamente en la página de Alertas.
        </div>
      )}

      {cargando ? (
        <div className="tabla-cargando">Cargando cámaras...</div>
      ) : camaras.length === 0 ? (
        <div className="tabla-vacia">
          <p>No hay cámaras registradas</p>
          <button className="btn-primary" onClick={abrirCrear}>Registrar la primera</button>
        </div>
      ) : (
        <div className="camaras-grid">
          {camaras.map(c => (
            <div key={c.id_camara} className={`camara-card ${!monitoreando[c.id_camara] ? 'inactiva' : ''}`}>
              <div className="camara-card-header">
                <div className="camara-icono">◈</div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                  <span className={`camara-estado ${monitoreando[c.id_camara] ? 'estado-ok' : 'estado-off'}`}>
                    {monitoreando[c.id_camara] ? '● Activa' : '○ Apagada'}
                  </span>
                  {monitoreando[c.id_camara] && (
                    <span style={{
                      fontSize: 10, fontWeight: 700, color: 'var(--acento)',
                      background: 'rgba(0,194,224,0.12)',
                      border: '1px solid rgba(0,194,224,0.3)',
                      borderRadius: 10, padding: '1px 8px',
                      animation: 'pulse 2s ease-in-out infinite',
                    }}>
                      ● EN VIVO
                    </span>
                  )}
                </div>
              </div>

              <h3 className="camara-nombre">{c.nombre}</h3>
              <p className="camara-ubicacion">{c.ubicacion || 'Sin ubicación'}</p>

              {/* Mostrar URL/IP configurada */}
              {c.direccion_ip && (
                <p className="mono" style={{
                  fontSize: 11, color: 'var(--texto-muted)',
                  marginBottom: 8, wordBreak: 'break-all',
                }}>
                  {c.direccion_ip}
                </p>
              )}

              <div className="camara-meta">
                <span className="mono">ID #{c.id_camara}</span>
                {c.id_cubiculo && <span className="mono">Cubículo {c.id_cubiculo}</span>}
              </div>

              <div className="camara-acciones" style={{ flexDirection: 'column', gap: 6 }}>
                {/* Botón Monitorear / Detener */}
                {c.direccion_ip && (
                  <button
                    className={`btn-accion ${monitoreando[c.id_camara] ? 'btn-danger' : ''}`}
                    style={{
                      width: '100%',
                      fontWeight: 600,
                      background: monitoreando[c.id_camara]
                        ? 'rgba(230,57,70,0.1)'
                        : 'rgba(45,198,83,0.08)',
                      borderColor: monitoreando[c.id_camara]
                        ? 'rgba(230,57,70,0.4)'
                        : 'rgba(45,198,83,0.3)',
                      color: monitoreando[c.id_camara]
                        ? 'var(--rojo-alerta)'
                        : 'var(--verde-ok)',
                    }}
                    disabled={cargandoStream[c.id_camara]}
                    onClick={() => monitoreando[c.id_camara]
                      ? handleDetenerStream(c)
                      : setModalStream(c)
                    }
                  >
                    {cargandoStream[c.id_camara]
                      ? '...'
                      : monitoreando[c.id_camara]
                        ? '⏹ Detener monitoreo'
                        : '▶ Iniciar monitoreo'
                    }
                  </button>
                )}

                {/* Botones editar / desactivar */}
                <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
                  <button className="btn-accion" style={{ flex: 1, minHeight: 40 }} onClick={() => abrirEditar(c)}>
                    <img src="/icons/editar.svg" alt="" style={{ width: 18, height: 18 }} />
                    Editar
                  </button>
                  {c.activa && (
                    <button
                      className="btn-accion btn-danger"
                      style={{ flex: 1, minHeight: 40 }}
                      onClick={() => handleDesactivar(c)}
                    >
                      ⏹ Desactivar
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal crear/editar */}
      {modal && (
        <div className="modal-overlay" onClick={cerrar}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{modal === 'crear' ? 'Nueva cámara' : 'Editar cámara'}</h3>
              <button className="modal-close" onClick={cerrar}>✕</button>
            </div>
            <form onSubmit={handleGuardar} className="modal-form">
              <div className="field">
                <label>Nombre *</label>
                <input
                  name="nombre"
                  value={form.nombre}
                  onChange={handleChange}
                  required
                  placeholder="Ej. Cámara Pasillo 1"
                />
              </div>

              <div className="field">
                <label>URL / Dirección IP del stream *</label>
                <input
                  name="direccion_ip"
                  value={form.direccion_ip}
                  onChange={handleChange}
                  placeholder="rtsp://192.168.1.100:554/stream  ó  0 para webcam"
                />
                <span style={{ fontSize: 11, color: 'var(--texto-muted)', marginTop: 4 }}>
                  Ejemplos: rtsp://admin:pass@192.168.1.10:554/stream · http://IP/video.mjpg · 0 (webcam local)
                </span>
              </div>

              <div className="field">
                <label>Ubicación</label>
                <input
                  name="ubicacion"
                  value={form.ubicacion}
                  onChange={handleChange}
                  placeholder="Ej. Pasillo 3er piso"
                />
              </div>

              <div className="field">
                <label>ID Cubículo</label>
                <input
                  name="id_cubiculo"
                  type="number"
                  value={form.id_cubiculo}
                  onChange={handleChange}
                />
              </div>

              {modal === 'editar' && (
                <div className="field field-check">
                  <label className="check-label">
                    <input
                      type="checkbox"
                      name="activa"
                      checked={form.activa}
                      onChange={handleChange}
                    />
                    Cámara activa
                  </label>
                </div>
              )}

              {error && <div className="form-error">⚠ {error}</div>}

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={cerrar}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary" disabled={guardando}>
                  {guardando ? 'Guardando...' : 'Guardar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Modal credenciales RTSP */}
{modalStream && (
  <div className="modal-overlay" onClick={() => setModalStream(null)}>
    <div className="modal" onClick={e => e.stopPropagation()}>
      <div className="modal-header">
        <h3>Iniciar stream — {modalStream.nombre}</h3>
        <button className="modal-close" onClick={() => setModalStream(null)}>✕</button>
      </div>
      <div className="modal-form">
        {modalStream.direccion_ip && (
          <div style={{
            background: 'var(--fondo-card2)', border: '1px solid var(--borde)',
            borderRadius: 8, padding: '10px 14px', marginBottom: 4,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between'
          }}>
            <span style={{ fontSize: 13, color: 'var(--texto)', fontWeight: 600 }}>
              {modalStream.nombre}
            </span>
            <code style={{ fontSize: 12, color: 'var(--acento)', fontFamily: 'var(--fuente-mono)' }}>
              {modalStream.direccion_ip}:554
            </code>
          </div>
        )}

        <div className="field">
          <label>Usuario RTSP</label>
          <input
            value={formStream.rtsp_user}
            onChange={e => setFormStream(f => ({ ...f, rtsp_user: e.target.value }))}
            placeholder="adminadmin"
          />
        </div>

        <div className="field">
          <label>Contraseña RTSP</label>
          <div className="pass-wrap">
            <input
              type={mostrarPassStream ? 'text' : 'password'}
              value={formStream.rtsp_pass}
              onChange={e => setFormStream(f => ({ ...f, rtsp_pass: e.target.value }))}
              placeholder="Contraseña de la camara"
            />
            <button type="button" className="pass-toggle"
              onClick={() => setMostrarPassStream(v => !v)}>
              {mostrarPassStream ? '🙈' : '👁️'}
            </button>
          </div>
        </div>

        <div className="field">
          <label>Calidad del stream</label>
          <select
            value={formStream.stream}
            onChange={e => setFormStream(f => ({ ...f, stream: e.target.value }))}
          >
            <option value="stream2">stream2 — 720p (recomendado)</option>
            <option value="stream1">stream1 — 2K 3MP</option>
          </select>
        </div>

        {/* Preview URL */}
        {modalStream.direccion_ip && (
          <div style={{
            background: 'rgba(0,194,224,0.05)',
            border: '1px solid rgba(0,194,224,0.15)',
            borderRadius: 8, padding: '10px 14px',
          }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--texto-muted)',
              textTransform: 'uppercase', letterSpacing: '0.8px', marginBottom: 4 }}>
              URL resultante
            </div>
            <code style={{ fontSize: 11, color: 'var(--acento)', wordBreak: 'break-all',
              fontFamily: 'var(--fuente-mono)' }}>
              {formStream.rtsp_pass
                ? `rtsp://${formStream.rtsp_user}:****@${modalStream.direccion_ip}:554/${formStream.stream}`
                : `rtsp://${modalStream.direccion_ip}:554/${formStream.stream}`
              }
            </code>
          </div>
        )}

        <div className="modal-actions">
          <button className="btn-secondary" onClick={() => setModalStream(null)}>
            Cancelar
          </button>
          <button
            className="btn-primary"
            onClick={() => handleIniciarStream(formStream)}
            disabled={cargandoStream[modalStream.id_camara]}
          >
            {cargandoStream[modalStream.id_camara] ? 'Conectando...' : '▶ Iniciar stream'}
          </button>
        </div>
      </div>
    </div>
  </div>
)}
    </div>
  )
}