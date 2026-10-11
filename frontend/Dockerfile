FROM node:22-alpine AS build

WORKDIR /app

# Dependencies first so this layer is cached until the lock file changes.
COPY package.json package-lock.json ./
RUN npm ci

# The browser, not the container, calls the API, so the URL must be reachable
# from the user's machine. Vite inlines it into the bundle at build time.
ARG VITE_API_URL=http://localhost:8000/api/v1
ENV VITE_API_URL=$VITE_API_URL

COPY . .
RUN npm run build


FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
