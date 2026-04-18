import { useEffect, useState } from 'react'
import {
  getProfesores,
  crearProfesor,
  actualizarProfesor,
  desactivarProfesor,
  getCubiculos,
} from '../services/api'
import './Profesores.css'

const FORM_VACIO = {
  nombre: '',
  correo: '',
  telefono: '',
  id_cubiculo: '',
}

export default function Profesores() {
  const [profesores, setProfesores] = useState([])
  const [cubiculos, setCubiculos] = useState([])
  const [cargando, setCargando] = useState(true)
  const [modal, setModal] = useState(null)
  const [seleccionado, setSeleccionado] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    cargar()
    cargarCubiculos()
  }, [])

  const cargar = async () => {
    setCargando(true)
    try {
      const res = await getProfesores()
      setProfesores(res.data || [])
    } catch {
      setProfesores([])
    } finally {
      setCargando(false)
    }
  }

  const cargarCubiculos = async () => {
    try {
      const res = await getCubiculos()
      setCubiculos(res.data || [])
    } catch {
      setCubiculos([])
    }
  }

  const cerrar = () => {
    setModal(null)
    setSeleccionado(null)
    setError('')
  }

  const abrirCrear = () => {
    setForm(FORM_VACIO)
    setError('')
    setModal('crear')
  }

  const abrirEditar = (p) => {
    setSeleccionado(p)
    setForm({
      nombre: p.nombre || '',
      correo: p.correo || '',
      telefono: p.telefono || '',
      id_cubiculo: p.id_cubiculo?.toString() || '',
    })
    setError('')
    setModal('editar')
  }

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }))
  }

  const handleGuardar = async (e) => {
    e.preventDefault()
    setGuardando(true)
    setError('')

    try {
      const payload = {
        nombre: form.nombre.trim(),
        correo: form.correo.trim(),
        telefono: form.telefono.trim(),
        id_cubiculo: form.id_cubiculo ? parseInt(form.id_cubiculo, 10) : null,
      }

      if (!payload.id_cubiculo) {
        throw new Error('Selecciona un cubículo para el profesor')
      }

      if (modal === 'crear') await crearProfesor(payload)
      else await actualizarProfesor(seleccionado.id_profesor, payload)

      cerrar()
      cargar()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al guardar')
    } finally {
      setGuardando(false)
    }
  }

  const handleDesactivar = async (p) => {
    if (!confirm(`¿Desactivar a ${p.nombre}?`)) return
    try {
      await desactivarProfesor(p.id_profesor)
      cargar()
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al desactivar')
    }
  }

  const activos = profesores.filter((p) => p.activo).length
  const inactivos = profesores.length - activos

  return (
    <div className="profesores-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Profesores</h1>
          <p className="page-sub">{profesores.length} profesores registrados</p>
        </div>
        <button className="btn-primary" onClick={abrirCrear}>+ Nuevo profesor</button>
      </div>

      <div className="prof-stats">
        <div className="prof-stat">
          <span className="prof-stat-val">{profesores.length}</span>
          <span className="prof-stat-label">Total</span>
        </div>
        <div className="prof-stat prof-stat-ok">
          <span className="prof-stat-val">{activos}</span>
          <span className="prof-stat-label">Activos</span>
        </div>
        <div className="prof-stat prof-stat-off">
          <span className="prof-stat-val">{inactivos}</span>
          <span className="prof-stat-label">Inactivos</span>
        </div>
      </div>

      <div className="tabla-wrap">
        {cargando ? (
          <div className="tabla-cargando">Cargando profesores...</div>
        ) : profesores.length === 0 ? (
          <div className="tabla-vacia">
            <p>No hay profesores registrados</p>
            <button className="btn-primary" onClick={abrirCrear}>Registrar el primero</button>
          </div>
        ) : (
          <table className="tabla">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Correo</th>
                <th>Teléfono</th>
                <th>Cubículo</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {profesores.map((p) => (
                <tr key={p.id_profesor}>
                  <td>{p.nombre}</td>
                  <td className="td-muted">{p.correo}</td>
                  <td className="mono td-muted">{p.telefono || '—'}</td>
                  <td className="mono td-muted">{p.id_cubiculo}</td>
                  <td>
                    <span className={`estado-badge ${p.activo ? 'estado-ok' : 'estado-off'}`}>
                      {p.activo ? '● Activo' : '○ Inactivo'}
                    </span>
                  </td>
                  <td>
                    <div className="acciones">
                      <button className="btn-icono" type="button" title="Editar" aria-label="Editar" onClick={() => abrirEditar(p)}>
                        <img src="/icons/editar.svg" alt="" />
                      </button>
                      {p.activo && (
                        <button className="btn-icono btn-danger" type="button" title="Desactivar" aria-label="Desactivar" onClick={() => handleDesactivar(p)}>
                          <img src="/icons/desactivar.svg" alt="" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modal && (
        <div className="modal-overlay" onClick={cerrar}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{modal === 'crear' ? 'Nuevo profesor' : 'Editar profesor'}</h3>
              <button className="modal-close" onClick={cerrar}>✕</button>
            </div>

            <form onSubmit={handleGuardar} className="modal-form">
              <div className="field">
                <label>Nombre *</label>
                <input name="nombre" value={form.nombre} onChange={handleChange} required />
              </div>

              <div className="field">
                <label>Correo *</label>
                <input name="correo" type="email" value={form.correo} onChange={handleChange} required />
              </div>

              <div className="field">
                <label>Teléfono *</label>
                <input name="telefono" value={form.telefono} onChange={handleChange} required placeholder="55XXXXXXXX" />
              </div>

              <div className="field">
                <label>Cubículo *</label>
                <select name="id_cubiculo" value={form.id_cubiculo} onChange={handleChange} required>
                  <option value="">Selecciona un cubículo</option>
                  {cubiculos.map((c) => (
                    <option key={c.id_cubiculo} value={c.id_cubiculo}>
                      {c.numero_cubiculo} (ID {c.id_cubiculo})
                    </option>
                  ))}
                </select>
              </div>

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
