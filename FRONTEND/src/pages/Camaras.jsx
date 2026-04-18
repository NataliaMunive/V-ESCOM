import { useState, useEffect } from 'react'
import { getCamaras, crearCamara, actualizarCamara, desactivarCamara, getCubiculos } from '../services/api'
import './Camaras.css'

const FORM_VACIO = {
  nombre: '',
  direccion_ip: '',
  ubicacion: '',
  id_cubiculo: '',
  activa: true,
  estado: 'Activa',
}

const construirStreams = (ip) => {
  if (!ip) return []
  return [
    `http://${ip}:8080/video`,
    `http://${ip}/video`,
    `http://${ip}:81/stream`,
    `http://${ip}/mjpeg`,
    `http://${ip}:4747/video`,
    `http://${ip}:5000/video_feed`,
  ]
}

export default function Camaras() {
  const [camaras, setCamaras] = useState([])
  const [cargando, setCargando] = useState(true)
  const [modal, setModal] = useState(null)
  const [seleccionada, setSeleccionada] = useState(null)
  const [form, setForm] = useState(FORM_VACIO)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState('')
  const [cubiculos, setCubiculos] = useState([])
  const [busqueda, setBusqueda] = useState('')
  const [camaraLive, setCamaraLive] = useState(null)
  const [streamUrl, setStreamUrl] = useState('')
  const [streamCandidatos, setStreamCandidatos] = useState([])
  const [streamIndex, setStreamIndex] = useState(0)
  const [errorStream, setErrorStream] = useState('')

  useEffect(() => { cargar(); cargarCubiculos() }, [])

  const cargar = async () => {
    setCargando(true)
    try { const r = await getCamaras(); setCamaras(r.data) }
    catch {}
    finally { setCargando(false) }
  }

  const cargarCubiculos = async () => {
    try {
      const r = await getCubiculos()
      setCubiculos(r.data || [])
    } catch {
      setCubiculos([])
    }
  }

  const abrirCrear = () => { setForm(FORM_VACIO); setError(''); setModal('crear') }

  const abrirEditar = (c) => {
    setSeleccionada(c)
    setForm({
      nombre: c.nombre || '',
      direccion_ip: c.direccion_ip || '',
      ubicacion: c.ubicacion || '',
      id_cubiculo: c.id_cubiculo || '',
      activa: c.activa,
      estado: c.estado || (c.activa ? 'Activa' : 'Inactiva'),
    })
    setError(''); setModal('editar')
  }

  const abrirLive = (c) => {
    const candidatos = construirStreams(c.direccion_ip)
    setCamaraLive(c)
    setStreamCandidatos(candidatos)
    setStreamIndex(0)
    setStreamUrl(candidatos[0] || '')
    setErrorStream('')
    setModal('live')
  }

  const cerrar = () => {
    setModal(null)
    setSeleccionada(null)
    setCamaraLive(null)
    setError('')
    setErrorStream('')
  }

  const handleChange = (e) => {
    const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    setForm(f => ({ ...f, [e.target.name]: val }))
  }

  const handleGuardar = async (e) => {
    e.preventDefault(); setGuardando(true); setError('')
    try {
      const payload = {
        ...form,
        nombre: form.nombre.trim(),
        direccion_ip: form.direccion_ip?.trim() || null,
        ubicacion: form.ubicacion?.trim() || null,
        id_cubiculo: form.id_cubiculo ? parseInt(form.id_cubiculo) : null,
      }
      if (modal === 'crear') await crearCamara(payload)
      else await actualizarCamara(seleccionada.id_camara, payload)
      cerrar(); cargar()
    } catch (err) { setError(err.response?.data?.detail || 'Error al guardar') }
    finally { setGuardando(false) }
  }

  const handleErrorStream = () => {
    const next = streamIndex + 1
    if (next < streamCandidatos.length) {
      setStreamIndex(next)
      setStreamUrl(streamCandidatos[next])
      setErrorStream('')
      return
    }
    setErrorStream('No se pudo abrir el stream. Verifica IP, puerto, credenciales o formato (MJPEG/HLS).')
  }

  const exportarCSV = () => {
    const rows = [
      ['ID', 'Camara', 'Cubiculo', 'IP', 'Ubicacion', 'Estado'],
      ...filtradas.map((c) => [
        c.id_camara,
        c.nombre,
        obtenerNumeroCubiculo(c.id_cubiculo),
        c.direccion_ip || '',
        c.ubicacion || '',
        c.activa ? (c.estado || 'Activa') : 'Inactiva',
      ]),
    ]
    const csv = rows
      .map((row) => row.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))
      .join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'camaras.csv'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const obtenerNumeroCubiculo = (idCubiculo) => {
    const cubiculo = cubiculos.find((c) => c.id_cubiculo === idCubiculo)
    return cubiculo?.numero_cubiculo || idCubiculo || '—'
  }

  const handleDesactivar = async (c) => {
    if (!confirm(`¿Desactivar la cámara "${c.nombre}"?`)) return
    try { await desactivarCamara(c.id_camara); cargar() }
    catch (err) { alert(err.response?.data?.detail || 'Error al desactivar') }
  }

  const activas   = camaras.filter(c => c.activa).length
  const inactivas = camaras.filter(c => !c.activa).length
  const filtradas = camaras.filter((c) => {
    const q = busqueda.toLowerCase().trim()
    if (!q) return true
    return (
      String(c.id_camara).includes(q)
      || (c.nombre || '').toLowerCase().includes(q)
      || (c.direccion_ip || '').toLowerCase().includes(q)
      || String(obtenerNumeroCubiculo(c.id_cubiculo)).toLowerCase().includes(q)
    )
  })

  return (
    <div className="camaras-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Gestión de Cámaras</h1>
          <p className="page-sub">{camaras.length} cámaras registradas</p>
        </div>
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

      <div className="cam-toolbar">
        <input
          className="cam-search"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Buscar ID, nombre o IP..."
        />
        <button className="btn-secondary" onClick={exportarCSV}>Exportar registro</button>
        <button className="btn-primary" onClick={abrirCrear}>Agregar cámara</button>
        <button className="btn-secondary" onClick={cargar}>Actualizar estado</button>
      </div>

      {cargando ? (
        <div className="tabla-cargando">Cargando cámaras...</div>
      ) : filtradas.length === 0 ? (
        <div className="tabla-vacia">
          <p>No hay cámaras para este filtro</p>
          <button className="btn-primary" onClick={abrirCrear}>Registrar la primera</button>
        </div>
      ) : (
        <div className="tabla-wrap cam-table-wrap">
          <table className="tabla cam-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Cámara</th>
                <th>Cubículo</th>
                <th>Dirección IP</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtradas.map(c => (
                <tr key={c.id_camara}>
                  <td className="mono td-muted">{c.id_camara}</td>
                  <td>{c.nombre}</td>
                  <td>{obtenerNumeroCubiculo(c.id_cubiculo)}</td>
                  <td className="mono td-muted">{c.direccion_ip || '—'}</td>
                  <td>
                    <span className={`estado-badge ${c.activa ? 'estado-ok' : 'estado-off'}`}>
                      {c.activa ? (c.estado || 'Activa') : 'Inactiva'}
                    </span>
                  </td>
                  <td>
                    <div className="acciones">
                      <button className="btn-icono" type="button" title="Ver en vivo" aria-label="Ver en vivo" onClick={() => abrirLive(c)}>
                        <img src="/icons/ver.svg" alt="" />
                      </button>
                      <button className="btn-icono" type="button" title="Editar" aria-label="Editar" onClick={() => abrirEditar(c)}>
                        <img src="/icons/editar.svg" alt="" />
                      </button>
                      {c.activa && (
                        <button className="btn-icono btn-danger" type="button" title="Desactivar" aria-label="Desactivar" onClick={() => handleDesactivar(c)}>
                          <img src="/icons/desactivar.svg" alt="" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(modal === 'crear' || modal === 'editar') && (
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
                <label>Dirección IP</label>
                <input name="direccion_ip" value={form.direccion_ip} onChange={handleChange} placeholder="Ej. 192.168.1.110" />
              </div>
              <div className="field">
                <label>Ubicación</label>
                <input name="ubicacion" value={form.ubicacion} onChange={handleChange} placeholder="Ej. Pasillo 3er piso" />
              </div>
              <div className="field">
                <label>Cubículo *</label>
                <select name="id_cubiculo" value={form.id_cubiculo} onChange={handleChange} required>
                  <option value="">Selecciona un cubículo</option>
                  {cubiculos.map(c => (
                    <option key={c.id_cubiculo} value={c.id_cubiculo}>
                      {c.numero_cubiculo} (ID {c.id_cubiculo})
                    </option>
                  ))}
                </select>
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

      {modal === 'live' && (
        <div className="modal-overlay" onClick={cerrar}>
          <div className="modal modal-live" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Monitoreo en vivo: {camaraLive?.nombre}</h3>
              <button className="modal-close" onClick={cerrar}>✕</button>
            </div>
            <div className="live-wrap">
              <div className="live-meta">
                <span className="mono">IP: {camaraLive?.direccion_ip || 'No definida'}</span>
                <span className="mono">Cubículo: {obtenerNumeroCubiculo(camaraLive?.id_cubiculo)}</span>
              </div>

              {!streamUrl ? (
                <div className="form-error">Esta cámara no tiene IP configurada para abrir stream.</div>
              ) : (
                <img
                  key={streamUrl}
                  src={streamUrl}
                  alt={`Stream ${camaraLive?.nombre || ''}`}
                  className="live-preview"
                  onError={handleErrorStream}
                />
              )}

              <div className="live-tools">
                <input
                  value={streamUrl}
                  onChange={(e) => setStreamUrl(e.target.value)}
                  placeholder="URL de stream (http://ip:puerto/ruta)"
                />
                <button className="btn-secondary" onClick={() => setStreamUrl((s) => s ? `${s.split('?')[0]}?t=${Date.now()}` : s)}>
                  Recargar stream
                </button>
              </div>

              {errorStream && <div className="form-error">⚠ {errorStream}</div>}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}