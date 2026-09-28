import streamlit as st
import cv2
import numpy as np
import pytesseract
import re
from PIL import Image
from datetime import datetime

# -----------------------------
# Page settings
# -----------------------------
st.set_page_config(
    page_title="MediScan",
    page_icon="💊",
    layout="centered"
)

st.title("💊 MediScan")
st.subheader("Scan. Verify. Understand.")

st.write(
    "Take a photo of a medicine strip or upload an image. "
    "MediScan will try to read the information printed on the package."
)

# -----------------------------
# QR CODE DETECTION
# -----------------------------
def detect_qr(image):
    img = np.array(image)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(img)

    if data:
        return data.strip()

    return None


# -----------------------------
# OCR
# -----------------------------
def extract_text(image):
    img = np.array(image)

    # RGB -> BGR
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # Make small printed text larger
    scale = 2
    img = cv2.resize(
        img,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC
    )

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Improve contrast
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    # OCR on normal image
    text1 = pytesseract.image_to_string(
        gray,
        config="--psm 6"
    )

    # OCR on threshold image
    threshold = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )

    text2 = pytesseract.image_to_string(
        threshold,
        config="--psm 6"
    )

    # Combine both OCR results
    combined = text1 + "\n" + text2

    return combined


# -----------------------------
# DATE DETECTION
# -----------------------------
def find_dates(text):

    upper = text.upper()

    # Examples:
    # MFG DEC 2023
    # MFD 12/2023
    # EXP NOV 2026
    # EXP 11/2026

    mfg_patterns = [
        r"(?:MFG|MFD|MFR|MANUFACTURED)[\s:.-]*"
        r"([A-Z]{3,9}\s*\d{4})",

        r"(?:MFG|MFD|MFR|MANUFACTURED)[\s:.-]*"
        r"(\d{1,2}[/-]\d{4})"
    ]

    exp_patterns = [
        r"(?:EXP|EXPIRY|EXPIRES)[\s:.-]*"
        r"([A-Z]{3,9}\s*\d{4})",

        r"(?:EXP|EXPIRY|EXPIRES)[\s:.-]*"
        r"(\d{1,2}[/-]\d{4})"
    ]

    mfg = None
    exp = None

    for pattern in mfg_patterns:
        match = re.search(pattern, upper)
        if match:
            mfg = match.group(1)
            break

    for pattern in exp_patterns:
        match = re.search(pattern, upper)
        if match:
            exp = match.group(1)
            break

    return mfg, exp


# -----------------------------
# MEDICINE NAME DETECTION
# -----------------------------
def find_medicine_name(text):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # Common words that are not medicine names
    ignore_words = [
        "TABLETS",
        "TABLET",
        "CAPSULES",
        "CAPSULE",
        "COMPOSITION",
        "WARNING",
        "CAUTION",
        "MANUFACTURED",
        "MFG",
        "MFD",
        "EXP",
        "EXPIRY",
        "DOSAGE",
        "STORAGE",
        "MRP",
        "BATCH",
        "INDIA",
        "PHARMACEUTICALS"
    ]

    candidates = []

    for line in lines:

        clean = re.sub(
            r"[^A-Za-z0-9 .+-]",
            " ",
            line
        )

        clean = re.sub(
            r"\s+",
            " ",
            clean
        ).strip()

        if len(clean) < 4:
            continue

        upper = clean.upper()

        if any(word in upper for word in ignore_words):
            continue

        # Prefer lines containing dosage numbers
        if re.search(r"\d+\s*(MG|MCG|G|ML)", upper):
            candidates.append(clean)

    if candidates:
        return candidates[0]

    # Fallback
    if lines:
        return lines[0]

    return "Not detected"


# -----------------------------
# MANUFACTURER DETECTION
# -----------------------------
def find_manufacturer(text):

    upper = text.upper()

    patterns = [
        r"MANUFACTURED BY[:\s]+([A-Z][A-Z &.-]+)",
        r"MANUFACTURER[:\s]+([A-Z][A-Z &.-]+)",
        r"BY[:\s]+([A-Z][A-Z &.-]+PHARM[A-Z]*)"
    ]

    for pattern in patterns:

        match = re.search(pattern, upper)

        if match:
            value = match.group(1).strip()

            if len(value) > 3:
                return value

    # Useful fallback for the prototype
    if "CADILA" in upper:
        return "Cadila Pharmaceuticals"

    return "Not detected"


# -----------------------------
# BATCH NUMBER
# -----------------------------
def find_batch(text):

    upper = text.upper()

    patterns = [
        r"(?:BATCH|B\.?NO|BATCH NO)[\s:.-]*([A-Z0-9/-]+)",
        r"(?:LOT|LOT NO)[\s:.-]*([A-Z0-9/-]+)"
    ]

    for pattern in patterns:

        match = re.search(pattern, upper)

        if match:
            return match.group(1).strip()

    return "Not detected"


# -----------------------------
# EXPIRY STATUS
# -----------------------------
def expiry_status(expiry_text):

    if not expiry_text:
        return "⚪ Expiry not detected"

    upper = expiry_text.upper()

    months = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12
    }

    match = re.search(
        r"([A-Z]{3})\s*(\d{4})",
        upper
    )

    if not match:
        return "⚪ Could not determine expiry"

    month_text = match.group(1)
    year = int(match.group(2))

    if month_text not in months:
        return "⚪ Could not determine expiry"

    month = months[month_text]

    # Expiry at the end of the stated month
    if month == 12:
        expiry_date = datetime(year + 1, 1, 1)
    else:
        expiry_date = datetime(year, month + 1, 1)

    if datetime.now() < expiry_date:
        return "✅ NOT EXPIRED"
    else:
        return "❌ EXPIRED"


# -----------------------------
# SCANNER
# -----------------------------
st.divider()

st.subheader("📷 Scan Medicine Strip")

camera_photo = st.camera_input(
    "Take a clear photo of the medicine strip"
)

st.caption(
    "Tip: Keep the printed side flat, well lit and close enough "
    "for the text to be readable."
)

# -----------------------------
# IMAGE UPLOAD
# -----------------------------
st.subheader("🖼️ Or Upload a Medicine Image")

uploaded_photo = st.file_uploader(
    "Choose an image",
    type=["jpg", "jpeg", "png"]
)

photo = camera_photo if camera_photo else uploaded_photo

# -----------------------------
# PROCESS IMAGE
# -----------------------------
if photo:

    image = Image.open(photo)

    st.image(
        image,
        caption="Medicine image",
        use_container_width=True
    )

    st.info("🔍 Reading medicine information...")

    # First check for QR
    qr_data = detect_qr(image)

    if qr_data:
        st.success(f"📱 QR detected: {qr_data}")

    # OCR
    extracted_text = extract_text(image)

    # Detect fields
    medicine_name = find_medicine_name(extracted_text)
    manufacturer = find_manufacturer(extracted_text)
    batch = find_batch(extracted_text)
    mfg, exp = find_dates(extracted_text)

    st.divider()

    st.subheader("💊 Detected Medicine Information")

    st.write(
        f"**Medicine Name:** {medicine_name}"
    )

    st.write(
        f"**Manufacturer:** {manufacturer}"
    )

    st.write(
        f"**Manufacturing Date:** {mfg or 'Not detected'}"
    )

    st.write(
        f"**Expiry Date:** {exp or 'Not detected'}"
    )

    st.write(
        f"**Batch Number:** {batch}"
    )

    if qr_data:
        st.write(
            f"**QR Information:** {qr_data}"
        )

    st.subheader("📅 Expiry Status")

    st.write(
        expiry_status(exp)
    )

    # -----------------------------
    # OCR RAW TEXT
    # -----------------------------
    with st.expander("🔎 View detected text"):

        st.text(
            extracted_text
        )

    st.divider()

    st.warning(
        "⚠️ Prototype: OCR may make mistakes when text is small, "
        "blurred or damaged. Always verify medicine information "
        "against the original package and an authoritative source."
    )
