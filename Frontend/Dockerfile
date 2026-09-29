# syntax=docker/dockerfile:1

# ---- Etapa de build: compila el bundle de Vite ----
FROM node:22.23.2-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
# Las variables VITE_* se incrustan en el bundle: nunca deben contener secretos.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# ---- Etapa de runtime: solo estaticos servidos por nginx no root ----
FROM nginxinc/nginx-unprivileged:1.29.1-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

USER nginx
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
