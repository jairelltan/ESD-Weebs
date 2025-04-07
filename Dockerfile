FROM python:3.9-slim

WORKDIR /app

# Install required packages including nginx
RUN apt-get update && apt-get install -y default-mysql-client netcat-traditional nginx dos2unix

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directory for web files
RUN mkdir -p /var/www/html

# Copy all Python files to the app directory
COPY . .

# Make sure the entrypoint script has the correct line endings
COPY docker-entrypoint.sh /usr/local/bin/
RUN dos2unix /usr/local/bin/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/docker-entrypoint.sh && \
    ls -la /usr/local/bin/docker-entrypoint.sh

# Copy HTML files to nginx web directory
COPY *.html /var/www/html/
RUN cp -f *.css /var/www/html/ 2>/dev/null || true
RUN cp -f *.js /var/www/html/ 2>/dev/null || true
RUN if [ -d "images" ]; then cp -r images /var/www/html/; fi

# Fix permissions for web directory
RUN chown -R www-data:www-data /var/www/html/
RUN chmod -R 755 /var/www/html/

# Configure Nginx to serve the website on port 8080
RUN echo 'server {\n\
    listen 8080;\n\
    server_name localhost;\n\
    root /var/www/html;\n\
    index comics.html index.html shop.html;\n\
\n\
    # API proxy configuration\n\
    location /api/user/ {\n\
        proxy_pass http://127.0.0.1:5000/;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
\n\
    location /api/comic/ {\n\
        proxy_pass http://127.0.0.1:5001/;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
\n\
    location /api/waitlist/ {\n\
        proxy_pass http://127.0.0.1:5003/;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
\n\
    location /api/chapter/ {\n\
        proxy_pass http://127.0.0.1:5005/;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
\n\
    location /api/cart/ {\n\
        proxy_pass http://127.0.0.1:5008/cart/;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
\n\
    location /api/payment/ {\n\
        proxy_pass http://127.0.0.1:5022/;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
\n\
    # Any other URLs serve from the web root\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
        add_header "Access-Control-Allow-Origin" "*";\n\
    }\n\
}' > /etc/nginx/sites-available/default

# Create a default index.html if it doesn't exist
RUN if [ ! -f "/var/www/html/index.html" ]; then \
    echo '<html><head><meta http-equiv="refresh" content="0;URL=comics.html"></head><body>Redirecting to comics...</body></html>' > /var/www/html/index.html; \
fi

EXPOSE 8080

# Use bash directly as the entrypoint to simplify and debug
CMD ["bash", "/usr/local/bin/docker-entrypoint.sh"] 