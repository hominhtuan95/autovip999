"""Run LOCALLY once. Never upload PRIVATE_LICENSE_KEY.pem to GitHub."""
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

folder = Path(__file__).resolve().parent
private_path = folder / 'PRIVATE_LICENSE_KEY.pem'
if private_path.exists():
    key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    print('Sử dụng khóa riêng đã có.')
else:
    key = Ed25519PrivateKey.generate()
    private_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    print('Đã tạo PRIVATE_LICENSE_KEY.pem')
public_hex = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
core = folder / 'license_core.py'
source = core.read_text(encoding='utf-8')
import re
source, count = re.subn(r"^PUBLIC_KEY_HEX = '[^']*'$", f"PUBLIC_KEY_HEX = '{public_hex}'", source, count=1, flags=re.M)
if count != 1:
    raise SystemExit('Không tìm thấy biến PUBLIC_KEY_HEX trong license_core.py')
core.write_text(source, encoding='utf-8')
print('Đã cập nhật khóa công khai trong license_core.py')
print('TUYỆT ĐỐI KHÔNG đưa PRIVATE_LICENSE_KEY.pem lên GitHub hoặc gửi khách!')
