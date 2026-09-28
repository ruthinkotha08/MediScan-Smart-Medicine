import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.set_page_config(
    page_title="MediScan",
    page_icon="💊",
    layout="centered"
)

# -----------------------------
# Demo Medicine Database
# -----------------------------
MEDICINES = {
    "MED001": {
        "name": "DemoCure 500",
        "ingredient": "Demo Ingredient 500 mg",
        "manufacturer": "MediScan Demo Pharma",
        "manufacturing_date": "15 January 2025",
        "expiry_date": "14 January 2027",
        "batch": "MS-A1025",
        "form": "Tablet",
        "use": "Used for demonstration purposes only.",
        "warning": "This is a prototype medicine record."
    },

    "MED002": {
        "name": "DemoRelief 10",
        "ingredient": "Demo Ingredient 10 mg",
        "manufacturer": "MediScan Demo Pharma",
        "manufacturing_date": "1 February 2026",
        "expiry_date": "31 January 2028",
        "batch": "MS-B2206",
        "form": "Tablet",
        "use": "Used for demonstration purposes only.",
        "warning": "This is a prototype medicine record."
    },

    "MED003": {
        "name": "ExpiredDemo 250",
        "ingredient": "Demo Ingredient 250 mg",
        "manufacturer": "MediScan Demo Pharma",
        "manufacturing_date": "1 March 2023",
        "expiry_date": "28 February 2025",
        "batch": "MS-X2303",
        "form": "Capsule",
        "use": "Used for demonstration purposes only.",
        "warning": "This demo medicine is marked as expired."
    }
}


# -----------------------------
# QR Decoder
# -----------------------------
def decode_qr(image):
    image = np.array(image)

    # Convert RGB to BGR for OpenCV
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    detector = cv2.QRCodeDetector()

    data, points, _ = detector.detectAndDecode(image)

    if data:
        return data.strip()

    return None


# -----------------------------
# Medicine Display
# -----------------------------
def show_medicine(medicine_id):

    medicine_id = medicine_id.strip().upper()

    if medicine_id not in MEDICINES:
        st.error(
            f"Medicine ID `{medicine_id}` was not found."
        )
        st.info(
            "For this prototype, use MED001, MED002 or MED003."
        )
        return

    medicine = MEDICINES[medicine_id]

    st.success(f"Medicine ID detected: {medicine_id}")

    st.title(f"💊 {medicine['name']}")

    st.write(f"**Medicine ID:** {medicine_id}")
    st.write(f"**Active Ingredient:** {medicine['ingredient']}")
    st.write(f"**Manufacturer:** {medicine['manufacturer']}")
    st.write(f"**Manufacturing Date:** {medicine['manufacturing_date']}")
    st.write(f"**Expiry Date:** {medicine['expiry_date']}")
    st.write(f"**Batch Number:** {medicine['batch']}")
    st.write(f"**Dosage Form:** {medicine['form']}")

    st.divider()

    st.subheader("📌 General Use")
    st.write(medicine["use"])

    st.subheader("⚠️ Safety Information")
    st.write(medicine["warning"])

    if medicine_id == "MED003":
        st.error("❌ EXPIRED")
    else:
        st.success("✅ VALID")


# -----------------------------
# App UI
# -----------------------------
st.title("💊 MediScan")
st.subheader("Scan. Verify. Understand.")

st.write(
    "Scan a prototype QR code containing a Medicine ID "
    "such as MED001, MED002 or MED003."
)

st.divider()

# -----------------------------
# Camera QR Scanner
# -----------------------------
st.subheader("📷 Scan Medicine QR Code")

camera_image = st.camera_input(
    "Point your camera at the QR code and take a picture"
)

if camera_image:

    image = Image.open(camera_image)

    qr_data = decode_qr(image)

    if qr_data:

        st.success(f"QR Code detected: {qr_data}")

        show_medicine(qr_data)

    else:

        st.error(
            "❌ QR code could not be detected."
        )

        st.info(
            "Make sure the QR code clearly contains "
            "MED001, MED002 or MED003."
        )


st.divider()

# -----------------------------
# Manual Product ID
# -----------------------------
st.subheader("⌨️ Product ID")

product_id = st.text_input(
    "Enter Medicine ID manually",
    placeholder="Example: MED001"
)

if st.button("Verify Medicine"):

    if product_id:
        show_medicine(product_id)
    else:
        st.warning("Please enter a Medicine ID.")


st.divider()

st.caption(
    "⚠️ Prototype only. Demo medicine records are fictional "
    "and should not be used for medical decisions."
)
