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
      const r = await api.get('/stream/activas')
      const estado = {}
      r.data.camaras_activas.forEach(id => { estado[id] = true })
      setMonitoreando(estado)
    } catch {}
  }

  const handleIniciarStream = async (c) => {
    setCargandoStream(s => ({ ...s, [c.id_camara]: true }))
    try {
      await api.post(`/stream/${c.id_camara}/iniciar?intervalo=3`)
      setMonitoreando(m => ({ ...m, [c.id_camara]: true }))
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al iniciar monitoreo')
    } finally {
      setCargandoStream(s => ({ ...s, [c.id_camara]: false }))
    }
  }

  const handleDetenerStream = async (c) => {
    setCargandoStream(s => ({ ...s, [c.id_camara]: true }))
    try {
      await api.post(`/stream/${c.id_camara}/detener`)
      setMonitoreando(m => ({ ...m, [c.id_camara]: false }))
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al detener monitoreo')
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
    } catch (err) { setError(err.response?.data?.detail || 'Error al guardar') }
    finally { setGuardando(false) }
  }

  const handleDesactivar = async (c) => {
    if (!confirm(`¿Desactivar la cámara "${c.nombre}"?`)) return
    try { await desactivarCamara(c.id_camara); cargar() }
    catch (err) { alert(err.response?.data?.detail || 'Error al desactivar') }
  }

  const activas   = camaras.filter(c => c.activa).length
  const inactivas = camaras.filter(c => !c.activa).length
  const enMonitoreo = Object.values(monitoreando).filter(Boolean).length

  return (
    <div className="camaras-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Gestión de Cámaras</h1>
          <p className="page-sub">{camaras.length} cámaras · {enMonitoreo} en monitoreo activo</p>
        </div>
        <button className="btn-primary" onClick={abrirCrear}>+ Nueva cámara</button>
      </div>

      <div className="cam-stats">
        <div className="cam-stat">
          <span className="cam-stat-val">{camaras.length}</span>
          <span className="cam-stat-label">Total</span>
        </div>
        <div className="cam-stat cam-stat-ok">
          <span className="cam-stat-val">{activas}</span>
          <span className="cam-stat-label">Activas</span>
        </div>
        <div className="cam-stat cam-stat-off">
          <span className="cam-stat-val">{inactivas}</span>
          <span className="cam-stat-label">Inactivas</span>
        </div>
        <div className="cam-stat" style={{ borderLeft: '3px solid var(--acento)' }}>
          <span className="cam-stat-val" style={{ color: 'var(--acento)' }}>{enMonitoreo}</span>
          <span className="cam-stat-label">Monitoreando</span>
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
            <div key={c.id_camara} className={`camara-card ${!c.activa ? 'inactiva' : ''}`}>
              <div className="camara-card-header">
                <div className="camara-icono">◈</div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                  <span className={`camara-estado ${c.activa ? 'estado-ok' : 'estado-off'}`}>
                    {c.activa ? '● Activa' : '○ Inactiva'}
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
                {c.activa && c.direccion_ip && (
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
                      : handleIniciarStream(c)
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
                <div style={{ display: 'flex', gap: 6 }}>
                  <button className="btn-accion" style={{ flex: 1 }} onClick={() => abrirEditar(c)}>
                    ✏️ Editar
                  </button>
                  {c.activa && (
                    <button
                      className="btn-accion btn-danger"
                      style={{ flex: 1 }}
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
    </div>
  )
}