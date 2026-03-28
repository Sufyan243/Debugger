FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

ARG VITE_TOOL_URL
ENV VITE_TOOL_URL=$VITE_TOOL_URL
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY . .
RUN npm run build

FROM busybox:latest
COPY --from=builder /app/dist /dist
CMD ["sh", "-c", "cp -r /dist/. /mnt/ && echo done"]
