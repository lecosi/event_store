# Convenciones del frontend

Reglas que se siguen en `frontend/src` y cómo agregar una pantalla nueva respetándolas.
Para el mapa general de carpetas ver [frontend-architecture.md](frontend-architecture.md).

## Resumen

| Tema | Regla |
| --- | --- |
| Textos visibles | Siempre en español y siempre desde `i18n/es.ts`; nunca escritos dentro de un componente |
| Validación de formularios | Funciones puras en `utils/`; el backend sigue siendo la autoridad |
| Estilos | Un CSS Module por componente o página, con las variables de `styles/tokens.css` |
| Componentes compartidos | Se reutilizan `Button`, `Input`, `Fields`, `Toast`, ... antes de crear uno nuevo |
| Permisos | Se decide con funciones de `utils/permissions.ts`, no con comparaciones de rol sueltas |
| Pruebas | Cada `*.test.ts(x)` vive junto al archivo que cubre |

## Textos e i18n

Todo texto que el usuario ve vive en `i18n/es.ts`, agrupado por área (`common`, `nav`,
`auth`, `events`, `sessions`, `validators`, ...). El código lo consume así:

```tsx
import { es } from '../i18n'

<Button>{es.events.register}</Button>
```

- Los textos con valores variables son funciones: `es.events.spotsAvailable(libres, capacidad)`.
- Las etiquetas de estado y rol se obtienen con `statusLabel(status)` y `roleLabel(role)`
  de `i18n/index.ts`.
- Los nombres de campo mostrados en errores del backend están en `es.fields`.
- `es.*` y `messages.*` son el mismo objeto: `messages = locales['es']` en
  `i18n/index.ts`. Los componentes importan `es`; el cliente HTTP importa `messages`.
- Para agregar un idioma habría que crear otro archivo con la forma del tipo `Messages` y
  registrarlo en `locales` (`i18n/index.ts`). Hoy solo existe `es`.

Los identificadores del código (nombres de funciones, variables, rutas) van en inglés; solo
el texto visible va en español.

## Validaciones

Los formularios validan antes de enviar para dar respuesta inmediata. Estas validaciones
**copian** reglas del backend y pueden quedar desactualizadas: el backend siempre vuelve a
validar y su error se muestra traducido (ver "Cliente HTTP y errores en español" en
[frontend-architecture.md](frontend-architecture.md)).

| Archivo | Qué valida |
| --- | --- |
| `utils/validation.ts` | Correo, nombre completo, contraseña (`MIN_PASSWORD_LENGTH`) y confirmación de contraseña |
| `utils/eventValidation.ts` | Formulario de evento (`validateEventForm`) y de sesión (`validateSessionForm`): obligatorios, largos máximos, fechas, capacidad |
| `utils/speakerValidation.ts` | Formulario de ponente (`validateSpeakerForm`) |

Cada validador devuelve un mensaje de error o `null` cuando el valor es válido, y los
mensajes salen de `es.validators`. Si cambias un límite en el backend, actualiza la
constante correspondiente en estos archivos y su prueba.

Algunas reglas solo existen en el backend porque el frontend no tiene todos los datos
(por ejemplo, que dos sesiones del mismo usuario no se solapen). En esos casos la pantalla
muestra el error que devuelve el backend. Las reglas de negocio están en
[backend-domain-rules.md](backend-domain-rules.md).

## Estilos

- Cada componente o página tiene su `Nombre.module.css` al lado (`Button.tsx` y
  `Button.module.css`) y lo importa como `styles`. Las clases quedan acotadas al componente.
- Varios formularios comparten `components/Form.module.css`; las páginas comparten
  `pages/Pages.module.css` y las de autenticación `pages/AuthForm.module.css`.
- Colores, espacios, radios y sombras salen de las variables de `styles/tokens.css`
  (`var(--color-primary)`, `var(--space-3)`); no se escriben valores sueltos.

## Componentes compartidos

| Componente | Para qué sirve |
| --- | --- |
| `Button` | Botón con `variant` (`primary`, `secondary`, `danger`) y `loading` |
| `Input` | Campo de texto con etiqueta y mensaje de error accesible |
| `Select`, `TextArea` (`Fields.tsx`) | Lo mismo para listas desplegables y áreas de texto |
| `ErrorMessage` | Mensaje de error en bloque; no pinta nada si el mensaje es vacío |
| `Spinner` | Indicador de carga |
| `Toast` (`ToastContainer`) y `toast` de `store/toastStore.ts` | Avisos temporales de éxito o error: `toast.success('...')` |
| `StatusBadge` | Etiqueta con el estado del evento |
| `Pagination`, `SearchBar` | Paginación y búsqueda de los listados |

## Cómo agregar una pantalla nueva

Ejemplo: una página `/venues` que lista lugares.

1. **Tipos.** Agrega las interfaces de la respuesta en `types/index.ts`.
2. **API.** Crea `api/venues.ts` con una función por endpoint, usando `apiClient`
   (`api/client.ts`). Copia el estilo de `api/speakers.ts`. No manejes errores aquí: el
   interceptor ya los traduce.
3. **Textos.** Agrega un grupo `venues` en `i18n/es.ts` con todos los textos de la pantalla.
   Si el backend devuelve mensajes nuevos, agrégalos a `errors.known`.
4. **Estado.** Si varias pantallas comparten los datos, crea un store en `store/`
   (modelo: `store/eventStore.ts`). Si solo los usa una página, basta `useState`.
5. **Validación.** Si hay formulario, agrega las reglas en `utils/` y sus mensajes en
   `es.validators`.
6. **Página.** Crea `pages/VenuesPage.tsx` con `export default` (las rutas la cargan con
   `lazy`) y `pages/VenuesPage.module.css` si necesita estilos propios. Muestra `Spinner`,
   `ErrorMessage` y el contenido, como en `EventDetailPage.tsx`.
7. **Permisos.** Si la pantalla es por rol, agrega una función a `utils/permissions.ts` y
   úsala en la página (muestra un `ErrorMessage` si no alcanza) y en `Navbar.tsx` para
   ocultar el enlace.
8. **Ruta.** En `routes/index.tsx` declara el `lazy(() => import(...))` y la entrada de
   ruta. Si requiere sesión, ponla dentro del bloque de `ProtectedRoute`.
9. **Navegación.** Si debe tener enlace, agrégalo en `components/Navbar.tsx` con su texto
   en `es.nav`.
10. **Pruebas.** Agrega `VenuesPage.test.tsx` y las pruebas de los archivos nuevos. El
    umbral de cobertura está en [frontend-operations.md](frontend-operations.md).

Antes de abrir el cambio corre `npm run lint`, `npm run format:check`, `npm test` y
`npm run build` (detalle en [frontend-operations.md](frontend-operations.md)).
