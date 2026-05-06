import { useState, useEffect, useRef } from 'react'
import {
  getPersonas, getPersona, getEventos, crearPersona, actualizarPersona,
  eliminarPersona, subirRostro, getCubiculos
} from '../services/api'
import './Personas.css'

const FORM_VACIO = { nombre: '', apellidos: '', email: '', telefono: '', id_cubiculo: '', rol: 'Profesor' }

export default function Personas() {
  const [personas, setPersonas] = useState([])
  const [cargando, setCargando] = useState(true)
  const [modal, setModal] = useState(null)       // null | 'crear' | 'editar'
  const [verModal, setVerModal] = useState(false)
  const [seleccionada, setSeleccionada] = useState(null)
  const [perfil, setPerfil] = useState(null)
  const [eventosPerfil, setEventosPerfil] = useState([])
  const [cargandoPerfil, setCargandoPerfil] = useState(false)
  const [form, setForm] = useState(FORM_VACIO)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [busqueda, setBusqueda] = useState('')
  const [subiendoFoto, setSubiendoFoto] = useState(null) // id_persona
  const fotoRef = useRef()
  const [duplicadoInfo, setDuplicadoInfo] = useState(null)
  const [cubiculos, setCubiculos] = useState([])
  const fotoPerfil = perfil?.ruta_rostro ? `/${String(perfil.ruta_rostro).replace(/\\/g, '/')}` : null
  useEffect(() => { cargar(); cargarCubiculos() }, [])

  const cargar = async () => {
    setCargando(true)
    try {
      const res = await getPersonas()
      setPersonas(res.data)
    } catch {}
    finally { setCargando(false) }
  }

  const cargarCubiculos = async () => {
    try {
      const res = await getCubiculos()
      setCubiculos(res.data || [])
    } catch {
      setCubiculos([])
    }
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

  const abrirPerfil = async (p) => {
    setCargandoPerfil(true)
    setVerModal(true)
    setPerfil(null)
    setEventosPerfil([])
    try {
      const [perfilRes, eventosRes] = await Promise.all([
        getPersona(p.id_persona),
        getEventos({ id_persona: p.id_persona, limit: 20 }),
      ])
      setPerfil(perfilRes.data)
      setEventosPerfil(eventosRes.data || [])
    } catch (err) {
      setPerfil(p)
      setEventosPerfil([])
      setError(err.response?.data?.detail || 'No se pudo cargar el perfil')
    } finally {
      setCargandoPerfil(false)
    }
  }

  const cerrarModal = () => { setModal(null); setSeleccionada(null); setError('') }
  const cerrarPerfil = () => { setVerModal(false); setPerfil(null); setEventosPerfil([]); setCargandoPerfil(false) }

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

  const handleFoto = async (e, id_persona, forzar = false) => {
  const file = e?.target?.files?.[0] ?? fotoRef.current._pendingFile
  if (!file) return
 
  // guardamos referencia al archivo para poder re-usarla si el usuario fuerza
  fotoRef.current._pendingFile = file
  fotoRef.current._pendingId   = id_persona
 
  setSubiendoFoto(id_persona)
  setDuplicadoInfo(null)
 
  try {
    await subirRostro(id_persona, file, forzar)
    // limpiar estado pendiente
    fotoRef.current._pendingFile = null
    fotoRef.current._pendingId   = null
    if (fotoRef.current) fotoRef.current.value = ''
    cargar()
  } catch (err) {
    if (err.response?.status === 409) {
      // Posible duplicado — mostrar modal de advertencia
      const detail = err.response.data?.detail
      setDuplicadoInfo({
        id_persona,
        similitud: detail?.similitud,
        persona_similar: detail?.persona_similar,
      })
    } else {
      alert(err.response?.data?.detail || 'Error al subir la foto')
    }
  } finally {
    setSubiendoFoto(null)
  }
}
 
// helper para cuando el usuario decide forzar desde el modal
const handleForzarRostro = async () => {
  const id_persona = fotoRef.current._pendingId
  setDuplicadoInfo(null)
  setSubiendoFoto(id_persona)
  try {
    await subirRostro(id_persona, fotoRef.current._pendingFile, true)
    fotoRef.current._pendingFile = null
    fotoRef.current._pendingId   = null
    if (fotoRef.current) fotoRef.current.value = ''
    cargar()
  } catch (err) {
    alert(err.response?.data?.detail || 'Error al subir la foto')
  } finally {
    setSubiendoFoto(null)
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
          <p className="page-sub">{personas.length} registros · Profesores, administrativos e investigadores autorizados</p>
        </div>
        <button className="btn-primary" onClick={abrirCrear}>+ Registrar persona autorizada</button>
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
                        type="button"
                        title="Subir foto de rostro"
                        aria-label="Subir foto de rostro"
                        onClick={() => { fotoRef.current.dataset.id = p.id_persona; fotoRef.current.click() }}
                        disabled={subiendoFoto === p.id_persona}
                      >
                        {subiendoFoto === p.id_persona ? '...' : <img src="/icons/foto.svg" alt="" />}
                      </button>
                      <button className="btn-accion" type="button" title="Editar" aria-label="Editar" onClick={() => abrirEditar(p)}>
                        <img src="/icons/editar.svg" alt="" />
                      </button>
                      <button className="btn-accion" type="button" title="Ver perfil" aria-label="Ver perfil" onClick={() => abrirPerfil(p)}>
                        <img src="/icons/ver.svg" alt="" />
                      </button>
                      <button className="btn-accion btn-danger" type="button" title="Eliminar" aria-label="Eliminar" onClick={() => handleEliminar(p)}>
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
                  <label>Cubículo</label>
                  <select name="id_cubiculo" value={form.id_cubiculo} onChange={handleChange}>
                    <option value="">Sin asignar</option>
                    {cubiculos.map(c => (
                      <option key={c.id_cubiculo} value={c.id_cubiculo}>
                        {c.numero_cubiculo} (ID {c.id_cubiculo})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {error && <div className="form-error"> {error}</div>}

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

      {verModal && (
        <div className="modal-overlay" onClick={cerrarPerfil}>
          <div className="modal modal-perfil" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Persona autorizada</h3>
              <button className="modal-close" onClick={cerrarPerfil}>✕</button>
            </div>

            {cargandoPerfil ? (
              <div className="modal-perfil-loading">Cargando perfil...</div>
            ) : perfil ? (
              <div className="perfil-wrap">
                <div className="perfil-top">
                  <div className="perfil-foto-card">
                    {fotoPerfil ? (
                      <img src={fotoPerfil} alt={`${perfil.nombre} ${perfil.apellidos}`} className="perfil-foto" />
                    ) : (
                      <div className="persona-avatar perfil-fallback">{perfil.nombre?.[0]?.toUpperCase()}</div>
                    )}
                  </div>

                  <div className="perfil-datos">
                    <div className="perfil-linea"><span>Nombre:</span> <strong>{perfil.nombre} {perfil.apellidos}</strong></div>
                    <div className="perfil-linea"><span>Rol:</span> <strong>{perfil.rol}</strong></div>
                    <div className="perfil-linea"><span>Cubículo:</span> <strong>{perfil.id_cubiculo ?? '—'}</strong></div>
                    <div className="perfil-linea"><span>Teléfono de contacto:</span> <strong>{perfil.telefono || '—'}</strong></div>
                    <div className="perfil-linea"><span>Correo institucional:</span> <strong>{perfil.email || '—'}</strong></div>
                  </div>
                </div>

                <div className="perfil-section">
                  <h4>Historial de Accesos</h4>
                  {eventosPerfil.length === 0 ? (
                    <div className="perfil-vacio">No hay accesos registrados para esta persona.</div>
                  ) : (
                    <div className="perfil-tabla-wrap">
                      <table className="perfil-tabla">
                        <thead>
                          <tr>
                            <th>Fecha y hora</th>
                            <th>Evento</th>
                            <th>Cámara</th>
                            <th>Cubículo</th>
                          </tr>
                        </thead>
                        <tbody>
                          {eventosPerfil.map((ev) => (
                            <tr key={ev.id_evento}>
                              <td>{ev.fecha || '—'} · {ev.hora || '—'}</td>
                              <td>Persona Autorizada</td>
                              <td>{ev.id_camara ? `Cámara ${ev.id_camara}` : '—'}</td>
                              <td>{perfil.id_cubiculo ?? '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="modal-perfil-loading">No se pudo cargar el perfil.</div>
            )}
          </div>
        </div>
      )}

      {duplicadoInfo && (
  <div className="modal-overlay" onClick={() => setDuplicadoInfo(null)}>
    <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 440 }}>
      <div className="modal-header">
        <h3>⚠ Posible rostro duplicado</h3>
        <button className="modal-close" onClick={() => setDuplicadoInfo(null)}>✕</button>
      </div>
      <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
        <p style={{ fontSize: 14, color: 'var(--texto)' }}>
          El rostro que intentas registrar tiene una similitud de{' '}
          <strong>{((duplicadoInfo.similitud ?? 0) * 100).toFixed(1)}%</strong> con otra persona
          ya registrada:
        </p>
        {duplicadoInfo.persona_similar && (
          <div style={{
            background: 'var(--fondo-card2)', border: '1px solid var(--borde)',
            borderRadius: 8, padding: '12px 16px', fontSize: 13
          }}>
            <div style={{ fontWeight: 600, color: 'var(--texto)' }}>
              {duplicadoInfo.persona_similar.nombre} {duplicadoInfo.persona_similar.apellidos}
            </div>
            <div style={{ color: 'var(--texto-suave)', marginTop: 4 }}>
              {duplicadoInfo.persona_similar.rol} · ID #{duplicadoInfo.persona_similar.id_persona}
            </div>
          </div>
        )}
        <p style={{ fontSize: 13, color: 'var(--texto-suave)' }}>
          ¿Deseas continuar y registrar el embedding de todas formas?
        </p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button className="btn-secondary" onClick={() => setDuplicadoInfo(null)}>
            Cancelar
          </button>
          <button
            className="btn-primary"
            style={{ background: 'linear-gradient(135deg, #c0392b, #e74c3c)' }}
            onClick={handleForzarRostro}
          >
            Continuar de todas formas
          </button>
        </div>
      </div>
    </div>
  </div>
)}
    </div>
  )
}