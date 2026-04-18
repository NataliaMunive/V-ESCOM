import { useState, useEffect } from 'react'
import { getAdmins, crearAdmin, actualizarAdmin, desactivarAdmin } from '../services/api'
import { useAuth } from '../context/AuthContext'
import './Administradores.css'

const FORM_VACIO = { nombre: '', apellidos: '', email: '', telefono: '', contrasena: '' }

export default function Administradores() {
  const { admin: adminActual } = useAuth()
  const [admins, setAdmins] = useState([])
  const [cargando, setCargando] = useState(true)
  const [modal, setModal] = useState(null)
  const [seleccionado, setSeleccionado] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [mostrarPass, setMostrarPass] = useState(false)

  useEffect(() => { cargar() }, [])

  const cargar = async () => {
    setCargando(true)
    try { const r = await getAdmins(); setAdmins(r.data) }
    catch {}
    finally { setCargando(false) }
  }

  const abrirCrear = () => { setForm(FORM_VACIO); setError(''); setMostrarPass(false); setModal('crear') }

  const abrirEditar = (a) => {
    setSeleccionado(a)
    setForm({ nombre: a.nombre, apellidos: a.apellidos, email: a.email, telefono: a.telefono || '', contrasena: '' })
    setError(''); setMostrarPass(false); setModal('editar')
  }

  const cerrar = () => { setModal(null); setSeleccionado(null); setError('') }
  const handleChange = (e) => setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleGuardar = async (e) => {
    e.preventDefault(); setGuardando(true); setError('')
    try {
      if (modal === 'crear') {
        await crearAdmin(form)
      } else {
        const payload = { ...form }
        if (!payload.contrasena) delete payload.contrasena
        await actualizarAdmin(seleccionado.id_admin, payload)
      }
      cerrar(); cargar()
    } catch (err) { setError(err.response?.data?.detail || 'Error al guardar') }
    finally { setGuardando(false) }
  }

  const handleDesactivar = async (a) => {
    if (a.id_admin === adminActual?.id_admin) { alert('No puedes desactivar tu propia cuenta'); return }
    if (!confirm(`¿Desactivar la cuenta de ${a.nombre} ${a.apellidos}?`)) return
    try { await desactivarAdmin(a.id_admin); cargar() }
    catch (err) { alert(err.response?.data?.detail || 'Error al desactivar') }
  }

  const activos   = admins.filter(a => a.activo).length
  const inactivos = admins.filter(a => !a.activo).length

  return (
    <div className="admins-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Administradores</h1>
          <p className="page-sub">{admins.length} cuentas registradas</p>
        </div>
        <button className="btn-primary" onClick={abrirCrear}>+ Nuevo administrador</button>
      </div>

      <div className="adm-stats">
        <div className="adm-stat">
          <span className="adm-stat-val">{admins.length}</span>
          <span className="adm-stat-label">Total</span>
        </div>
        <div className="adm-stat adm-stat-ok">
          <span className="adm-stat-val">{activos}</span>
          <span className="adm-stat-label">Activos</span>
        </div>
        <div className="adm-stat adm-stat-off">
          <span className="adm-stat-val">{inactivos}</span>
          <span className="adm-stat-label">Inactivos</span>
        </div>
      </div>

      <div className="tabla-wrap">
        {cargando ? (
          <div className="tabla-cargando">Cargando administradores...</div>
        ) : admins.length === 0 ? (
          <div className="tabla-vacia"><p>No hay administradores registrados</p></div>
        ) : (
          <table className="tabla">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Correo</th>
                <th>Teléfono</th>
                <th>Estado</th>
                <th>Registro</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {admins.map(a => (
                <tr key={a.id_admin} className={a.id_admin === adminActual?.id_admin ? 'fila-actual' : ''}>
                  <td>
                    <div className="adm-nombre-cell">
                      <div className="adm-avatar">{a.nombre?.[0]?.toUpperCase()}</div>
                      <div>
                        <span className="adm-nombre">{a.nombre} {a.apellidos}</span>
                        {a.id_admin === adminActual?.id_admin && <span className="yo-badge">Tú</span>}
                      </div>
                    </div>
                  </td>
                  <td className="td-muted">{a.email}</td>
                  <td className="td-muted">{a.telefono || '—'}</td>
                  <td>
                    <span className={`estado-badge ${a.activo ? 'estado-ok' : 'estado-off'}`}>
                      {a.activo ? '● Activo' : '○ Inactivo'}
                    </span>
                  </td>
                  <td className="td-muted mono">{a.fecha_registro?.slice(0, 10) || '—'}</td>
                  <td>
                    <div className="acciones">
                      <button className="btn-icono" type="button" title="Editar" aria-label="Editar" onClick={() => abrirEditar(a)}>
                        <img src="/icons/editar.svg" alt="" />
                      </button>
                      {a.activo && a.id_admin !== adminActual?.id_admin && (
                        <button className="btn-icono btn-danger" type="button" title="Desactivar" aria-label="Desactivar" onClick={() => handleDesactivar(a)}>
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
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{modal === 'crear' ? 'Nuevo administrador' : 'Editar administrador'}</h3>
              <button className="modal-close" onClick={cerrar}>✕</button>
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
              <div className="field">
                <label>Correo institucional *</label>
                <input name="email" type="email" value={form.email} onChange={handleChange} required placeholder="admin@escom.ipn.mx" />
              </div>
              <div className="field">
                <label>Teléfono</label>
                <input name="telefono" value={form.telefono} onChange={handleChange} placeholder="55 1234 5678" />
              </div>
              <div className="field">
                <label>{modal === 'crear' ? 'Contraseña *' : 'Nueva contraseña (dejar vacío para no cambiar)'}</label>
                <div className="pass-wrap">
                  <input
                    name="contrasena"
                    type={mostrarPass ? 'text' : 'password'}
                    value={form.contrasena}
                    onChange={handleChange}
                    required={modal === 'crear'}
                    placeholder="Mínimo 8 caracteres"
                  />
                  <button type="button" className="pass-toggle" onClick={() => setMostrarPass(v => !v)}>
                    {mostrarPass ? '🙈' : '👁️'}
                  </button>
                </div>
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