import { useState } from 'react'
import { getReporte } from '../services/api'
import './Reportes.css'

const HOY    = new Date().toISOString().slice(0, 10)
const HACE30 = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)

export default function Reportes() {
  const [eventos, setEventos] = useState([])
  const [cargando, setCargando] = useState(false)
  const [generado, setGenerado] = useState(false)
  const [filtros, setFiltros] = useState({
    fecha_desde: HACE30, fecha_hasta: HOY,
    tipo: 'Todos', id_camara: '', limit: 500,
  })

  const handleChange = (e) => setFiltros(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleGenerar = async () => {
    setCargando(true); setGenerado(false)
    try {
      const params = { limit: filtros.limit }
      if (filtros.tipo !== 'Todos') params.tipo = filtros.tipo
      if (filtros.id_camara) params.id_camara = parseInt(filtros.id_camara)
      const r = await getReporte(params)
      const filtrados = r.data.filter(ev => {
        if (!ev.fecha) return true
        return ev.fecha >= filtros.fecha_desde && ev.fecha <= filtros.fecha_hasta
      })
      setEventos(filtrados); setGenerado(true)
    } catch {}
    finally { setCargando(false) }
  }

  const exportarCSV = () => {
    const enc  = ['ID Evento','Tipo Acceso','Fecha','Hora','ID Camara','ID Persona','Similitud']
    const filas = eventos.map(ev => [
      ev.id_evento, ev.tipo_acceso, ev.fecha || '', ev.hora || '',
      ev.id_camara ?? '', ev.id_persona ?? '',
      ev.similitud != null ? (ev.similitud * 100).toFixed(2) + '%' : '',
    ])
    const csv  = [enc, ...filas].map(f => f.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = `reporte_vescom_${filtros.fecha_desde}_${filtros.fecha_hasta}.csv`
    a.click(); URL.revokeObjectURL(url)
  }

  const total  = eventos.length
  const noAuth = eventos.filter(e => e.tipo_acceso === 'No Autorizado').length
  const auth   = eventos.filter(e => e.tipo_acceso === 'Autorizado').length

  return (
    <div className="reportes-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Reportes</h1>
          <p className="page-sub">Historial exportable de accesos · ESCOM-IPN</p>
        </div>
      </div>

      <div className="filtros-card">
        <h2 className="filtros-titulo">Parámetros del reporte</h2>
        <div className="filtros-grid">
          <div className="field">
            <label>Fecha desde</label>
            <input type="date" name="fecha_desde" value={filtros.fecha_desde} onChange={handleChange} />
          </div>
          <div className="field">
            <label>Fecha hasta</label>
            <input type="date" name="fecha_hasta" value={filtros.fecha_hasta} onChange={handleChange} />
          </div>
          <div className="field">
            <label>Tipo de acceso</label>
            <select name="tipo" value={filtros.tipo} onChange={handleChange}>
              <option value="Todos">Todos</option>
              <option value="Autorizado">Autorizado</option>
              <option value="No Autorizado">No Autorizado</option>
            </select>
          </div>
          <div className="field">
            <label>ID Cámara (opcional)</label>
            <input type="number" name="id_camara" value={filtros.id_camara} onChange={handleChange} placeholder="Todas las cámaras" />
          </div>
          <div className="field">
            <label>Máximo de registros</label>
            <select name="limit" value={filtros.limit} onChange={handleChange}>
              <option value={100}>100</option>
              <option value={250}>250</option>
              <option value={500}>500</option>
            </select>
          </div>
        </div>
        <div className="filtros-acciones">
          <button className="btn-primary" onClick={handleGenerar} disabled={cargando}>
            {cargando ? 'Generando...' : '⊕ Generar reporte'}
          </button>
          {generado && eventos.length > 0 && (
            <button className="btn-export" onClick={exportarCSV}>↓ Exportar CSV</button>
          )}
        </div>
      </div>

      {generado && (
        <>
          <div className="rep-stats">
            <div className="rep-stat">
              <span className="rep-stat-val">{total}</span>
              <span className="rep-stat-label">Registros encontrados</span>
            </div>
            <div className="rep-stat rep-stat-ok">
              <span className="rep-stat-val">{auth}</span>
              <span className="rep-stat-label">Autorizados</span>
            </div>
            <div className="rep-stat rep-stat-alerta">
              <span className="rep-stat-val">{noAuth}</span>
              <span className="rep-stat-label">No autorizados</span>
            </div>
            <div className="rep-stat">
              <span className="rep-stat-val">{total > 0 ? `${((auth/total)*100).toFixed(0)}%` : '—'}</span>
              <span className="rep-stat-label">Tasa de autorización</span>
            </div>
          </div>

          <div className="tabla-wrap">
            {eventos.length === 0 ? (
              <div className="tabla-vacia">No se encontraron registros con estos filtros</div>
            ) : (
              <table className="tabla">
                <thead>
                  <tr>
                    <th># Evento</th><th>Tipo</th><th>Fecha</th>
                    <th>Hora</th><th>Cámara</th><th>Persona</th><th>Similitud</th>
                  </tr>
                </thead>
                <tbody>
                  {eventos.map(ev => (
                    <tr key={ev.id_evento}>
                      <td className="mono td-muted">#{ev.id_evento}</td>
                      <td>
                        <span className={`tipo-badge ${ev.tipo_acceso === 'Autorizado' ? 'tipo-ok' : 'tipo-alerta'}`}>
                          {ev.tipo_acceso === 'Autorizado' ? '✓' : '⚠'} {ev.tipo_acceso}
                        </span>
                      </td>
                      <td className="mono">{ev.fecha || '—'}</td>
                      <td className="mono td-muted">{ev.hora?.slice(0,8) || '—'}</td>
                      <td className="mono td-muted">{ev.id_camara ?? '—'}</td>
                      <td className="td-muted">{ev.id_persona ?? 'Desconocido'}</td>
                      <td>
                        {ev.similitud != null ? (
                          <div className="sim-wrap">
                            <div className="sim-bar">
                              <div
                                className={`sim-fill ${ev.tipo_acceso === 'Autorizado' ? 'sim-ok' : 'sim-no'}`}
                                style={{ width: `${Math.min(ev.similitud*100,100)}%` }}
                              />
                            </div>
                            <span className="mono sim-val">{(ev.similitud*100).toFixed(1)}%</span>
                          </div>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {!generado && !cargando && (
        <div className="rep-placeholder">
          <div className="rep-placeholder-icon">◎</div>
          <p>Configura los filtros y haz clic en <strong>Generar reporte</strong></p>
        </div>
      )}
    </div>
  )
}