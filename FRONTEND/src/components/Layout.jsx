import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import './Layout.css'

const navItems = [
  { to: '/dashboard',       label: 'Dashboard',        icon: '◈' },
  { to: '/personas',        label: 'Personas',         icon: '◉' },
  { to: '/camaras',         label: 'Cámaras',          icon: '⊞' },
  { to: '/alertas',         label: 'Alertas',          icon: '⚠' },
  { to: '/eventos',         label: 'Eventos',          icon: '◎' },
  { to: '/reportes',        label: 'Reportes',         icon: '≡' },
  { to: '/administradores', label: 'Administradores',  icon: '⊛' },
]

export default function Layout() {
  const { admin, cerrarSesion } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => { cerrarSesion(); navigate('/login') }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <span className="logo-mark">V</span>
          <div className="logo-text">
            <span className="logo-title">ESCOM</span>
            <span className="logo-sub">Sistema de Vigilancia</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="admin-info">
            <div className="admin-avatar">
              {admin?.nombre?.[0]?.toUpperCase() || 'A'}
            </div>
            <div className="admin-datos">
              <span className="admin-nombre">{admin?.nombre} {admin?.apellidos}</span>
              <span className="admin-rol">Administrador</span>
            </div>
          </div>
          <button className="btn-logout" onClick={handleLogout} title="Cerrar sesión">
            ⏻
          </button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}