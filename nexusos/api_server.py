"""
NexusOS API Server - Simple Flask wrapper for Ollama

Endpoints:
- GET / - Status page
- POST /api/generate - Generate text
- POST /api/chat - Chat completion
- GET /api/models - List models
"""

from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
MODEL = os.environ.get('OLLAMA_MODEL', 'phi3')


@app.route('/')
def index():
    return jsonify({
        'name': 'NexusOS',
        'version': '1.0',
        'status': 'running',
        'model': MODEL,
        'ollama': OLLAMA_HOST
    })


@app.route('/api/models', methods=['GET'])
def list_models():
    try:
        r = requests.get(f'{OLLAMA_HOST}/api/tags', timeout=10)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json or {}
    prompt = data.get('prompt', '')
    model = data.get('model', MODEL)
    options = data.get('options', {})
    
    payload = {
        'model': model,
        'prompt': prompt,
        'stream': False,
        'options': options
    }
    
    try:
        r = requests.post(f'{OLLAMA_HOST}/api/generate', json=payload, timeout=120)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json or {}
    messages = data.get('messages', [])
    model = data.get('model', MODEL)
    
    payload = {
        'model': model,
        'messages': messages,
        'stream': False
    }
    
    try:
        r = requests.post(f'{OLLAMA_HOST}/api/chat', json=payload, timeout=120)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
