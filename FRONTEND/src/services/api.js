import axios from 'axios'

const BASE = '/api'
const api = axios.create({ baseURL: BASE })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('vescom_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('vescom_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const login = (email, contrasena) => {
  const form = new URLSearchParams()
  form.append('username', email)
  form.append('password', contrasena)
  return api.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  })
}

export const getPerfil = () => api.get('/auth/admins/me')

export const getPersonas = () => api.get('/reconocimiento/personas')
export const getPersona = (id) => api.get(`/reconocimiento/personas/${id}`)
export const crearPersona = (datos) => api.post('/reconocimiento/personas', datos)
export const actualizarPersona = (id, datos) => api.put(`/reconocimiento/personas/${id}`, datos)
export const eliminarPersona = (id) => api.delete(`/reconocimiento/personas/${id}`)
export const subirRostro = (id, file) => {
  const form = new FormData()
  form.append('imagen', file)
  return api.post(`/reconocimiento/personas/${id}/rostro`, form)
}

export const identificarRostro = (file, id_camara) => {
  const form = new FormData()
  form.append('imagen', file)
  if (id_camara) form.append('id_camara', id_camara)
  return api.post('/reconocimiento/identificar', form)
}

export const getEventos = (params) => api.get('/reconocimiento/eventos', { params })
export const getCamaras = () => api.get('/camaras/')

// ── Cámaras CRUD ─────────────────────────────────────────────────
export const crearCamara      = (datos)     => api.post('/camaras/', datos)
export const actualizarCamara = (id, datos) => api.put(`/camaras/id_camara?id_camara=${id}`, datos)
export const desactivarCamara = (id)        => api.delete(`/camaras/id_camara?id_camara=${id}`)

// ── Alertas ───────────────────────────────────────────────────────
export const getAlertas       = (params)    => api.get('/alertas/', { params })
export const actualizarAlerta = (id, datos) => api.put(`/alertas/${id}`, datos)

// ── Administradores ───────────────────────────────────────────────
export const getAdmins        = ()          => api.get('/auth/admins')
export const crearAdmin       = (datos)     => api.post('/auth/admins', datos)
export const actualizarAdmin  = (id, datos) => api.put(`/auth/admins/${id}`, datos)
export const desactivarAdmin  = (id)        => api.delete(`/auth/admins/${id}`)

// ── Reportes ──────────────────────────────────────────────────────
export const getReporte = (params) => api.get('/reconocimiento/eventos', { params })