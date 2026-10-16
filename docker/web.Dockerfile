FROM node:24.19.0-bookworm-slim@sha256:a9f5f7c91a432850b2a8a7797adf5eadb6c733ceed61167806cee7ea7fbc29df AS build
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/package.json
RUN --mount=type=secret,id=cloud_ca if [ -s /run/secrets/cloud_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/cloud_ca; fi && npm ci
COPY apps/web ./apps/web
COPY packages/contracts ./packages/contracts
COPY scripts/copy_web_static.mjs ./scripts/copy_web_static.mjs
RUN npm run build
FROM node:24.19.0-bookworm-slim@sha256:a9f5f7c91a432850b2a8a7797adf5eadb6c733ceed61167806cee7ea7fbc29df
WORKDIR /app
COPY --from=build /app/apps/web/.next/standalone ./
COPY --from=build /app/apps/web/.next/static ./apps/web/.next/static
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=3000
USER node
CMD ["node","apps/web/server.js"]
