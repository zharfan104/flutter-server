#!/usr/bin/env python3
from flask import Flask, jsonify, request
import os
import subprocess
import json

app = Flask(__name__)

@app.route('/api/health')
def health():
    return jsonify({
        'status': 'healthy',
        'user_id': os.environ.get('USER_ID', 'unknown'),
        'flutter_version': get_flutter_version()
    })

@app.route('/api/hot-reload', methods=['POST'])
def hot_reload():
    try:
        # Trigger Flutter hot reload
        result = subprocess.run(['flutter', 'run', '--hot'], 
                              cwd='/home/flutter/project',
                              capture_output=True, text=True, timeout=10)
        return jsonify({'status': 'reloaded', 'output': result.stdout})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/build', methods=['POST'])
def build_web():
    try:
        result = subprocess.run(['flutter', 'build', 'web'], 
                              cwd='/home/flutter/project',
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return jsonify({'status': 'built', 'output': result.stdout})
        else:
            return jsonify({'error': result.stderr}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_flutter_version():
    try:
        result = subprocess.run(['flutter', '--version'], 
                              capture_output=True, text=True)
        return result.stdout.split('\n')[0]
    except:
        return 'unknown'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)