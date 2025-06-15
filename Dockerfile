# Dockerfile - Single Port Solution
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies including nginx
RUN apt-get update && apt-get install -y \
    curl git unzip xz-utils zip libglu1-mesa \
    python3 python3-pip \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Flutter
RUN git clone https://github.com/flutter/flutter.git /flutter -b stable --depth 1
ENV PATH="/flutter/bin:${PATH}"
RUN flutter doctor
RUN flutter config --enable-web

# Install Python dependencies
RUN pip3 install flask flask-cors requests

WORKDIR /app

# Copy the Flutter server file
COPY flutter_server.py /app/flutter_server.py

# Create nginx log directories and files
RUN mkdir -p /var/log/nginx && \
    touch /var/log/nginx/access.log && \
    touch /var/log/nginx/error.log && \
    chown -R www-data:www-data /var/log/nginx && \
    chmod 644 /var/log/nginx/access.log && \
    chmod 644 /var/log/nginx/error.log


# Create nginx configuration
RUN echo 'server {\n\
    listen 80 default_server;\n\
    listen [::]:80 default_server;\n\
    \n\
    # Enable error logging\n\
    error_log /var/log/nginx/error.log debug;\n\
    access_log /var/log/nginx/access.log;\n\
    \n\
    # API routes go to Flask\n\
    location /api {\n\
        proxy_pass http://127.0.0.1:5000;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
        proxy_set_header X-Forwarded-Proto $scheme;\n\
    }\n\
    \n\
    # Flutter web assets (accessed from iframe) - catch all static files\n\
    location ~ ^/(.*\.js|.*\.js\.map|.*\.css|.*\.png|.*\.jpg|.*\.jpeg|.*\.gif|.*\.svg|.*\.woff|.*\.woff2|.*\.ttf|canvaskit/.*|assets/.*|manifest\.json|favicon\.ico|favicon\.png|icons/.*) {\n\
        proxy_pass http://127.0.0.1:8080;\n\
        proxy_http_version 1.1;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_cache_bypass $http_upgrade;\n\
        add_header Cache-Control "no-cache, no-store, must-revalidate";\n\
        add_header Pragma "no-cache";\n\
        add_header Expires "0";\n\
    }\n\
    \n\
    # Flutter app routes - simplified\n\
    location /app {\n\
        proxy_pass http://127.0.0.1:8080/;\n\
        proxy_http_version 1.1;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
        proxy_set_header X-Forwarded-Proto $scheme;\n\
        proxy_read_timeout 60s;\n\
        proxy_connect_timeout 60s;\n\
        proxy_send_timeout 60s;\n\
    }\n\
    \n\
    # Root goes to Flask landing page\n\
    location / {\n\
        proxy_pass http://127.0.0.1:5000;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
}' > /etc/nginx/sites-available/default

# Create supervisor config to run both nginx and flask
RUN echo '[supervisord]\n\
nodaemon=true\n\
\n\
[program:nginx]\n\
command=/usr/sbin/nginx -g "daemon off;"\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0\n\
\n\
[program:flask]\n\
command=python3 /app/flutter_server.py\n\
directory=/app\n\
autostart=true\n\
autorestart=true\n\
stdout_logfile=/dev/stdout\n\
stdout_logfile_maxbytes=0\n\
stderr_logfile=/dev/stderr\n\
stderr_logfile_maxbytes=0' > /etc/supervisor/conf.d/flutter-app.conf

# Only expose port 80
EXPOSE 80

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/flutter-app.conf"]