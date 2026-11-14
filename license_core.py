"""Offline Ed25519 licensing. Only the public key is embedded in the EXE."""
import base64
import hashlib
import json
import os
import re
import uuid
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PUBLIC_KEY_HEX = '8a5ebe472268cdce8a1b5cfa1b786bfdc5d0d8795fb5ab8e5bc51c4a36e29b72'
PRODUCT = 'Auto Train Mil va Co Mo'

def hwid():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography', 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            machine_id = str(winreg.QueryValueEx(k, 'MachineGuid')[0])
    except OSError:
        machine_id = str(uuid.getnode())
    raw = hashlib.sha256((PRODUCT + ':' + machine_id).encode('utf-8')).hexdigest().upper()[:32]
    return '-'.join(raw[i:i+8] for i in range(0, 32, 8))

def license_file():
    folder = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'AutoTrainMilCoMo'
    folder.mkdir(parents=True, exist_ok=True)
    return folder / 'license.txt'

def validate(token, current_hwid=None):
    if not re.fullmatch(r'[0-9a-fA-F]{64}', PUBLIC_KEY_HEX):
        raise ValueError('Chưa cấu hình khóa công khai. Chủ phần mềm cần chạy setup_license.py trước khi build.')
    try:
        part1, part2 = token.strip().split('.')
        payload_bytes = base64.urlsafe_b64decode(part1 + '=' * (-len(part1) % 4))
        signature = base64.urlsafe_b64decode(part2 + '=' * (-len(part2) % 4))
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(PUBLIC_KEY_HEX)).verify(signature, payload_bytes)
        payload = json.loads(payload_bytes)
    except Exception as exc:
        raise ValueError('Mã kích hoạt không hợp lệ hoặc đã bị thay đổi.') from exc
    if payload.get('product') != PRODUCT or payload.get('hwid') != (current_hwid or hwid()):
        raise ValueError('Mã kích hoạt không thuộc máy tính này.')
    # date.max is a compatibility sentinel for permanent licenses.
    # Existing GUI code expects a date object and compares it to date.today().
    if payload.get('permanent') is True and payload.get('expires') is None:
        return date.max
    try:
        expiry = date.fromisoformat(payload['expires'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Mã kích hoạt thiếu ngày hết hạn.') from exc
    if date.today() > expiry:
        raise ValueError(f'Mã đã hết hạn ngày {expiry.strftime("%d/%m/%Y")}. Vui lòng gia hạn.')
    return expiry

def saved_license():
    try:
        return license_file().read_text(encoding='utf-8').strip()
    except OSError:
        return ''
