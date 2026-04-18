import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Personas from './pages/Personas'
import Profesores from './pages/Profesores'
import Eventos from './pages/Eventos'
import Camaras from './pages/Camaras'
import Cubiculos from './pages/Cubiculos'
import Alertas from './pages/Alertas'
import Administradores from './pages/Administradores'
import Reportes from './pages/Reportes'
import Layout from './components/Layout'

function RutaProtegida({ children }) {
  const { admin, cargando } = useAuth()
  if (cargando) return <div className="cargando-global"><span>Cargando...</span></div>
  return admin ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={
            <RutaProtegida>
              <Layout />
            </RutaProtegida>
          }>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard"        element={<Dashboard />} />
            <Route path="personas"         element={<Personas />} />
            <Route path="profesores"       element={<Profesores />} />
            <Route path="cubiculos"        element={<Cubiculos />} />
            <Route path="eventos"          element={<Eventos />} />
            <Route path="camaras"          element={<Camaras />} />
            <Route path="alertas"          element={<Alertas />} />
            <Route path="administradores"  element={<Administradores />} />
            <Route path="reportes"         element={<Reportes />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}