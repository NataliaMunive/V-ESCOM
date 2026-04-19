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

export default api

export const login = (email, contrasena) => {
  const form = new URLSearchParams()
  form.append('username', email)
  form.append('password', contrasena)
  return api.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  })
}

export const getPerfil = () => api.get('/auth/admins/me')

// ── Personas ──────────────────────────────────────────────────────
export const getPersonas      = ()          => api.get('/reconocimiento/personas')
export const getPersona       = (id)        => api.get(`/reconocimiento/personas/${id}`)
export const crearPersona     = (datos)     => api.post('/reconocimiento/personas', datos)
export const actualizarPersona = (id, datos) => api.put(`/reconocimiento/personas/${id}`, datos)
export const eliminarPersona  = (id)        => api.delete(`/reconocimiento/personas/${id}`)
export const subirRostro      = (id, file, forzar = false) => {
  const form = new FormData()
  form.append('imagen', file)
  const url = forzar
    ? `/reconocimiento/personas/${id}/rostro?forzar=true`
    : `/reconocimiento/personas/${id}/rostro`
  return api.post(url, form)
}

export const identificarRostro = (file, id_camara) => {
  const form = new FormData()
  form.append('imagen', file)
  if (id_camara) form.append('id_camara', id_camara)
  return api.post('/reconocimiento/identificar', form)
}

// ── Eventos ───────────────────────────────────────────────────────
export const getEventos = (params) => api.get('/reconocimiento/eventos', { params })

// ── Cámaras CRUD ──────────────────────────────────────────────────
export const getCamaras       = ()          => api.get('/camaras/')
export const crearCamara      = (datos)     => api.post('/camaras/', datos)
export const actualizarCamara = (id, datos) => api.put(`/camaras/${id}`, datos)
export const desactivarCamara = (id)        => api.delete(`/camaras/${id}`)

// ── Stream / Monitoreo ────────────────────────────────────────────
export const iniciarStream    = (id, intervalo = 3) =>
  api.post(`/stream/${id}/iniciar?intervalo=${intervalo}`)
export const detenerStream    = (id) => api.post(`/stream/${id}/detener`)
export const getStreamsActivos = ()  => api.get('/stream/activas')
export const getEstadoStream  = (id) => api.get(`/stream/estado/${id}`)

// ── Alertas ───────────────────────────────────────────────────────
export const getAlertas       = (params)    => api.get('/alertas/', { params })
export const actualizarAlerta = (id, datos) => api.put(`/alertas/${id}`, datos)

// ── Administradores ───────────────────────────────────────────────
export const getAdmins        = ()          => api.get('/auth/admins')
export const crearAdmin       = (datos)     => api.post('/auth/admins', datos)
export const actualizarAdmin  = (id, datos) => api.put(`/auth/admins/${id}`, datos)
export const desactivarAdmin  = (id)        => api.delete(`/auth/admins/${id}`)

// ── Reportes ──────────────────────────────────────────────────────
export const getReporte  = (params) => api.get('/reconocimiento/eventos', { params })
export const exportarPDF = (params) => api.get('/reportes/pdf', { params, responseType: 'blob' })

// ── Profesores ────────────────────────────────────────────────────
export const getProfesores      = ()          => api.get('/profesores/')
export const crearProfesor      = (datos)     => api.post('/profesores/', datos)
export const actualizarProfesor = (id, datos) => api.put(`/profesores/${id}`, datos)
export const desactivarProfesor = (id)        => api.delete(`/profesores/${id}`)

// ── Cubículos CRUD ────────────────────────────────────────────────
export const getCubiculos       = ()          => api.get('/cubiculos/')
export const crearCubiculo      = (datos)     => api.post('/cubiculos/', datos)
export const actualizarCubiculo = (id, datos) => api.put(`/cubiculos/${id}`, datos)
export const eliminarCubiculo   = (id)        => api.delete(`/cubiculos/${id}`)