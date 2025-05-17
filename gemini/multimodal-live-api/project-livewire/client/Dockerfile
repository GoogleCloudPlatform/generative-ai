FROM nginx:alpine

# Create the directory structure
RUN mkdir -p /usr/share/nginx/html

# Copy mobile.html as index.html
COPY mobile.html /usr/share/nginx/html/index.html

# Copy other required files
COPY styles /usr/share/nginx/html/styles
COPY src /usr/share/nginx/html/src
COPY assets /usr/share/nginx/html/assets

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create a simple health check file
RUN echo "OK" > /usr/share/nginx/html/health

# Expose port 8080 (Cloud Run requirement)
EXPOSE 8080

# Start nginx in foreground
CMD ["nginx", "-g", "daemon off;"] 