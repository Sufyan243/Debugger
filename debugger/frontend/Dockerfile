FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG VITE_API_BASE_URL
ARG VITE_BASE_PATH=/app
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build -- --base=$VITE_BASE_PATH

FROM busybox:latest
COPY --from=builder /app/dist /dist
CMD ["sh", "-c", "cp -r /dist/. /mnt/ && echo done"]
