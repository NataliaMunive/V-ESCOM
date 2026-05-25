import { useState, useEffect, useRef } from 'react'
import {
  getPersonas, getPersona, getEventos, crearPersona, actualizarPersona,
  eliminarPersona, subirRostro, getCubiculos, subirRostrosMultiples, entrenarReconocimiento
} from '../services/api'
import { conectarAlertasWebSocket } from '../services/wsAlertas'
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
  const fotosMultiplesRef = useRef()
  const [duplicadoInfo, setDuplicadoInfo] = useState(null)
  const [loteInfo, setLoteInfo] = useState(null)
  const [loteArchivos, setLoteArchivos] = useState([])
  const [entrenando, setEntrenando] = useState(false)
  const [resultadoEntrenamiento, setResultadoEntrenamiento] = useState(null)
  const [resultadoModal, setResultadoModal] = useState(false)
  const [cubiculos, setCubiculos] = useState([])
  const [modalLote, setModalLote] = useState(null)
  const fotoPerfil = perfil?.ruta_rostro ? `/${String(perfil.ruta_rostro).replace(/\\/g, '/')}` : null
  useEffect(() => { cargar(); cargarCubiculos() }, [])
  // abrir websocket de alertas (incluye notificaciones de entrenamiento)
  const wsRef = useRef(null)
  useEffect(() => {
    const token = localStorage.getItem('vescom_token')
    if (!token) return
    const ws = conectarAlertasWebSocket({
      token,
      onMessage: (msg) => {
        if (!msg || typeof msg !== 'object') return
        if (msg.type === 'entrenamiento_completado') {
          const info = msg.data || {}
          setEntrenando(false)
          setResultadoEntrenamiento(info)
          setResultadoModal(true)
          try { cargar() } catch {}
        }
      },
      onOpen: () => {},
      onClose: () => {},
      onError: () => {},
    })
    wsRef.current = ws
    return () => { try { wsRef.current?.close() } catch {} }
  }, [])

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
      // Si eventosRes.data es un array, usarlo; si es objeto (mensaje), usar array vacío
      const eventos = Array.isArray(eventosRes.data) ? eventosRes.data : []
      setEventosPerfil(eventos)
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
  const cerrarLote = () => {
    setModalLote(null)
    setLoteInfo(null)
    setLoteArchivos(prev => {
      prev.forEach(item => {
        try { URL.revokeObjectURL(item.preview) } catch {}
      })
      return []
    })
    if (fotosMultiplesRef.current) fotosMultiplesRef.current.value = ''
  }

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

  const handleEntrenar = async () => {
    if (!confirm('Esto entrenará el clasificador SVM con los embeddings guardados. ¿Continuar?')) return
    setEntrenando(true)
    setError('')
    try {
      // Llamada asíncrona: el servidor iniciará el entrenamiento en background
      await entrenarReconocimiento()
      // Limpiar resultado previo y esperar notificación por WebSocket
      setResultadoEntrenamiento(null)
      setResultadoModal(false)
    } catch (err) {
      setEntrenando(false)
      setError(err.response?.data?.detail?.mensaje || err.response?.data?.detail || 'Error al iniciar el entrenamiento')
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

  const abrirLote = (p) => {
    setModalLote({ id_persona: p.id_persona, nombre: `${p.nombre} ${p.apellidos}` })
    setLoteInfo(null)
    setLoteArchivos([])
  }

  const handleSeleccionarLote = (e) => {
    const files = Array.from(e?.target?.files || [])
    if (!files.length) return
    setLoteInfo(null)
    setLoteArchivos(prev => {
      const existentes = new Set(prev.map(item => `${item.file.name}_${item.file.size}_${item.file.lastModified}`))
      const nuevos = files
        .filter(file => !existentes.has(`${file.name}_${file.size}_${file.lastModified}`))
        .map(file => ({
          file,
          preview: URL.createObjectURL(file),
        }))
      return [...prev, ...nuevos]
    })
    if (fotosMultiplesRef.current) fotosMultiplesRef.current.value = ''
  }

  const subirLote = async (forzar = false) => {
    if (!loteArchivos.length || !modalLote) return
    setSubiendoFoto(modalLote.id_persona)
    setLoteInfo(null)
    try {
      const res = await subirRostrosMultiples(modalLote.id_persona, loteArchivos.map(item => item.file), forzar)
      setLoteInfo(res.data)
      setLoteArchivos(prev => {
        prev.forEach(item => {
          try { URL.revokeObjectURL(item.preview) } catch {}
        })
        return []
      })
      cargar()
    } catch (err) {
      setLoteInfo(err.response?.data?.detail?.resultado || null)
      setError(err.response?.data?.detail?.mensaje || err.response?.data?.detail || 'Error al subir varias fotos')
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
        <div className="header-actions">
          <button className="btn-secondary" onClick={handleEntrenar} disabled={entrenando}>
            {entrenando ? 'Entrenando...' : 'Entrenar SVM'}
          </button>
          <button className="btn-primary" onClick={abrirCrear}>+ Registrar persona autorizada</button>
        </div>
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
                      <button className="btn-accion" type="button" title="Subir varias fotos" aria-label="Subir varias fotos" onClick={() => abrirLote(p)}>
                        <span className="btn-accion-text">+</span>
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

      {modalLote && (
        <div className="modal-overlay" onClick={cerrarLote}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 680 }}>
            <div className="modal-header">
              <h3>Subir varias fotos</h3>
              <button className="modal-close" onClick={cerrarLote}>✕</button>
            </div>

            <div className="modal-form">
              <p className="modal-helper">
                Persona seleccionada: <strong>{modalLote.nombre}</strong>
              </p>
              <p className="modal-helper">
                Sube varias fotos con diferentes angulos e iluminacion. El sistema procesara cada imagen por separado.
              </p>

              <button
                type="button"
                className="btn-primary"
                onClick={() => fotosMultiplesRef.current?.click()}
                disabled={subiendoFoto === modalLote.id_persona}
              >
                {loteArchivos.length > 0 ? 'Agregar más fotos' : 'Seleccionar fotos'}
              </button>

              <input
                type="file"
                ref={fotosMultiplesRef}
                accept="image/*"
                multiple
                onChange={handleSeleccionarLote}
                className="input-multifoto"
                style={{ display: 'none' }}
              />

              <div className="modal-actions">
                <button type="button" className="btn-secondary" onClick={cerrarLote}>Cancelar</button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => subirLote(false)}
                  disabled={!loteArchivos.length || subiendoFoto === modalLote.id_persona}
                >
                  {subiendoFoto === modalLote.id_persona ? 'Subiendo...' : `Subir ${loteArchivos.length || ''}`}
                </button>
              </div>

              {loteArchivos.length > 0 && (
                <div style={{ marginTop: 8, fontSize: 13, color: 'var(--texto-suave)' }}>
                  {loteArchivos.length} archivo{loteArchivos.length === 1 ? '' : 's'} seleccionado{loteArchivos.length === 1 ? '' : 's'}:
                  <div className="lote-preview-grid">
                    {loteArchivos.map((item, idx) => (
                      <div key={`${item.file.name}-${idx}`} className="lote-preview-card">
                        <img src={item.preview} alt={item.file.name} className="lote-preview-img" />
                        <div className="lote-preview-name" title={item.file.name}>{item.file.name}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {loteInfo && (
                <div className="lote-resumen">
                  <div className="lote-kpis">
                    <span><strong>{loteInfo.exitosas ?? 0}</strong> exitosas</span>
                    <span><strong>{loteInfo.fallidas ?? 0}</strong> fallidas</span>
                    <span><strong>{loteInfo.total_recibidas ?? 0}</strong> recibidas</span>
                  </div>

                  <div className="lote-lista">
                    {(loteInfo.resultados || []).map((item, idx) => (
                      <div key={`${item.nombre_archivo}-${idx}`} className={`lote-item lote-${item.estado}`}>
                        <div className="lote-item-top">
                          <strong>{item.nombre_archivo}</strong>
                          <span>{item.estado}</span>
                        </div>
                        <div className="lote-item-detail">{item.detalle}</div>
                        {typeof item.similitud === 'number' && (
                          <div className="lote-item-detail">Similitud: {(item.similitud * 100).toFixed(1)}%</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {resultadoModal && resultadoEntrenamiento && (
        <div className="modal-overlay" onClick={() => setResultadoModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 560 }}>
            <div className="modal-header">
              <h3>Resultado del entrenamiento</h3>
              <button className="modal-close" onClick={() => setResultadoModal(false)}>✕</button>
            </div>

            <div style={{ padding: '20px 24px' }}>
              <p style={{ marginBottom: 8 }}>{resultadoEntrenamiento.mensaje || 'Entrenamiento finalizado'}</p>
              {resultadoEntrenamiento.traceback && (
                <details style={{ marginBottom: 8 }}>
                  <summary style={{ cursor: 'pointer' }}>Mostrar detalles del error</summary>
                  <pre style={{ whiteSpace: 'pre-wrap', maxHeight: 240, overflow: 'auto', background: 'var(--fondo-card2)', padding: 12, borderRadius: 6, marginTop: 8 }}>{resultadoEntrenamiento.traceback}</pre>
                </details>
              )}
              {resultadoEntrenamiento.error && (
                <div style={{ color: '#f1c40f', marginBottom: 8 }}>Error: {resultadoEntrenamiento.error}</div>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="kpi"><strong>{resultadoEntrenamiento.personas_entrenadas ?? '—'}</strong><div>Personas entrenadas</div></div>
                <div className="kpi"><strong>{resultadoEntrenamiento.total_embeddings ?? '—'}</strong><div>Total embeddings</div></div>
                <div className="kpi"><strong>{typeof resultadoEntrenamiento.accuracy === 'number' ? (resultadoEntrenamiento.accuracy * 100).toFixed(2) + '%' : '—'}</strong><div>Accuracy (CV)</div></div>
                <div className="kpi"><strong style={{ wordBreak: 'break-all' }}>{resultadoEntrenamiento.modelo_guardado_en ?? '—'}</strong><div>Ruta del modelo</div></div>
              </div>

              {Array.isArray(resultadoEntrenamiento.omitidos) && resultadoEntrenamiento.omitidos.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <strong>Omitidos:</strong>
                  <ul>
                    {resultadoEntrenamiento.omitidos.map((o, idx) => <li key={idx}>{o}</li>)}
                  </ul>
                </div>
              )}

              <div style={{ marginTop: 18, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ fontSize: 12, color: 'var(--texto-suave)' }}>
                  {resultadoEntrenamiento.timestamp ? `Finalizado: ${new Date(resultadoEntrenamiento.timestamp * 1000).toLocaleString()}` : ''}
                  {resultadoEntrenamiento.duration_seconds ? ` · Duración: ${resultadoEntrenamiento.duration_seconds}s` : ''}
                </div>
                <div>
                  <button className="btn-secondary" onClick={() => setResultadoModal(false)}>Cerrar</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}