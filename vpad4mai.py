import logging
import platform
import socket
import subprocess
from flask import Flask, request, render_template_string, jsonify
import win32api
import win32con
import time
import qrcode
from io import StringIO
import re
import win32clipboard
import argparse

app = Flask(__name__)

def get_local_ip():
    def is_private_ip(ip):
        return ip.startswith(('10.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.', '172.21.', '172.22.', '172.23.', '172.24.', '172.25.', '172.26.', '172.27.', '172.28.', '172.29.', '172.30.', '172.31.', '192.168.'))

    if platform.system() == "Windows":
        output = subprocess.check_output("ipconfig", universal_newlines=True)
        for line in output.split('\n'):
            if 'IPv4 Address' in line:
                ip = line.split(':')[-1].strip()
                if is_private_ip(ip):
                    return ip
    else:
        try:
            interfaces = socket.getaddrinfo(host=socket.gethostname(), port=None, family=socket.AF_INET)
            for interface in interfaces:
                ip = interface[4][0]
                if is_private_ip(ip):
                    return ip
        except Exception:
            pass
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if is_private_ip(ip):
            return ip
    except:
        pass
    
    return '127.0.0.1'


# 更新按键映射
# 修改maimai_keys字典，以模拟按下小键盘的按键，同时保留left区的字母键
maimai_keys = {
    'right_0': 0x66,  # VK_NUMPAD6
    'right_1': 0x63,  # VK_NUMPAD3
    'right_2': 0x62,  # VK_NUMPAD2
    'right_3': 0x61,  # VK_NUMPAD1
    'right_4': 0x64,  # VK_NUMPAD4
    'right_5': 0x67,  # VK_NUMPAD7
    'right_6': 0x68,  # VK_NUMPAD8
    'right_7': 0x69,  # VK_NUMPAD9
    'left_0': ord('D'),  # 保留字母键D
    'left_1': ord('C'),  # 保留字母键C
    'left_2': ord('X'),  # 保留字母键X
    'left_3': ord('Z'),  # 保留字母键Z
    'left_4': ord('A'),  # 保留字母键A
    'left_5': ord('Q'),  # 保留字母键Q
    'left_6': ord('W'),  # 保留字母键W
    'left_7': ord('E')   # 保留字母键E
}

def press_key(key_code):
    win32api.keybd_event(key_code, 0, 0, 0)
    time.sleep(0.1)
    win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>maimai DX Controller</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background-color: #f0f0f0;
            padding: 20px;
        }
        h1 {
            margin-bottom: 20px;
        }
        .controllers {
            display: flex;
            justify-content: space-around;
            width: 100%;
            margin-bottom: 20px;
        }
        .controller {
            width: 300px;
            height: 300px;
            position: relative;
            margin: 10px;
        }
        .button {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            position: absolute;
            display: flex;
            justify-content: center;
            align-items: center;
            font-size: 20px;
            font-weight: bold;
            color: white;
            cursor: pointer;
            user-select: none;
        }
        .left .button { background-color: #51bcf3; }
        .right .button { background-color: #f74000; }
        .button:active { transform: scale(0.95); }
        .url-processor {
            width: 100%;
            max-width: 600px;
            margin-top: 20px;
        }
        #urlInput {
            width: 100%;
            padding: 10px;
            margin-bottom: 10px;
        }
        #processButton {
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
        }
        #processButton:hover {
            background-color: #45a049;
        }
        #result {
            margin-top: 10px;
        }
        @media (max-width: 768px) {
            .controllers {
                flex-direction: column;
                align-items: center;
            }
        }
    </style>
</head>
<body>
    <h1>🛟maimai DX 虚拟控制器</h1>
    <div class="controllers">
        <div class="controller left"></div>
        <div class="controller right"></div>
    </div>

    <div class="url-processor">
        <input type="text" id="urlInput" placeholder="输入二维码链接">
        <p>登入二维码 -> 右上角[...] -> 复制链接</p>
        <button id="processButton">写入剪贴板</button>
        <div id="result"></div>
    </div>

    <script>
        function createButtons(container, side) {
            const centerX = 150;
            const centerY = 150;
            const radius = 120;
            const buttonLabels = side === 'left' ? 
                ['D', 'C', 'X', 'Z', 'A', 'Q', 'W', 'E'] : 
                ['6', '3', '2', '1', '4', '7', '8', '9'];

            for (let i = 0; i < 8; i++) {
                const angle = (i * Math.PI / 4) - (Math.PI / 8);
                const x = centerX + radius * Math.cos(angle) - 30;
                const y = centerY + radius * Math.sin(angle) - 30;

                const button = document.createElement('div');
                button.className = 'button';
                button.textContent = buttonLabels[i];
                button.style.left = `${x}px`;
                button.style.top = `${y}px`;
                button.setAttribute('data-key', `${side}_${i}`);

                button.addEventListener('touchstart', handleButtonPress);
                button.addEventListener('mousedown', handleButtonPress);

                container.appendChild(button);
            }
        }

        function handleButtonPress(event) {
            event.preventDefault();
            const key = event.target.getAttribute('data-key');
            fetch('/keypress', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: key })
            });
        }

        createButtons(document.querySelector('.left'), 'left');
        createButtons(document.querySelector('.right'), 'right');

        document.getElementById('processButton').addEventListener('click', function() {
            const url = document.getElementById('urlInput').value;
            fetch('/process_url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('result').textContent = data.message;
            });
        });
    </script>
</body>
</html>
    ''')

@app.route('/keypress', methods=['POST'])
def keypress():
    key = request.json['key']
    if key in maimai_keys:
        press_key(maimai_keys[key])
    return jsonify(success=True)

@app.route('/process_url', methods=['POST'])
def process_url():
    url = request.json['url']
    match = re.search(r'(MAID[0-9A-Za-z]+)\.html', url)
    if match:
        result = 'SGWC' + match.group(1)
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(result)
        win32clipboard.CloseClipboard()
        return jsonify(success=True, message="处理成功,结果已复制到剪贴板")
    else:
        return jsonify(success=False, message="URL格式不正确")

def generate_qr_code(url):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)
    
    f = StringIO()
    qr.print_ascii(out=f)
    f.seek(0)
    return f.read()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the Flask app with a custom port.')
    parser.add_argument('-PORT', type=int, default=7001, help='Port number to run the app on')
    args = parser.parse_args()
    hostname = get_local_ip()

    url = f'http://{hostname}:{args.PORT}'
    
    print("Scan this QR code to access the maimai DX controller:")
    print(generate_qr_code(url))
    print('url:', url)
    
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    app.run(host='0.0.0.0', port=args.PORT, debug=True)