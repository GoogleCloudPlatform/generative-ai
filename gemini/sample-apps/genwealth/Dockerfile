##
## Stage 1: Build the API
##
FROM node:lts-alpine AS api-build

WORKDIR /src
COPY ./api .

RUN npm install
RUN npx tsc --outDir /dist

##
## Stage 2: Build the UI
##
FROM node:lts-alpine AS ui-build

WORKDIR /app
COPY ./ui .

RUN npm install
RUN npx ng build --output-path /dist

##
## Stage 3: Build Runtime
##
FROM node:lts-alpine AS runtime

WORKDIR /app

# Copy build artifacts from the api-build stage
COPY --from=api-build /dist .
COPY --from=api-build /src/node_modules ./node_modules

# Copy build artifacts from the ui-build stage
COPY --from=ui-build /dist ./ui/dist/genwealth-advisor-ui

EXPOSE 8080

CMD ["node", "index.js"] 
