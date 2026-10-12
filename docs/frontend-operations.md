# Operación del frontend

Cómo ejecutar, construir, desplegar y probar el frontend. Todos los comandos `npm` se
corren dentro de `frontend/`.

## Inicio rápido

```bash
cd frontend
npm install
npm run dev        # servidor de desarrollo de Vite
```

El frontend necesita el backend corriendo (ver [backend-operations.md](backend-operations.md)).
El backend acepta peticiones del navegador solo desde los orígenes de `CORS_ORIGINS`, cuyo
valor por defecto es `http://localhost:5173` (`backend/app/core/config.py`), que es el
puerto del servidor de desarrollo de Vite y el que publica Docker Compose.

## Scripts de `package.json`

| Script | Qué hace |
| --- | --- |
| `npm run dev` | Servidor de desarrollo de Vite con recarga automática |
| `npm run build` | Verifica tipos con `tsc -b` y genera el paquete de producción en `dist/` con `vite build` |
| `npm run lint` | ESLint sobre todo el proyecto (`eslint.config.js`) |
| `npm test` | Corre todas las pruebas una vez (`vitest run`) |
| `npm run test:coverage` | Igual que `npm test` y además mide cobertura; falla si no se cumplen los umbrales |
| `npm run format` | Prettier reescribe los archivos de `src` |
| `npm run format:check` | Prettier solo revisa `src`, sin modificar nada |

## Variable de entorno

| Variable | Valor por defecto | Para qué |
| --- | --- | --- |
| `VITE_API_URL` | `http://localhost:8000/api/v1` | Dirección del backend que usa el navegador (`api/client.ts`) |

Vite incorpora este valor dentro del paquete en el momento del `build`. Cambiarla exige
volver a construir, no basta con reiniciar el contenedor.

## Docker y nginx

El servicio `frontend` de `docker-compose.yml` construye `frontend/Dockerfile`:

| Etapa | Qué hace |
| --- | --- |
| `build` (`node:22-alpine`) | Instala dependencias con `npm ci`, recibe `VITE_API_URL` como argumento de construcción y ejecuta `npm run build` |
| Final (`nginx:1.27-alpine`) | Copia `dist/` a `/usr/share/nginx/html` y usa `frontend/nginx.conf` |

`nginx.conf` hace dos cosas:

- `/assets/` se sirve con cache de un año (`immutable`), porque Vite nombra esos archivos
  con un hash del contenido.
- Cualquier otra ruta devuelve `index.html` con `no-cache`, para que el enrutador de React
  resuelva la URL (por ejemplo, recargar `/events/12` no da 404).

```bash
# desde la raíz del repositorio
docker compose up -d --build        # frontend en http://localhost:5173
```

El contenedor publica el puerto 80 de nginx como `5173` en tu máquina.

### Cómo llega al backend

nginx **no** hace de proxy hacia el backend. El navegador del usuario descarga los archivos
estáticos y luego llama directamente a `VITE_API_URL`, por lo que esa dirección debe ser
alcanzable desde la máquina del usuario, no desde dentro de la red de Docker. Por defecto
es `http://localhost:8000/api/v1`, el puerto que publica el backend. Para otro host:

```bash
VITE_API_URL=https://api.ejemplo.com/api/v1 docker compose up -d --build frontend
```

Ese origen también debe estar en `CORS_ORIGINS` del backend.

## Pruebas

- Herramientas: Vitest con `jsdom`, Testing Library y `@testing-library/user-event`.
  Configuración en `frontend/vite.config.ts`; preparación común en `src/test/setup.ts`
  (limpia el DOM y `localStorage` después de cada prueba).
- Ubicación: junto al archivo probado (`Button.tsx` y `Button.test.tsx`).
- No requieren backend ni servicios externos: las llamadas a `api/` se simulan.

```bash
npm test                                   # todas
npx vitest run src/utils                   # una carpeta
npx vitest run src/store/authStore.test.ts # un archivo
```

### Cobertura

`npm run test:coverage` usa el proveedor `v8`, mide `src/**/*.{ts,tsx}` y excluye
`main.tsx`, `src/test/`, los archivos de prueba, `vite-env.d.ts` y `src/types/`. Umbrales
mínimos (si uno falla, el comando termina con error):

| Métrica | Mínimo |
| --- | --- |
| Sentencias (`statements`) | 90 % |
| Líneas (`lines`) | 90 % |
| Funciones (`functions`) | 90 % |
| Ramas (`branches`) | 85 % |

El reporte HTML queda en `frontend/coverage/index.html`. Los resúmenes versionados y cómo
regenerarlos están en [coverage/README.md](coverage/README.md).

## Lint y formato

| Herramienta | Configuración | Alcance |
| --- | --- | --- |
| ESLint | `eslint.config.js`: reglas recomendadas de JavaScript, TypeScript y `react-hooks` | Archivos `.ts` y `.tsx`; ignora `dist` y `coverage` |
| Prettier | `.prettierrc`: sin punto y coma, comillas simples, 100 columnas | `src` |
| TypeScript | `tsconfig.app.json`, ejecutado por `npm run build` | Todo `src` |

Verificación completa antes de integrar un cambio:

```bash
npm run lint && npm run format:check && npm run test:coverage && npm run build
```
