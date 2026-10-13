# Frontend de Mis Eventos

Aplicación de una sola página (SPA) de **Mis Eventos**, en español, para que asistentes,
organizadores y administradores gestionen eventos, sesiones, ponentes e inscripciones.
Usa React 18, TypeScript, Vite, React Router, Zustand y Axios; las pruebas son con
Vitest y Testing Library.

## Mapa de `src/`

| Carpeta | Contenido |
| --- | --- |
| `api/` | Cliente HTTP (`client.ts`) y llamadas al backend por recurso |
| `pages/` | Pantallas, una por ruta |
| `components/` | Componentes compartidos (formularios, tarjetas, navegación) |
| `routes/` | Definición de rutas y protección por rol |
| `store/` | Estado global con Zustand (sesión, eventos, avisos) |
| `utils/` | Validaciones, formato y permisos |
| `i18n/` | Textos en español |
| `styles/`, `types/`, `test/` | Tokens de estilo, tipos compartidos, preparación de pruebas |

## Configurar

| Variable | Por defecto | Para qué |
| --- | --- | --- |
| `VITE_API_URL` | `http://localhost:8000/api/v1` | Dirección del backend que usa el navegador |

- Vite la incorpora al paquete en el `build`: cambiarla exige volver a construir.
- Nunca pongas secretos en variables `VITE_*`: quedan visibles en el navegador.
- El `CORS_ORIGINS` del backend debe incluir el origen del frontend
  (`http://localhost:5173` por defecto).

## Ejecutar

Requiere Node.js y el backend en ejecución.

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # verifica tipos y genera dist/
```

Con Docker Compose, desde la raíz del repositorio (nginx sirve el paquete estático). Es el
mismo comando que levanta el backend: arranca todo el sistema, no solo el frontend.

```bash
docker compose up -d --build        # frontend en http://localhost:5173
```

## Probar

Las pruebas no necesitan backend ni servicios externos.

```bash
npm test                  # todas las pruebas, una vez
npm run test:coverage     # con cobertura; falla bajo los umbrales
npm run lint              # ESLint
npm run format:check      # Prettier (usa npm run format para corregir)
```

Umbrales de cobertura: 90 % en sentencias, líneas y funciones, y 85 % en ramas.

## Más documentación

- [../docs/frontend-architecture.md](../docs/frontend-architecture.md): mapa de `src`, rutas, sesión y cliente HTTP.
- [../docs/frontend-conventions.md](../docs/frontend-conventions.md): textos, validaciones, estilos y cómo agregar una pantalla.
- [../docs/frontend-operations.md](../docs/frontend-operations.md): scripts, Docker, nginx, pruebas y cobertura.
- [../docs/screens.md](../docs/screens.md): pantallas de la aplicación.
