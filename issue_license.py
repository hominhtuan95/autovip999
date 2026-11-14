"""Issue signed offline licenses for 3 days, N months, or permanently."""
import argparse
import base64
import json
import re
from datetime import date, timedelta
from calendar import monthrange
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from license_core import PRODUCT


def add_months(d, n):
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    return date(year, month, min(d.day, monthrange(year, month)[1]))


def main():
    parser = argparse.ArgumentParser(description='Cấp mã bản quyền theo HWID')
    parser.add_argument('--hwid', required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--days', type=int, help='Thời hạn theo ngày, ví dụ --days 3')
    group.add_argument('--months', type=int, help='Thời hạn theo tháng, ví dụ --months 6')
    group.add_argument('--permanent', action='store_true', help='Bản quyền không hết hạn')
    args = parser.parse_args()
    if args.days is not None and not 1 <= args.days <= 36500:
        parser.error('--days phải từ 1 đến 36500')
    if args.months is not None and not 1 <= args.months <= 120:
        parser.error('--months phải từ 1 đến 120')
    if not re.fullmatch(r'(?:[0-9A-Fa-f]{8}-){3}[0-9A-Fa-f]{8}', args.hwid):
        parser.error('HWID phải có dạng XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX')
    path = Path(__file__).resolve().parent / 'PRIVATE_LICENSE_KEY.pem'
    if not path.exists():
        parser.error('Thiếu PRIVATE_LICENSE_KEY.pem. Chạy setup_license.py trên máy cấp mã.')
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if args.permanent:
        expiry = None
    elif args.days is not None:
        expiry = date.today() + timedelta(days=args.days)
    else:
        expiry = add_months(date.today(), args.months if args.months is not None else 6)
    payload = {'product': PRODUCT, 'hwid': args.hwid.upper(), 'expires': expiry.isoformat() if expiry else None}
    if args.permanent:
        payload['permanent'] = True
    data = json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')
    enc = lambda b: base64.urlsafe_b64encode(b).decode('ascii').rstrip('=')
    print('HẾT HẠN:', expiry.strftime('%d/%m/%Y') if expiry else 'VĨNH VIỄN')
    print('MÃ KÍCH HOẠT:')
    print(enc(data) + '.' + enc(key.sign(data)))


if __name__ == '__main__':
    main()
