#!/usr/bin/env python3
"""
server.py - Backend utama untuk aplikasi Komo AI.
File ini berfungsi sebagai server yang menerima pesan dari pengguna,
membersihkan data sensitif (privasi), dan berkomunikasi dengan kecerdasan buatan (AI).
"""

import http.server
import socketserver
import json
import os
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime
import random

# Konfigurasi
PORT = int(os.environ.get('PORT', 3030))
HF_TOKEN = os.environ.get('HF_TOKEN') or os.environ.get('HF_API_KEY') or None
HF_MODEL = os.environ.get('HF_MODEL', 'meta-llama/Llama-3.1-8B-Instruct:novita')
MAX_MODEL_TOKENS = int(os.environ.get('MAX_MODEL_TOKENS', '2048'))

class KomoAIHandler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_cors_headers()
        self.send_response(204)
        self.end_headers()
    
    def send_cors_headers(self):
        """Set CORS headers for cross-origin requests"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_GET(self):
        """Handle GET requests for static files"""
        print(f"GET {self.path}")
        
        # Route untuk file statis
        if self.path == '/':
            self.path = '/index.html'
        elif self.path == '/favicon.ico':
            self.send_response(404)
            self.end_headers()
            return
        
        # Coba kirim file statis
        try:
            return super().do_GET()
        except FileNotFoundError:
            self.send_error(404, f"File not found: {self.path}")
    
    def do_POST(self):
        """Handle POST requests, especially for chat"""
        print(f"POST {self.path}")
        
        # Set CORS headers
        self.send_cors_headers()
        
        if self.path == '/chat':
            self.handle_chat()
        else:
            self.send_error(404, "Endpoint not found")
    
    def handle_chat(self):
        """Handle chat requests to AI"""
        try:
            # Baca data dari request
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Validasi data
            if not data or 'messages' not in data:
                self.send_error(400, "Invalid request data")
                return
            
            messages = data['messages']
            
            # Validasi pesan
            if not isinstance(messages, list) or len(messages) == 0:
                self.send_error(400, "Messages must be a non-empty array")
                return
            
            # Validasi setiap pesan
            for msg in messages:
                if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
                    self.send_error(400, "Each message must have role and content")
                    return
                if not isinstance(msg['content'], str) or msg['content'].strip() == '':
                    self.send_error(400, "Message content must be non-empty string")
                    return
            
            # Persiapkan pesan untuk AI
            system_prompt = "You are Komo — a privacy-first multilingual AI assistant. Default: reply in English. If the user writes in another language, reply in that language. Translate only when explicitly requested; preserve meaning and tone. Avoid mixing languages; use clear, natural sentences. Keep formatting and line breaks; do not add extra commentary."
            
            # Bangun conversation history
            conversation = [{"role": "system", "content": system_prompt}]
            
            # Tambahkan pesan dari user (skip system messages)
            for msg in messages:
                if msg['role'] != 'system':
                    conversation.append({
                        "role": msg['role'],
                        "content": msg['content'].strip()
                    })
            
            # Hitung token (sederhana)
            total_tokens = sum(len(msg["content"].split()) for msg in conversation)
            
            # Potong jika terlalu panjang
            if total_tokens > MAX_MODEL_TOKENS:
                # Hapus pesan lama kecuali system prompt
                while total_tokens > MAX_MODEL_TOKENS and len(conversation) > 1:
                    removed = conversation.pop(1)
                    total_tokens -= len(removed["content"].split())
            
            # Siapkan request ke Hugging Face
            hf_payload = {
                "model": HF_MODEL,
                "messages": conversation,
                "max_tokens": 1024,
                "temperature": 0.7,
                "stream": False
            }
            
            # Kirim request ke Hugging Face
            try:
                # Siapkan data dan headers
                data_json = json.dumps(hf_payload).encode('utf-8')
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {HF_TOKEN}" if HF_TOKEN else ""
                }
                
                # Buat request
                req = urllib.request.Request(
                    'https://router.huggingface.co/v1/chat/completions',
                    data=data_json,
                    headers=headers,
                    method='POST'
                )
                
                # Kirim request
                with urllib.request.urlopen(req, timeout=30) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    ai_reply = result['choices'][0]['message']['content']
                    
                    # Kirim response ke client
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    
                    response_data = {
                        "reply": ai_reply,
                        "model": HF_MODEL,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    self.wfile.write(json.dumps(response_data).encode('utf-8'))
                    
            except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
                # Fallback: gunakan response sederhana
                fallback_responses = [
                    "I'm here to help! What would you like to know?",
                    "Hello! I'm Komo AI. How can I assist you today?",
                    "I understand your question. Let me help you with that.",
                    "Thanks for your message! I'm ready to assist you."
                ]
                
                fallback_reply = random.choice(fallback_responses)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                
                response_data = {
                    "reply": fallback_reply,
                    "model": "fallback",
                    "timestamp": datetime.now().isoformat(),
                    "note": "Using fallback due to AI service unavailable"
                }
                
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
                
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON data")
        except Exception as e:
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

def run_server():
    """Start the server"""
    with socketserver.TCPServer(("", PORT), KomoAIHandler) as httpd:
        print(f"🚀 Komo AI Server running at http://localhost:{PORT}")
        print(f"📡 Using model: {HF_MODEL}")
        if HF_TOKEN:
            print("🔑 Hugging Face token configured")
        else:
            print("⚠️  No Hugging Face token found, using fallback responses")
        print("Press Ctrl+C to stop the server")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
            httpd.shutdown()

if __name__ == "__main__":
    run_server()