import { useEffect, useState } from 'react'
import { getCubiculos, crearCubiculo, actualizarCubiculo, eliminarCubiculo } from '../services/api'
import './Cubiculos.css'

const FORM_VACIO = { numero_cubiculo: '', capacidad: '', responsable: '' }

export default function Cubiculos() {
  const [cubiculos, setCubiculos] = useState([])
  const [cargando, setCargando] = useState(true)
  const [modal, setModal] = useState(null)
  const [seleccionado, setSeleccionado] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { cargar() }, [])

  const cargar = async () => {
    setCargando(true)
    try {
      const r = await getCubiculos()
      setCubiculos(r.data || [])
    } catch {
      setCubiculos([])
    } finally {
      setCargando(false)
    }
  }

  const abrirCrear = () => {
    setForm(FORM_VACIO)
    setError('')
    setModal('crear')
  }

  const abrirEditar = (c) => {
    setSeleccionado(c)
    setForm({
      numero_cubiculo: c.numero_cubiculo || '',
      capacidad: c.capacidad?.toString() || '',
      responsable: c.responsable || '',
    })
    setError('')
    setModal('editar')
  }

  const cerrar = () => {
    setModal(null)
    setSeleccionado(null)
    setError('')
  }

  const handleChange = (e) => {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }))
  }

  const handleGuardar = async (e) => {
    e.preventDefault()
    setGuardando(true)
    setError('')

    try {
      const payload = {
        numero_cubiculo: form.numero_cubiculo.trim(),
        capacidad: parseInt(form.capacidad, 10),
        responsable: form.responsable?.trim() || null,
      }

      if (!payload.numero_cubiculo) {
        throw new Error('El número de cubículo es obligatorio')
      }
      if (!payload.capacidad || payload.capacidad < 1) {
        throw new Error('La capacidad debe ser mayor a 0')
      }

      if (modal === 'crear') await crearCubiculo(payload)
      else await actualizarCubiculo(seleccionado.id_cubiculo, payload)

      cerrar()
      cargar()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error al guardar')
    } finally {
      setGuardando(false)
    }
  }

  const handleEliminar = async (c) => {
    if (!confirm(`¿Eliminar el cubículo ${c.numero_cubiculo}?`)) return
    try {
      await eliminarCubiculo(c.id_cubiculo)
      cargar()
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al eliminar cubículo')
    }
  }

  const totalCapacidad = cubiculos.reduce((acc, c) => acc + (c.capacidad || 0), 0)

  return (
    <div className="cubiculos-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Gestión de Cubículos</h1>
          <p className="page-sub">{cubiculos.length} cubículos registrados</p>
        </div>
        <button className="btn-primary" onClick={abrirCrear}>+ Nuevo cubículo</button>
      </div>

      <div className="cub-stats">
        <div className="cub-stat">
          <span className="cub-stat-val">{cubiculos.length}</span>
          <span className="cub-stat-label">Total</span>
        </div>
        <div className="cub-stat cub-stat-ok">
          <span className="cub-stat-val">{totalCapacidad}</span>
          <span className="cub-stat-label">Capacidad total</span>
        </div>
      </div>

      <div className="tabla-wrap">
        {cargando ? (
          <div className="tabla-cargando">Cargando cubículos...</div>
        ) : cubiculos.length === 0 ? (
          <div className="tabla-vacia">
            <p>No hay cubículos registrados</p>
            <button className="btn-primary" onClick={abrirCrear}>Registrar el primero</button>
          </div>
        ) : (
          <table className="tabla">
            <thead>
              <tr>
                <th>ID</th>
                <th>Número</th>
                <th>Capacidad</th>
                <th>Responsable</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {cubiculos.map(c => (
                <tr key={c.id_cubiculo}>
                  <td className="td-muted mono">#{c.id_cubiculo}</td>
                  <td><strong>{c.numero_cubiculo}</strong></td>
                  <td>{c.capacidad}</td>
                  <td className="td-muted">{c.responsable || '—'}</td>
                  <td>
                    <div className="acciones">
                      <button className="btn-icono" type="button" title="Editar" aria-label="Editar" onClick={() => abrirEditar(c)}>
                        <img src="/icons/editar.svg" alt="" />
                      </button>
                      <button className="btn-icono btn-danger" type="button" title="Eliminar" aria-label="Eliminar" onClick={() => handleEliminar(c)}>
                        <img src="/icons/eliminar.svg" alt="" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {error && <div className="form-error">⚠ {error}</div>}

      {modal && (
        <div className="modal-overlay" onClick={cerrar}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{modal === 'crear' ? 'Nuevo cubículo' : 'Editar cubículo'}</h3>
              <button className="modal-close" onClick={cerrar}>✕</button>
            </div>
            <form onSubmit={handleGuardar} className="modal-form">
              <div className="form-row">
                <div className="field">
                  <label>Número de cubículo *</label>
                  <input
                    name="numero_cubiculo"
                    value={form.numero_cubiculo}
                    onChange={handleChange}
                    required
                    placeholder="Ej. A-203"
                  />
                </div>
                <div className="field">
                  <label>Capacidad *</label>
                  <input
                    name="capacidad"
                    type="number"
                    min="1"
                    value={form.capacidad}
                    onChange={handleChange}
                    required
                    placeholder="Ej. 8"
                  />
                </div>
              </div>
              <div className="field">
                <label>Responsable</label>
                <input
                  name="responsable"
                  value={form.responsable}
                  onChange={handleChange}
                  placeholder="Ej. M. en C. Ana Pérez"
                />
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
