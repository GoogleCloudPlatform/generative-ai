FROM nginx:alpine

# install Python 3 and pip
RUN apk add --no-cache python3=3.12.8-r1 py3-pip=24.0-r2 supervisor=4.2.5-r5

# copy the front end 
COPY frontend/. /usr/share/nginx/html

# copy backend
COPY backend/. /app

# install supervisord
RUN pip3 install --no-cache-dir --break-system-packages -r app/requirements.txt

COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]