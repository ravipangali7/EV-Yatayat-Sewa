import email
import re

path = r"C:\Users\legen\Downloads\Request to share Gateway QR test keys.eml"
with open(path, "rb") as f:
    raw = f.read()
print("file bytes", len(raw))
msg = email.message_from_bytes(raw)
print("--- all parts ---")
for i, part in enumerate(msg.walk()):
    ctype = part.get_content_type()
    fname = part.get_filename()
    disp = part.get("Content-Disposition")
    decoded = part.get_payload(decode=True)
    size = len(decoded) if decoded else 0
    cte = part.get("Content-Transfer-Encoding")
    print(f"{i:02d} type={ctype!r} cte={cte!r} fname={fname!r} disp={disp!r} decoded={size}")

print("--- filename strings ---")
for m in re.finditer(br"filename\*?=\s*\"?([^\";\r\n]+)", raw, re.I):
    print(m.group(1)[:300])

low = raw.lower()
print("npi.pfx count", low.count(b"npi.pfx"))
print("pkcs12 count", low.count(b"pkcs12"))
print(".pfx count", low.count(b".pfx"))
print("begin certificate", low.count(b"begin certificate"))
