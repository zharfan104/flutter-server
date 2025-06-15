# Flutter Development Environment Docker Image
FROM ubuntu:22.04

# Set non-interactive mode for apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Install essential packages
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y \
        curl \
        git \
        unzip \
        xz-utils \
        nginx \
        python3 \
        python3-pip \
        python3-venv \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3-dev \
        wget \
        sudo && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Flutter
RUN cd /opt && \
    wget -q https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.16.0-stable.tar.xz && \
    tar xf flutter_linux_3.16.0-stable.tar.xz && \
    rm flutter_linux_3.16.0-stable.tar.xz && \
    chown -R root:root /opt/flutter && \
    chmod -R 755 /opt/flutter

# Add Flutter to PATH
ENV PATH="/opt/flutter/bin:$PATH"

# Fix Git safe directory issue
RUN git config --global --add safe.directory /opt/flutter

# Disable Flutter analytics and pre-cache
RUN flutter config --no-analytics && \
    flutter config --no-cli-animations && \
    flutter precache --web && \
    flutter doctor || true

# Install Python packages
RUN pip3 install flask gunicorn requests

# Create Flutter user and directories
RUN useradd -m -s /bin/bash flutter && \
    mkdir -p /home/flutter/project && \
    chown -R flutter:flutter /home/flutter && \
    chown -R flutter:flutter /opt/flutter

# Switch to flutter user and setup git config
USER flutter
WORKDIR /home/flutter

# Fix git config for flutter user, disable analytics, and create project
RUN git config --global --add safe.directory /opt/flutter && \
    flutter --disable-analytics && \
    flutter config --no-analytics && \
    flutter create --platforms=web project
WORKDIR /home/flutter/project
RUN flutter pub get

# Switch back to root for service configuration
USER root

# Configure nginx
COPY nginx.conf /etc/nginx/sites-available/flutter
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -sf /etc/nginx/sites-available/flutter /etc/nginx/sites-enabled/ && \
    nginx -t

# Create Flask app
COPY app.py /home/flutter/project/app.py
RUN chown flutter:flutter /home/flutter/project/app.py

# Create startup script
COPY start-flutter-env.sh /usr/local/bin/start-flutter-env.sh
RUN sed -i 's/\r$//' /usr/local/bin/start-flutter-env.sh && \
    chmod +x /usr/local/bin/start-flutter-env.sh && \
    echo "✅ Startup script fixed and ready" && \
    head -3 /usr/local/bin/start-flutter-env.sh

# Expose ports
EXPOSE 80 5000

# Set startup command
CMD ["/usr/local/bin/start-flutter-env.sh"]