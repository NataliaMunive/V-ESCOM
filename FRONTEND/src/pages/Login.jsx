import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { login, getPerfil } from '../services/api'
import './Login.css'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)
  const { guardarSesion } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setCargando(true)
    try {
      const res = await login(email, password)
      const token = res.data.access_token
      localStorage.setItem('vescom_token', token)
      const perfil = await getPerfil()
      guardarSesion(token, perfil.data)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al iniciar sesión')
    } finally {
      setCargando(false)
    }
  }

  return (
    <div className="login-page">
      {/* Decoración de fondo */}
      <div className="login-bg">
        <div className="grid-overlay" />
        <div className="scanline" />
      </div>

      {/* Panel izquierdo */}
      <div className="login-left">
        <div className="login-brand">
          <div className="brand-logo">V</div>
          <div>
            <h1 className="brand-nombre">V-ESCOM</h1>
            <p className="brand-desc">Sistema de Vigilancia con Reconocimiento Facial</p>
          </div>
        </div>
        <div className="login-feature-list">
          <div className="feature-item">
            <span className="feature-dot" />
            Detección facial en tiempo real con ArcFace
          </div>
          <div className="feature-item">
            <span className="feature-dot" />
            Alertas automáticas ante intrusos
          </div>
          <div className="feature-item">
            <span className="feature-dot" />
            Historial completo de accesos
          </div>
          <div className="feature-item">
            <span className="feature-dot" />
            Gestión de cubículos y personas autorizadas
          </div>
        </div>
        <div className="login-institution">
          <span>Instituto Politécnico Nacional</span>
          <span className="sep">·</span>
          <span>ESCOM</span>
        </div>
      </div>

      {/* Formulario */}
      <div className="login-right">
        <div className="login-card">
          <div className="login-card-header">
            <h2>Acceso al sistema</h2>
            <p>Solo administradores autorizados</p>
          </div>

          <form onSubmit={handleSubmit} className="login-form">
            <div className="field">
              <label>Correo institucional</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="admin@escom.ipn.mx"
                required
                autoComplete="email"
              />
            </div>

            <div className="field">
              <label>Contraseña</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete="current-password"
              />
            </div>

            {error && (
              <div className="login-error">
                <span>⚠</span> {error}
              </div>
            )}

            <button type="submit" className="btn-login" disabled={cargando}>
              {cargando ? (
                <span className="btn-loading">Autenticando<span className="dots">...</span></span>
              ) : (
                'Iniciar sesión'
              )}
            </button>
          </form>

          <div className="login-card-footer">
            <span className="mono">ESCOM-IPN · 2026-A023</span>
          </div>
        </div>
      </div>
    </div>
  )
}