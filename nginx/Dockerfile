# Stage 1: build frontend
FROM node:20-alpine AS fe
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: nginx serving dist + proxy config
FROM nginx:alpine
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=fe /app/dist /usr/share/nginx/html