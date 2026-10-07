# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS builder

WORKDIR /build

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

COPY . .

# Vite inlines this at build time, so it has to be a build argument and
# not a runtime environment variable: the bundle is static.
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# The build runs vue-tsc before vite, so an image that exists is type clean.
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=builder /build/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Drop the default page and run as the unprivileged nginx user.
RUN rm -f /usr/share/nginx/html/index.html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget --quiet --spider http://127.0.0.1/ || exit 1
