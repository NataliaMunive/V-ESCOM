import { createContext, useContext, useState, useEffect } from 'react'
import { getPerfil } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [admin, setAdmin] = useState(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('vescom_token')
    if (!token) { setCargando(false); return }
    getPerfil()
      .then(r => setAdmin(r.data))
      .catch(() => localStorage.removeItem('vescom_token'))
      .finally(() => setCargando(false))
  }, [])

  const guardarSesion = (token, datos) => {
    localStorage.setItem('vescom_token', token)
    setAdmin(datos)
  }

  const cerrarSesion = () => {
    localStorage.removeItem('vescom_token')
    setAdmin(null)
  }

  return (
    <AuthContext.Provider value={{ admin, cargando, guardarSesion, cerrarSesion }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)