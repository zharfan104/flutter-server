#!/bin/bash
set -e

echo "🚀 Starting Flutter environment..."

# Get user ID from metadata (if running on GCP)
USER_ID=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/user_id" -H "Metadata-Flavor: Google" 2>/dev/null || echo "docker-user")
echo "USER_ID=$USER_ID" > /etc/environment

# Start nginx
nginx

# Start Flask app as flutter user
cd /home/flutter/project
export PATH="/opt/flutter/bin:$PATH"

# Build web app
su -c 'export PATH="/opt/flutter/bin:$PATH"; cd /home/flutter/project; flutter build web' flutter

# Start Flask API in background
su -c 'export PATH="/opt/flutter/bin:$PATH"; cd /home/flutter/project; python3 app.py' flutter &

echo "✅ Flutter environment ready!"
echo "Web app: http://localhost/"
echo "API: http://localhost/api/health"

# Keep container running
tail -f /dev/null