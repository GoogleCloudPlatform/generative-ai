FROM node:20-alpine AS root_build

ARG NODE_ENV
ARG NEXT_PUBLIC_BACKEND_URL
# Docker build build arg (e.g. git repo hashbranch name)
ENV NEXT_PUBLIC_APP_ENV=$NODE_ENV
ENV NEXT_PUBLIC_BACKEND_URL=$NEXT_PUBLIC_BACKEND_URL

WORKDIR /app/frontend
COPY src/frontend/package*.json ./
RUN npm ci --force
COPY src/frontend/app ./app/
COPY src/frontend/components ./components/
COPY src/frontend/lib ./lib/
COPY src/frontend/public ./public/
COPY src/frontend/components.json .
COPY src/frontend/eslint.config.mjs .
COPY src/frontend/next.config.mjs .
COPY src/frontend/postcss.config.mjs .
COPY src/frontend/tailwind.config.ts .
COPY src/frontend/tsconfig.json .
# COPY src/frontend/app/fonts .
COPY src/frontend/public/fonts .

RUN npm run build --force

FROM root_build AS serve

WORKDIR /app
COPY --from=root_build /app/frontend/out/. .
ENV PORT=8000
EXPOSE $PORT
CMD ["sh", "-c", "npx --y serve -p $PORT"]