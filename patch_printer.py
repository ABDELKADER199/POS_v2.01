import os

file_path = r'd:\Python Desktop\POS_V2\utils\printer_service.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

out_lines = []
in_qr_block = False
replaced = False

for line in lines:
    if "def _get_qr_code_html" in line:
        in_qr_block = True
        out_lines.append(line)
        continue
        
    if in_qr_block:
        if "qr = qrcode.QRCode" in line:
            # We reached the rest of the function, insert our logic first
            indent = "            "
            out_lines.append(indent + "from utils.zatca_qr import ZatcaQRCoder\n")
            out_lines.append(indent + "now = datetime.now()\n")
            out_lines.append(indent + "timestamp_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')\n")
            out_lines.append(indent + "qr_payload = ZatcaQRCoder.generate_base64(\n")
            out_lines.append(indent + "    seller_name=store_name or 'المتجر',\n")
            out_lines.append(indent + "    tax_number=tax_number or '000000000000000',\n")
            out_lines.append(indent + "    timestamp_iso=timestamp_iso,\n")
            out_lines.append(indent + "    total_with_vat=float(invoice_data.get('total_amount', 0)),\n")
            out_lines.append(indent + "    vat_amount=float(invoice_data.get('tax_amount', 0))\n")
            out_lines.append(indent + ")\n")
            out_lines.append(line.replace("qr_content", "qr_payload"))
            in_qr_block = False
            replaced = True
        elif "qr_content =" in line or "f\"Store:" in line or "f\"Tax ID:" in line or "f\"Date:" in line or "f\"Total:" in line or "f\"VAT:" in line or "Generates an E-Invoice QR code" in line or "if not QR_AVAILABLE:" in line or "return \"<!-- QR Library not installed -->\"" in line or "try:" in line or "For a basic compliant QR" in line or line.strip() == ")":
            if "Generates an E-Invoice" in line:
                out_lines.append('        """Generates an E-Invoice QR code based on ZATCA/Egyptian standard (Base64 TLV)."""\n')
            elif "if not QR_AVAILABLE" in line:
                out_lines.append(line)
            elif "return " in line and "QR Library not installed" in line:
                out_lines.append(line)
            elif "try:" in line:
                out_lines.append(line)
            else:
                pass # skip old qr_content generation
        else:
            out_lines.append(line)
    else:
        if "qr.add_data(qr_content)" in line:
            out_lines.append(line.replace("qr_content", "qr_payload"))
        else:
            out_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(out_lines)

print("Patch applied." if replaced else "Patch failed.")
