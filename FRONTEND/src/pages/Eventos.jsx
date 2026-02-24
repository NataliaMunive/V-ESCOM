import { useState, useEffect } from 'react'
import { getEventos } from '../services/api'
import './Eventos.css'

const FILTROS = ['Todos', 'Autorizado', 'No Autorizado']

export default function Eventos() {
  const [eventos, setEventos] = useState([])
  const [cargando, setCargando] = useState(true)
  const [filtro, setFiltro] = useState('Todos')
  const [limite, setLimite] = useState(50)

  useEffect(() => { cargar() }, [filtro, limite])

  const cargar = async () => {
    setCargando(true)
    try {
      const params = { limit: limite }
      if (filtro !== 'Todos') params.tipo = filtro
      const res = await getEventos(params)
      setEventos(res.data)
    } catch {}
    finally { setCargando(false) }
  }

  const totalAuth = eventos.filter(e => e.tipo_acceso === 'Autorizado').length
  const totalNoAuth = eventos.filter(e => e.tipo_acceso === 'No Autorizado').length

  return (
    <div className="eventos-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Historial de Eventos</h1>
          <p className="page-sub">{eventos.length} eventos · últimos registros</p>
        </div>
      </div>

      {/* Stats rápidas */}
      <div className="ev-stats">
        <div className="ev-stat">
          <span className="ev-stat-val">{eventos.length}</span>
          <span className="ev-stat-label">Total</span>
        </div>
        <div className="ev-stat ev-stat-ok">
          <span className="ev-stat-val">{totalAuth}</span>
          <span className="ev-stat-label">Autorizados</span>
        </div>
        <div className="ev-stat ev-stat-alerta">
          <span className="ev-stat-val">{totalNoAuth}</span>
          <span className="ev-stat-label">No autorizados</span>
        </div>
        <div className="ev-stat">
          <span className="ev-stat-val">
            {eventos.length > 0
              ? `${((totalAuth / eventos.length) * 100).toFixed(0)}%`
              : '—'}
          </span>
          <span className="ev-stat-label">Tasa de acceso</span>
        </div>
      </div>

      {/* Controles */}
      <div className="ev-controles">
        <div className="filtros-grupo">
          {FILTROS.map(f => (
            <button
              key={f}
              className={`filtro-btn ${filtro === f ? 'activo' : ''}`}
              onClick={() => setFiltro(f)}
            >
              {f}
            </button>
          ))}
        </div>
        <select
          className="limite-select"
          value={limite}
          onChange={e => setLimite(Number(e.target.value))}
        >
          <option value={25}>Últimos 25</option>
          <option value={50}>Últimos 50</option>
          <option value={100}>Últimos 100</option>
          <option value={500}>Últimos 500</option>
        </select>
      </div>

      {/* Tabla */}
      <div className="tabla-wrap">
        {cargando ? (
          <div className="tabla-cargando">Cargando eventos...</div>
        ) : eventos.length === 0 ? (
          <div className="tabla-vacia">No hay eventos con este filtro</div>
        ) : (
          <table className="tabla">
            <thead>
              <tr>
                <th># Evento</th>
                <th>Tipo</th>
                <th>Fecha</th>
                <th>Hora</th>
                <th>Cámara</th>
                <th>Persona</th>
                <th>Similitud</th>
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
                  <td className="mono td-muted">{ev.hora?.slice(0, 8) || '—'}</td>
                  <td className="mono td-muted">{ev.id_camara ?? '—'}</td>
                  <td className="td-muted">{ev.id_persona ?? 'Desconocido'}</td>
                  <td>
                    {ev.similitud != null ? (
                      <div className="similitud-wrap">
                        <div className="similitud-bar">
                          <div
                            className={`similitud-fill ${ev.similitud >= 0.4 ? 'fill-ok' : 'fill-no'}`}
                            style={{ width: `${Math.min(ev.similitud * 100, 100)}%` }}
                          />
                        </div>
                        <span className="mono similitud-val">
                          {(ev.similitud * 100).toFixed(1)}%
                        </span>
                      </div>
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}