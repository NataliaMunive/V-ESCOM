import { useState, useEffect } from 'react'
import { getEventos } from '../services/api'
import './Alertas.css'

const ESTADOS = ['Todos', 'No Autorizado']

export default function Alertas() {
  const [alertas, setAlertas] = useState([])
  const [cargando, setCargando] = useState(true)
  const [filtro, setFiltro] = useState('Todos')
  const [limite, setLimite] = useState(50)

  useEffect(() => { cargar() }, [filtro, limite])

  const cargar = async () => {
    setCargando(true)
    try {
      const params = { limit: limite }
      if (filtro === 'No Autorizado') params.tipo = 'No Autorizado'
      const r = await getEventos(params)
      setAlertas(r.data)
    } catch {}
    finally { setCargando(false) }
  }

  const total      = alertas.length
  const noAuth     = alertas.filter(a => a.tipo_acceso === 'No Autorizado').length
  const auth       = alertas.filter(a => a.tipo_acceso === 'Autorizado').length
  const porcentaje = total > 0 ? ((noAuth / total) * 100).toFixed(0) : 0

  const getNivel = (similitud) => {
    if (similitud === null || similitud === undefined) return { label: '—', cls: '' }
    if (similitud < 0.2)  return { label: 'Alto riesgo',  cls: 'nivel-alto' }
    if (similitud < 0.35) return { label: 'Riesgo medio', cls: 'nivel-medio' }
    return { label: 'Bajo riesgo', cls: 'nivel-bajo' }
  }

  return (
    <div className="alertas-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Alertas y Detecciones</h1>
          <p className="page-sub">Registro de eventos de acceso · ESCOM-IPN</p>
        </div>
      </div>

      <div className="al-stats">
        <div className="al-stat">
          <span className="al-stat-val">{total}</span>
          <span className="al-stat-label">Total eventos</span>
        </div>
        <div className="al-stat al-stat-alerta">
          <span className="al-stat-val">{noAuth}</span>
          <span className="al-stat-label">No autorizados</span>
        </div>
        <div className="al-stat al-stat-ok">
          <span className="al-stat-val">{auth}</span>
          <span className="al-stat-label">Autorizados</span>
        </div>
        <div className="al-stat al-stat-porc">
          <span className="al-stat-val">{porcentaje}%</span>
          <span className="al-stat-label">Tasa de intrusión</span>
        </div>
      </div>

      <div className="al-controles">
        <div className="filtros-grupo">
          {ESTADOS.map(f => (
            <button
              key={f}
              className={`filtro-btn ${filtro === f ? 'activo' : ''}`}
              onClick={() => setFiltro(f)}
            >
              {f}
            </button>
          ))}
        </div>
        <select className="limite-select" value={limite} onChange={e => setLimite(Number(e.target.value))}>
          <option value={25}>Últimos 25</option>
          <option value={50}>Últimos 50</option>
          <option value={100}>Últimos 100</option>
        </select>
      </div>

      {cargando ? (
        <div className="tabla-cargando">Cargando alertas...</div>
      ) : alertas.length === 0 ? (
        <div className="tabla-vacia">Sin alertas registradas</div>
      ) : (
        <div className="alertas-lista">
          {alertas.map(a => {
            const nivel    = getNivel(a.similitud)
            const esAlerta = a.tipo_acceso === 'No Autorizado'
            return (
              <div key={a.id_evento} className={`alerta-row ${esAlerta ? 'alerta-row-danger' : 'alerta-row-ok'}`}>
                <div className={`alerta-icono ${esAlerta ? 'icono-danger' : 'icono-ok'}`}>
                  {esAlerta ? '⚠' : '✓'}
                </div>
                <div className="alerta-info">
                  <div className="alerta-tipo">{a.tipo_acceso}</div>
                  <div className="alerta-meta mono">
                    {a.fecha} {a.hora?.slice(0, 8)} · Cámara {a.id_camara ?? '—'} · Evento #{a.id_evento}
                  </div>
                </div>
                {esAlerta && (
                  <span className={`nivel-badge ${nivel.cls}`}>{nivel.label}</span>
                )}
                <div className="alerta-sim">
                  {a.similitud != null ? (
                    <>
                      <div className="sim-bar">
                        <div
                          className={`sim-fill ${a.tipo_acceso === 'Autorizado' ? 'sim-ok' : 'sim-no'}`}
                          style={{ width: `${Math.min(a.similitud * 100, 100)}%` }}
                        />
                      </div>
                      <span className="mono sim-val">{(a.similitud * 100).toFixed(1)}%</span>
                    </>
                  ) : <span className="mono sim-val">—</span>}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}