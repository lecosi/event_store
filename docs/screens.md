# Pantallas

Espacio reservado para capturas de pantalla de la aplicación. Las imágenes se agregan más
adelante; mientras tanto, cada sección contiene un marcador de texto plano. El texto de la
interfaz de la aplicación está en español.

## Cómo agregar una imagen

1. Toma la captura (un ancho de escritorio de unos 1280 px para las páginas, unos 390 px
   para las móviles) y guárdala como PNG en `docs/images/` con el nombre de archivo que
   indica el marcador de la sección, por ejemplo `docs/images/event-list.png`.
2. En este archivo, reemplaza todo el bloque `Captura pendiente` de esa sección por:

   ```markdown
   ![Event list with search and pagination](images/event-list.png)
   ```

3. Mantén el texto alternativo corto y descriptivo. No agregues el enlace a una imagen
   antes de que el archivo exista, para que no haya imágenes rotas.
4. No incluyas datos personales reales: usa el seed de demostración (ver
   [backend-operations.md](backend-operations.md#carga-inicial-de-datos-seed)).

## Índice

| Pantalla | Ruta | Archivo de imagen |
| --- | --- | --- |
| [Inicio de sesión](#inicio-de-sesión) | `/login` | `docs/images/login.png` |
| [Registro de cuenta](#registro-de-cuenta) | `/register` | `docs/images/register.png` |
| [Listado de eventos](#listado-de-eventos) | `/` | `docs/images/event-list.png` |
| [Detalle del evento](#detalle-del-evento) | `/events/:id` | `docs/images/event-detail.png` |
| [Detalle del evento, vista de gestión](#detalle-del-evento-vista-de-gestión) | `/events/:id` | `docs/images/event-detail-manage.png` |
| [Formulario de evento](#formulario-de-evento) | `/events/new` y `/events/:id/edit` | `docs/images/event-form.png` |
| [Formulario de ponente](#formulario-de-ponente) | `/speakers/new` | `docs/images/speaker-form.png` |
| [Mis eventos](#mis-eventos) | `/profile` | `docs/images/profile.png` |
| [Reportes](#reportes) | `/reports` | `docs/images/reports.png` |
| [Administración de usuarios](#administración-de-usuarios) | `/admin/users` | `docs/images/admin-users.png` |
| [Página no encontrada](#página-no-encontrada) | cualquier ruta desconocida (`*`) | `docs/images/not-found.png` |
| [Barra de navegación, anónimo](#barra-de-navegación-anónimo) | todas las páginas | `docs/images/navbar-anonymous.png` |
| [Barra de navegación, organizador](#barra-de-navegación-organizador) | todas las páginas | `docs/images/navbar-organizer.png` |
| [Móvil: listado de eventos](#móvil-listado-de-eventos) | `/` en ancho de teléfono | `docs/images/mobile-event-list.png` |
| [Móvil: detalle del evento](#móvil-detalle-del-evento) | `/events/:id` en ancho de teléfono | `docs/images/mobile-event-detail.png` |

## Inicio de sesión

**Ruta:** `/login`

Formulario de correo y contraseña. Público. Tras iniciar sesión devuelve al usuario a la página de la que venía.

> **Captura pendiente:** guarda la imagen como `docs/images/login.png` y reemplaza este bloque con `![Inicio de sesión](images/login.png)`.

## Registro de cuenta

**Ruta:** `/register`

Formulario de creación de cuenta (nombre, correo, contraseña y confirmación). Público. Las cuentas nuevas reciben el rol de organizador.

> **Captura pendiente:** guarda la imagen como `docs/images/register.png` y reemplaza este bloque con `![Registro de cuenta](images/register.png)`.

## Listado de eventos

**Ruta:** `/`

Cuadrícula de tarjetas de eventos con búsqueda y paginación (9 por página) y una insignia de estado. Público; los organizadores y administradores también ven los eventos no publicados según su rol.

> **Captura pendiente:** guarda la imagen como `docs/images/event-list.png` y reemplaza este bloque con `![Listado de eventos](images/event-list.png)`.

## Detalle del evento

**Ruta:** `/events/:id`

Información del evento, insignia de estado, cupos disponibles, el botón de inscribirse/cancelar y la lista de sesiones con la inscripción a cada sesión. La lectura es pública; inscribirse requiere iniciar sesión.

> **Captura pendiente:** guarda la imagen como `docs/images/event-detail.png` y reemplaza este bloque con `![Detalle del evento](images/event-detail.png)`.

## Detalle del evento, vista de gestión

**Ruta:** `/events/:id`

La misma página para el organizador del evento o un administrador: enlace de edición, cambio de estado, descarga del CSV de participantes, eliminación y los controles para agregar, editar y eliminar sesiones.

> **Captura pendiente:** guarda la imagen como `docs/images/event-detail-manage.png` y reemplaza este bloque con `![Detalle del evento, vista de gestión](images/event-detail-manage.png)`.

## Formulario de evento

**Ruta:** `/events/new` y `/events/:id/edit`

Crear o editar un evento (nombre, descripción, lugar, fechas, capacidad). Organizadores y administradores; la edición se limita al organizador del evento o a un administrador, y solo mientras el evento no esté cancelado ni finalizado.

> **Captura pendiente:** guarda la imagen como `docs/images/event-form.png` y reemplaza este bloque con `![Formulario de evento](images/event-form.png)`.

## Formulario de ponente

**Ruta:** `/speakers/new`

Agregar un ponente (nombre, biografía, correo opcional) al directorio compartido. Organizadores y administradores.

> **Captura pendiente:** guarda la imagen como `docs/images/speaker-form.png` y reemplaza este bloque con `![Formulario de ponente](images/speaker-form.png)`.

## Mis eventos

**Ruta:** `/profile`

El resumen del perfil del usuario con sesión iniciada y los eventos a los que está inscrito, con una acción para cancelar. Cualquier usuario con sesión iniciada.

> **Captura pendiente:** guarda la imagen como `docs/images/profile.png` y reemplaza este bloque con `![Mis eventos](images/profile.png)`.

## Reportes

**Ruta:** `/reports`

Vista previa de participantes por evento o por sesión, con búsqueda, filtros de estado y de fecha, paginación y descarga en CSV. Organizadores (sus propios eventos) y administradores; los demás roles ven un mensaje de acceso no permitido.

> **Captura pendiente:** guarda la imagen como `docs/images/reports.png` y reemplaza este bloque con `![Reportes](images/reports.png)`.

## Administración de usuarios

**Ruta:** `/admin/users`

Búsqueda por prefijo de correo sobre las cuentas de usuario, con edición en línea de nombre, correo, rol e indicador de activo. Solo administradores; los demás roles ven un mensaje de acceso no permitido.

> **Captura pendiente:** guarda la imagen como `docs/images/admin-users.png` y reemplaza este bloque con `![Administración de usuarios](images/admin-users.png)`.

## Página no encontrada

**Ruta:** cualquier ruta desconocida (`*`)

Mensaje y enlace de regreso a la página de inicio. Público.

> **Captura pendiente:** guarda la imagen como `docs/images/not-found.png` y reemplaza este bloque con `![Página no encontrada](images/not-found.png)`.

## Barra de navegación, anónimo

**Ruta:** todas las páginas

Enlace de la marca más los enlaces de inicio de sesión y registro. Se muestra a los visitantes sin sesión.

> **Captura pendiente:** guarda la imagen como `docs/images/navbar-anonymous.png` y reemplaza este bloque con `![Barra de navegación, anónimo](images/navbar-anonymous.png)`.

## Barra de navegación, organizador

**Ruta:** todas las páginas

Muestra Nuevo evento, Nuevo ponente, Reportes y Mis eventos, el nombre del usuario y Cerrar sesión. Los administradores también ven Administración.

> **Captura pendiente:** guarda la imagen como `docs/images/navbar-organizer.png` y reemplaza este bloque con `![Barra de navegación, organizador](images/navbar-organizer.png)`.

## Móvil: listado de eventos

**Ruta:** `/` en ancho de teléfono

El listado de eventos por debajo del punto de corte de 640 px, donde la barra de navegación se apila verticalmente y la cuadrícula pasa a una sola columna.

> **Captura pendiente:** guarda la imagen como `docs/images/mobile-event-list.png` y reemplaza este bloque con `![Móvil: listado de eventos](images/mobile-event-list.png)`.

## Móvil: detalle del evento

**Ruta:** `/events/:id` en ancho de teléfono

El detalle del evento y la lista de sesiones en ancho de teléfono.

> **Captura pendiente:** guarda la imagen como `docs/images/mobile-event-detail.png` y reemplaza este bloque con `![Móvil: detalle del evento](images/mobile-event-detail.png)`.
