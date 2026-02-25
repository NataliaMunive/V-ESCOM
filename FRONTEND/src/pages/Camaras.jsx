import { useState, useEffect } from 'react'
import { getCamaras, crearCamara, actualizarCamara, desactivarCamara } from '../services/api'
import './Camaras.css'

const FORM_VACIO = { nombre: '', ubicacion: '', id_cubiculo: '', activa: true }

export default function Camaras() {
  const [camaras, setCamaras] = useState([])
  const [cargando, setCargando] = useState(true)
  const [modal, setModal] = useState(null)
  const [seleccionada, setSeleccionada] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { cargar() }, [])

  const cargar = async () => {
    setCargando(true)
    try { const r = await getCamaras(); setCamaras(r.data) }
    catch {}
    finally { setCargando(false) }
  }

  const abrirCrear = () => { setForm(FORM_VACIO); setError(''); setModal('crear') }

  const abrirEditar = (c) => {
    setSeleccionada(c)
    setForm({
      nombre: c.nombre || '',
      ubicacion: c.ubicacion || '',
      id_cubiculo: c.id_cubiculo || '',
      activa: c.activa,
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
      const payload = { ...form, id_cubiculo: form.id_cubiculo ? parseInt(form.id_cubiculo) : null }
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

  return (
    <div className="camaras-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Gestión de Cámaras</h1>
          <p className="page-sub">{camaras.length} cámaras registradas</p>
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
      </div>

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
                <span className={`camara-estado ${c.activa ? 'estado-ok' : 'estado-off'}`}>
                  {c.activa ? '● Activa' : '○ Inactiva'}
                </span>
              </div>
              <h3 className="camara-nombre">{c.nombre}</h3>
              <p className="camara-ubicacion">{c.ubicacion || 'Sin ubicación'}</p>
              <div className="camara-meta">
                <span className="mono">ID #{c.id_camara}</span>
                {c.id_cubiculo && <span className="mono">Cubículo {c.id_cubiculo}</span>}
              </div>
              <div className="camara-acciones">
                <button className="btn-accion" onClick={() => abrirEditar(c)}>✏️ Editar</button>
                {c.activa && (
                  <button className="btn-accion btn-danger" onClick={() => handleDesactivar(c)}>
                    ⏹ Desactivar
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

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
                <input name="nombre" value={form.nombre} onChange={handleChange} required placeholder="Ej. Cámara Pasillo 1" />
              </div>
              <div className="field">
                <label>Ubicación</label>
                <input name="ubicacion" value={form.ubicacion} onChange={handleChange} placeholder="Ej. Pasillo 3er piso" />
              </div>
              <div className="field">
                <label>ID Cubículo</label>
                <input name="id_cubiculo" type="number" value={form.id_cubiculo} onChange={handleChange} />
              </div>
              {modal === 'editar' && (
                <div className="field field-check">
                  <label className="check-label">
                    <input type="checkbox" name="activa" checked={form.activa} onChange={handleChange} />
                    Cámara activa
                  </label>
                </div>
              )}
              {error && <div className="form-error">⚠ {error}</div>}
              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={cerrar}>Cancelar</button>
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