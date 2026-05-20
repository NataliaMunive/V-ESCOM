import { useState } from 'react'
import './ModalPrivacidad.css'

export default function ModalPrivacidad({ onAceptar }) {
  const [tab, setTab] = useState('privacidad')
  const [checkedPriv, setCheckedPriv] = useState(false)
  const [checkedTerms, setCheckedTerms] = useState(false)

  const puedeAceptar = checkedPriv && checkedTerms

  return (
    <div className="mp-overlay">
      <div className="mp-modal">

        {/* ── Header ── */}
        <div className="mp-header">
          <div className="mp-header-brand">
            <div className="mp-logo">V</div>
            <div>
              <div className="mp-sistema">V-ESCOM · ESCOM-IPN</div>
              <div className="mp-titulo">Aviso de Privacidad y Términos de Uso</div>
            </div>
          </div>
          <div className="mp-version">v1.0 · 2026</div>
        </div>

        {/* ── Tabs ── */}
        <div className="mp-tabs">
          <button
            className={`mp-tab ${tab === 'privacidad' ? 'activo' : ''}`}
            onClick={() => setTab('privacidad')}
          >
            Aviso de Privacidad
          </button>
          <button
            className={`mp-tab ${tab === 'terminos' ? 'activo' : ''}`}
            onClick={() => setTab('terminos')}
          >
            Términos de Uso
          </button>
          <button
            className={`mp-tab ${tab === 'datos' ? 'activo' : ''}`}
            onClick={() => setTab('datos')}
          >
            Datos Sensibles
          </button>
        </div>

        {/* ── Contenido ── */}
        <div className="mp-body">

          {tab === 'privacidad' && (
            <div className="mp-content">
              <h2 className="mp-section-title">Responsable del Tratamiento</h2>
              <p>
                La <strong>Escuela Superior de Cómputo (ESCOM)</strong> del <strong>Instituto
                Politécnico Nacional (IPN)</strong> es responsable del tratamiento de sus datos
                personales a través del sistema V-ESCOM, conforme a la Ley Federal de Protección
                de Datos Personales en Posesión de los Particulares (LFPDPPP).
              </p>

              <h2 className="mp-section-title">Datos que Recabamos</h2>
              <div className="mp-table-wrap">
                <table className="mp-table">
                  <thead>
                    <tr>
                      <th>Categoría</th>
                      <th>Datos</th>
                      <th>Tipo</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><strong>Identidad</strong></td>
                      <td>Nombre completo, apellidos</td>
                      <td><span className="mp-badge info">General</span></td>
                    </tr>
                    <tr>
                      <td><strong>Contacto</strong></td>
                      <td>Correo institucional, teléfono</td>
                      <td><span className="mp-badge info">General</span></td>
                    </tr>
                    <tr>
                      <td><strong>Biométrico</strong></td>
                      <td>Fotografía de rostro, embedding facial (512-d)</td>
                      <td><span className="mp-badge danger">Sensible</span></td>
                    </tr>
                    <tr>
                      <td><strong>Acceso</strong></td>
                      <td>Eventos, fecha, hora, cámara, similitud</td>
                      <td><span className="mp-badge warn">Operativo</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <h2 className="mp-section-title">Finalidades del Tratamiento</h2>
              <ul className="mp-list">
                <li>Controlar el acceso físico a cubículos de la unidad ESCOM.</li>
                <li>Identificar en tiempo real a personas autorizadas mediante reconocimiento facial.</li>
                <li>Generar alertas y notificaciones SMS ante detecciones de personas no autorizadas.</li>
                <li>Mantener bitácora de eventos para fines de auditoría y seguridad institucional.</li>
              </ul>

              <h2 className="mp-section-title">Derechos ARCO</h2>
              <p>
                Usted tiene derecho a <strong>Acceder, Rectificar, Cancelar u Oponerse</strong> al
                tratamiento de sus datos. Para ejercer estos derechos envíe su solicitud a{' '}
                <strong>administracion@escom.ipn.mx</strong> adjuntando identificación oficial.
                Tiempo de respuesta: 20 días hábiles.
              </p>

              <h2 className="mp-section-title">Transferencia de Datos</h2>
              <p>
                El único tercero que recibe datos es <strong>Twilio Inc.</strong>, quien recibe
                exclusivamente el número telefónico del destinatario para el envío de alertas SMS.
                No se transfieren datos biométricos a ningún tercero.
              </p>
            </div>
          )}

          {tab === 'terminos' && (
            <div className="mp-content">
              <h2 className="mp-section-title">Acceso de Administradores</h2>
              <p>
                El acceso al sistema V-ESCOM está restringido a personal autorizado por ESCOM-IPN.
                Las credenciales son <strong>personales e intransferibles</strong>. El sistema
                aplica bloqueo temporal de 5 minutos tras 3 intentos fallidos consecutivos de
                autenticación.
              </p>

              <h2 className="mp-section-title">Uso Aceptable</h2>
              <ul className="mp-list">
                <li>El sistema debe usarse exclusivamente para control de acceso en cubículos de ESCOM.</li>
                <li>Queda <strong>prohibido</strong> registrar personas sin su consentimiento previo y expreso.</li>
                <li>Queda <strong>prohibido</strong> usar el sistema para vigilancia de actividades ajenas al control de acceso.</li>
                <li>Los administradores son responsables de mantener la confidencialidad de sus credenciales.</li>
                <li>Queda prohibido intentar eludir los mecanismos de autenticación o acceder a datos sin autorización.</li>
              </ul>

              <h2 className="mp-section-title">Limitación de Responsabilidad</h2>
              <div className="mp-alert warn">
                ESCOM-IPN no será responsable de errores de identificación inherentes a la
                tecnología de reconocimiento facial (falsos positivos o negativos). El sistema
                es una <strong>herramienta de apoyo</strong> y no reemplaza la supervisión humana.
              </div>

              <h2 className="mp-section-title">Seguridad</h2>
              <ul className="mp-list">
                <li>Contraseñas hasheadas con BCrypt (factor 12), sin almacenamiento en texto plano.</li>
                <li>Autenticación con JWT (HS256) con expiración de 60 minutos.</li>
                <li>Comunicación cifrada mediante HTTPS/WSS en producción.</li>
                <li>Variables de entorno sensibles excluidas del control de versiones.</li>
              </ul>

              <h2 className="mp-section-title">Retención de Datos</h2>
              <div className="mp-table-wrap">
                <table className="mp-table">
                  <thead>
                    <tr><th>Dato</th><th>Período de Retención</th></tr>
                  </thead>
                  <tbody>
                    <tr><td>Embeddings y fotografías de personas autorizadas</td><td>Vigencia del registro o solicitud ARCO</td></tr>
                    <tr><td>Imágenes de intrusos</td><td>Máximo 90 días</td></tr>
                    <tr><td>Eventos de acceso y alertas</td><td>Mínimo 1 año</td></tr>
                    <tr><td>Logs del sistema</td><td>Mínimo 6 meses</td></tr>
                  </tbody>
                </table>
              </div>

              <h2 className="mp-section-title">Propiedad Intelectual</h2>
              <p>
                El software V-ESCOM, su código fuente, arquitectura y documentación son propiedad
                de los autores del proyecto académico y de ESCOM-IPN. Queda prohibida su
                reproducción o modificación sin autorización expresa.
              </p>
            </div>
          )}

          {tab === 'datos' && (
            <div className="mp-content">
              <div className="mp-alert danger">
                Los datos biométricos (fotografía e embeddings faciales) constituyen{' '}
                <strong>datos personales sensibles</strong> conforme al artículo 3, fracción VI
                de la LFPDPPP. Su tratamiento requiere <strong>consentimiento expreso</strong> del titular.
              </div>

              <h2 className="mp-section-title">¿Cómo se Procesan tus Datos Biométricos?</h2>
              <ul className="mp-list">
                <li>
                  La fotografía de referencia se captura <strong>una única vez</strong> de forma
                  manual por un administrador autorizado y se almacena en el servidor de ESCOM.
                </li>
                <li>
                  Mediante el modelo <strong>ArcFace (InsightFace)</strong> se genera un vector
                  numérico de <strong>512 dimensiones</strong> (embedding) que representa
                  matemáticamente los rasgos faciales. Este vector <strong>no permite
                  reconstruir la imagen original</strong>.
                </li>
                <li>
                  El embedding se almacena en la base de datos PostgreSQL con extensión pgvector,
                  protegida con credenciales de acceso restringido.
                </li>
                <li>
                  Durante vigilancia activa, el sistema calcula la <strong>similitud coseno</strong>{' '}
                  entre el embedding capturado y los registrados. Si la similitud supera{' '}
                  <strong>0.40</strong>, el acceso se clasifica como "Autorizado".
                </li>
                <li>
                  Los frames de personas no reconocidas se almacenan temporalmente en{' '}
                  <code>capturas_intrusos/</code> y su embedding se registra para análisis posterior.
                </li>
              </ul>

              <h2 className="mp-section-title">Consentimiento</h2>
              <div className="mp-alert success">
                <strong>El consentimiento es obligatorio.</strong> Ninguna persona será registrada
                en el sistema sin haber expresado su consentimiento libre, específico, informado
                e inequívoco. Los administradores tienen la obligación de informar a cada persona
                antes del registro biométrico.
              </div>

              <h2 className="mp-section-title">Marco Normativo</h2>
              <ul className="mp-list">
                <li>Ley Federal de Protección de Datos Personales en Posesión de los Particulares (LFPDPPP)</li>
                <li>Ley General de Protección de Datos Personales en Posesión de Sujetos Obligados (LGPDPPSO)</li>
                <li>Reglamento de la LFPDPPP</li>
                <li>Lineamientos del INAI sobre tratamiento de datos biométricos</li>
              </ul>

              <h2 className="mp-section-title">Contacto</h2>
              <div className="mp-contact-box">
                <div className="mp-contact-row">
                  <span className="mp-contact-label">Área responsable</span>
                  <span>Coordinación de Proyectos Académicos — ESCOM-IPN</span>
                </div>
                <div className="mp-contact-row">
                  <span className="mp-contact-label">Correo</span>
                  <span>administracion@escom.ipn.mx</span>
                </div>
                <div className="mp-contact-row">
                  <span className="mp-contact-label">Horario</span>
                  <span>Lunes a viernes, 9:00 – 18:00 hrs.</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Footer con checkboxes y botón ── */}
        <div className="mp-footer">
          <div className="mp-checks">
            <label className="mp-check-label">
              <input
                type="checkbox"
                checked={checkedPriv}
                onChange={e => setCheckedPriv(e.target.checked)}
              />
              <span>He leído y acepto el <strong>Aviso de Privacidad</strong> y el tratamiento de mis datos personales, incluyendo datos biométricos.</span>
            </label>
            <label className="mp-check-label">
              <input
                type="checkbox"
                checked={checkedTerms}
                onChange={e => setCheckedTerms(e.target.checked)}
              />
              <span>He leído y acepto los <strong>Términos y Condiciones</strong> de uso del sistema V-ESCOM.</span>
            </label>
          </div>
          <button
            className="mp-btn-aceptar"
            disabled={!puedeAceptar}
            onClick={onAceptar}
          >
            {puedeAceptar ? 'Continuar al sistema →' : 'Acepta ambas condiciones para continuar'}
          </button>
        </div>

      </div>
    </div>
  )
}