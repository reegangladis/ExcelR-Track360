"""
ExcelR Track360 - High-Resolution PDF Certificate & Dynamic QR Generation Engine
Renders production-ready, tamper-evident landscape credentials.
Strictly adheres to FR-CER-003, FR-CER-004, and SEC-CERT-01 specifications.
"""
import io
import hashlib
from datetime import date
from pathlib import Path
from typing import Tuple

import qrcode
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader


def render_certificate_pdf_bytes(
    serial_number: str,
    candidate_name: str,
    track_title: str,
    accredited_duration_months: int,
    issue_date: date,
    verification_hash: str,
    verification_url: str,
) -> bytes:
    """
    Renders an official high-resolution landscape A4 certificate as raw PDF bytes.
    Embeds dynamic QR code and cryptographic verification signature.
    """
    buffer = io.BytesIO()
    width, height = landscape(A4)  # 841.89 x 595.28 points

    c = canvas.Canvas(buffer, pagesize=(width, height))

    # 1. Background fill (Very light luxury cream / crisp slate)
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # 2. Outer Border (Deep Executive Navy)
    c.setStrokeColor(colors.HexColor("#0F172A"))
    c.setLineWidth(6)
    c.rect(24, 24, width - 48, height - 48, fill=0, stroke=1)

    # 3. Inner Decorative Border (Rich Gold)
    c.setStrokeColor(colors.HexColor("#D97706"))
    c.setLineWidth(2)
    c.rect(32, 32, width - 64, height - 64, fill=0, stroke=1)

    # 4. Corner Accent Ornaments
    c.setFillColor(colors.HexColor("#D97706"))
    corner_size = 14
    # Top-left
    c.rect(34, height - 34 - corner_size, corner_size, corner_size, fill=1, stroke=0)
    # Top-right
    c.rect(width - 34 - corner_size, height - 34 - corner_size, corner_size, corner_size, fill=1, stroke=0)
    # Bottom-left
    c.rect(34, 34, corner_size, corner_size, fill=1, stroke=0)
    # Bottom-right
    c.rect(width - 34 - corner_size, 34, corner_size, corner_size, fill=1, stroke=0)

    # 5. Top Brand Header
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 19)
    c.drawCentredString(width / 2.0, height - 76, "EXCELR ADVANCED LEARNING & INTERNSHIP ECOSYSTEM")

    c.setFillColor(colors.HexColor("#D97706"))
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(
        width / 2.0,
        height - 96,
        "CREDENTIAL OF PROFESSIONAL EXCELLENCE & ACCREDITED MILESTONE COMPLETION",
    )

    # Top separator line
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(1)
    c.line(width / 2.0 - 180, height - 108, width / 2.0 + 180, height - 108)

    # 6. Presentation Statement
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2.0, height - 145, "This is to certify that")

    # 7. Candidate Name (Large, Bold Navy)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width / 2.0, height - 185, candidate_name.strip())

    # Underline accent below name
    c.setStrokeColor(colors.HexColor("#D97706"))
    c.setLineWidth(2)
    c.line(width / 2.0 - 140, height - 195, width / 2.0 + 140, height - 195)

    # 8. Achievement Description
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 11)
    c.drawCentredString(
        width / 2.0,
        height - 232,
        "has successfully fulfilled all rigorous academic curriculum, industry project tiers, and accredited internship requirements in",
    )

    # 9. Specialization Track Title
    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2.0, height - 268, track_title.strip())

    # 10. Accredited Duration & Issue Date Badges
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 12)
    date_str = issue_date.strftime("%B %d, %Y")
    c.drawCentredString(
        width / 2.0,
        height - 302,
        f"Accredited Duration: {accredited_duration_months} Months  |  Date of Issuance: {date_str}",
    )

    # Mid separator line
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.setLineWidth(1)
    c.line(60, height - 330, width - 60, height - 330)

    # 11. Footer Section: QR Code, Verifier Credentials, Signatures
    # Generate QR Code image
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=1,
    )
    qr.add_data(verification_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)
    qr_reader = ImageReader(qr_buf)

    # Draw QR Code in bottom-center
    qr_size = 90
    qr_x = (width / 2.0) - (qr_size / 2.0)
    qr_y = 65
    c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)

    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(width / 2.0, 52, "SCAN TO VERIFY CREDENTIAL")

    # Left Column: Serial ID & Cryptographic Hash
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(60, 130, "AUTHENTIC CERTIFICATE IDENTIFIER:")
    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, 114, serial_number)

    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(60, 96, "CRYPTOGRAPHIC INTEGRITY HASH:")
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Courier", 7.5)
    c.drawString(60, 83, verification_hash[:32])
    c.drawString(60, 72, verification_hash[32:])

    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.drawString(60, 56, "Issued via ExcelR Track360 Credential Engine.")
    c.drawString(60, 46, "Cryptographically signed and tamper-evident.")

    # Right Column: Authorizing Signatures
    c.setStrokeColor(colors.HexColor("#475569"))
    c.setLineWidth(1)
    sig_line_w = 170
    c.line(width - 60 - sig_line_w, 114, width - 60, 114)

    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 60, 100, "Prof. Dr. Rajesh K. Varma")
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 8)
    c.drawRightString(width - 60, 88, "Academic Dean & Controller of Examinations")
    c.drawRightString(width - 60, 76, "ExcelR Education Standards Board")

    c.line(width - 60 - sig_line_w, 56, width - 60, 56)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.HexColor("#D97706"))
    c.drawRightString(width - 60, 44, "Officially Sealed & Digitally Verified")

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.getvalue()
