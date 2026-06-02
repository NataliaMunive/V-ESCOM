// Utilidades para enmascarar correo y teléfono para mostrar en UI
export function maskEmail(email) {
  if (!email) return '—'
  const parts = String(email).split('@')
  if (parts.length !== 2) return email
  const [local, domain] = parts
  if (!local) return `****@${domain}`
  const start = local.slice(0, 1)
  const end = local.length > 2 ? local.slice(-2) : local.slice(1)
  return `${start}****${end}@${domain}`
}

export function maskPhone(phone) {
  if (!phone) return '—'
  const s = String(phone).trim()
  const hasPlus = s.startsWith('+')
  const digits = s.replace(/\D/g, '')
  if (!digits) return s
  // Mostrar los primeros 6 dígitos (si existen) y ocultar el resto
  if (digits.length <= 6) return (hasPlus ? '+' : '') + digits
  const visible = digits.slice(0, 6)
  return (hasPlus ? '+' : '') + visible + ' ****'
}

export default { maskEmail, maskPhone }
