FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG VITE_TOOL_URL
ENV VITE_TOOL_URL=$VITE_TOOL_URL
RUN npm run build

FROM scratch
COPY --from=builder /app/dist /dist
