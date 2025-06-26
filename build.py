#!/usr/bin/env python3
"""
Simple build script - just submit the Docker build
"""

import os
import subprocess

def main():
    project_id = os.environ.get('GCP_PROJECT_ID', 'steve-prod-cb8d0')
    location = 'us-west2'
    
    print("🚀 Building Flutter Docker Image...")
    
    cmd = [
        'gcloud', 'builds', 'submit',
        f'--region={location}',
        '--config=cloudbuild.yaml',
        f'--project={project_id}',
        '.'
    ]
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ Build submitted!")
        print(f"📋 Monitor: https://console.cloud.google.com/cloud-build/builds?project={project_id}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())