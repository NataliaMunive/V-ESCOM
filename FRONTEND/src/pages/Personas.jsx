import { useState, useEffect, useRef } from 'react'
import {
  getPersonas, crearPersona, actualizarPersona,
  eliminarPersona, subirRostro
} from '../services/api'
import './Personas.css'

const FORM_VACIO = { nombre: '', apellidos: '', email: '', telefono: '', id_cubiculo: '', rol: 'Profesor' }

export default function Personas() {
  const [personas, setPersonas] = useState([])
  const [cargando, setCargando] = useState(true)
  const [modal, setModal] = useState(null)       // null | 'crear' | 'editar'
  const [seleccionada, setSeleccionada] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [busqueda, setBusqueda] = useState('')
  const [subiendoFoto, setSubiendoFoto] = useState(null) // id_persona
  const fotoRef = useRef()

  useEffect(() => { cargar() }, [])

  const cargar = async () => {
    setCargando(true)
    try {
      const res = await getPersonas()
      setPersonas(res.data)
    } catch {}
    finally { setCargando(false) }
  }

  const abrirCrear = () => {
    setForm(FORM_VACIO)
    setError('')
    setModal('crear')
  }

  const abrirEditar = (p) => {
    setSeleccionada(p)
    setForm({
      nombre: p.nombre || '',
      apellidos: p.apellidos || '',
      email: p.email || '',
      telefono: p.telefono || '',
      id_cubiculo: p.id_cubiculo || '',
      rol: p.rol || 'Profesor',
    })
    setError('')
    setModal('editar')
  }

  const cerrarModal = () => { setModal(null); setSeleccionada(null); setError('') }

  const handleChange = (e) => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleGuardar = async (e) => {
    e.preventDefault()
    setGuardando(true)
    setError('')
    try {
      const payload = {
        ...form,
        id_cubiculo: form.id_cubiculo ? parseInt(form.id_cubiculo) : null,
      }
      if (modal === 'crear') await crearPersona(payload)
      else await actualizarPersona(seleccionada.id_persona, payload)
      cerrarModal()
      cargar()
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al guardar')
    } finally {
      setGuardando(false)
    }
  }

  const handleEliminar = async (p) => {
    if (!confirm(`¿Eliminar a ${p.nombre} ${p.apellidos}?`)) return
    try {
      await eliminarPersona(p.id_persona)
      cargar()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al eliminar')
    }
  }

  const handleFoto = async (e, id_persona) => {
    const file = e.target.files[0]
    if (!file) return
    setSubiendoFoto(id_persona)
    try {
      await subirRostro(id_persona, file)
      cargar()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al subir la foto')
    } finally {
      setSubiendoFoto(null)
      fotoRef.current.value = ''
    }
  }

  const filtradas = personas.filter(p =>
    `${p.nombre} ${p.apellidos} ${p.email}`.toLowerCase().includes(busqueda.toLowerCase())
  )

  return (
    <div className="personas-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Personas Autorizadas</h1>
          <p className="page-sub">{personas.length} registros · ESCOM-IPN</p>
        </div>
        <button className="btn-primary" onClick={abrirCrear}>+ Registrar persona</button>
      </div>

      {/* Buscador */}
      <div className="buscador-wrap">
        <input
          className="buscador"
          type="text"
          placeholder="Buscar por nombre, apellidos o correo..."
          value={busqueda}
          onChange={e => setBusqueda(e.target.value)}
        />
      </div>

      {/* Tabla */}
      <div className="tabla-wrap">
        {cargando ? (
          <div className="tabla-cargando">Cargando...</div>
        ) : filtradas.length === 0 ? (
          <div className="tabla-vacia">
            <p>No hay personas registradas</p>
            <button className="btn-primary" onClick={abrirCrear}>Registrar la primera</button>
          </div>
        ) : (
          <table className="tabla">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Correo</th>
                <th>Rol</th>
                <th>Cubículo</th>
                <th>Embedding</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtradas.map(p => (
                <tr key={p.id_persona}>
                  <td>
                    <div className="persona-nombre-cell">
                      <div className="persona-avatar">
                        {p.nombre?.[0]?.toUpperCase()}
                      </div>
                      <span>{p.nombre} {p.apellidos}</span>
                    </div>
                  </td>
                  <td className="td-muted">{p.email || '—'}</td>
                  <td><span className="rol-badge">{p.rol}</span></td>
                  <td className="td-muted mono">{p.id_cubiculo ?? '—'}</td>
                  <td>
                    <span className={`emb-badge ${p.tiene_embedding ? 'emb-ok' : 'emb-no'}`}>
                      {p.tiene_embedding ? '✓ Registrado' : '✕ Sin foto'}
                    </span>
                  </td>
                  <td>
                    <div className="acciones">
                      {/* Subir foto */}
                      <button
                        className="btn-accion"
                        title="Subir foto de rostro"
                        onClick={() => { fotoRef.current.dataset.id = p.id_persona; fotoRef.current.click() }}
                        disabled={subiendoFoto === p.id_persona}
                      >
                        {subiendoFoto === p.id_persona ? '...' : '📷'}
                      </button>
                      <button className="btn-accion" title="Editar" onClick={() => abrirEditar(p)}>✏️</button>
                      <button className="btn-accion btn-danger" title="Eliminar" onClick={() => handleEliminar(p)}>🗑️</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Input foto oculto */}
      <input
        type="file"
        ref={fotoRef}
        accept="image/*"
        style={{ display: 'none' }}
        onChange={e => handleFoto(e, parseInt(fotoRef.current.dataset.id))}
      />

      {/* Modal */}
      {modal && (
        <div className="modal-overlay" onClick={cerrarModal}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{modal === 'crear' ? 'Registrar persona' : 'Editar persona'}</h3>
              <button className="modal-close" onClick={cerrarModal}>✕</button>
            </div>

            <form onSubmit={handleGuardar} className="modal-form">
              <div className="form-row">
                <div className="field">
                  <label>Nombre *</label>
                  <input name="nombre" value={form.nombre} onChange={handleChange} required />
                </div>
                <div className="field">
                  <label>Apellidos *</label>
                  <input name="apellidos" value={form.apellidos} onChange={handleChange} required />
                </div>
              </div>
              <div className="form-row">
                <div className="field">
                  <label>Correo</label>
                  <input name="email" type="email" value={form.email} onChange={handleChange} />
                </div>
                <div className="field">
                  <label>Teléfono</label>
                  <input name="telefono" value={form.telefono} onChange={handleChange} />
                </div>
              </div>
              <div className="form-row">
                <div className="field">
                  <label>Rol</label>
                  <select name="rol" value={form.rol} onChange={handleChange}>
                    <option value="Profesor">Profesor</option>
                    <option value="Administrativo">Administrativo</option>
                    <option value="Investigador">Investigador</option>
                  </select>
                </div>
                <div className="field">
                  <label>ID Cubículo</label>
                  <input name="id_cubiculo" type="number" value={form.id_cubiculo} onChange={handleChange} />
                </div>
              </div>

              {error && <div className="form-error">⚠ {error}</div>}

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={cerrarModal}>Cancelar</button>
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