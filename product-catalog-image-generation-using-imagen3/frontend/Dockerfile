FROM node:18.17.1 as build

RUN mkdir -p /code
WORKDIR /code
COPY . /code/
RUN npm ci
RUN npm run build:prod

FROM nginx:alpine
COPY --from=build /code/dist/quick-bot-app-frontend /usr/share/nginx/html
COPY --from=build /code/nginx.conf /etc/nginx/conf.d/

EXPOSE 8080