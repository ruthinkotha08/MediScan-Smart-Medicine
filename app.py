import streamlit as st
import base64
import json
import re
import cv2
import numpy as np
from openai import OpenAI
from PIL import Image


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="MediScan",
    page_icon="💊",
    layout="centered"
)

st.title("💊 MediScan")
st.subheader("Scan. Verify. Understand.")

st.write(
    "Take a photo of a medicine strip and MediScan will "
    "extract the information printed on the package."
)


# =========================================================
# OPENAI
# =========================================================

try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

except Exception:
    st.error(
        "OPENAI_API_KEY is not configured."
    )
    st.stop()

client = OpenAI(
    api_key=OPENAI_API_KEY
)


# =========================================================
# QR CODE DETECTION
# =========================================================

def detect_qr(image):

    img = np.array(image)

    img = cv2.cvtColor(
        img,
        cv2.COLOR_RGB2BGR
    )

    detector = cv2.QRCodeDetector()

    data, points, _ = detector.detectAndDecode(img)

    if data:
        return data.strip()

    return None


# =========================================================
# IMAGE → BASE64
# =========================================================

def image_to_base64(image):

    # Convert image to JPEG
    from io import BytesIO

    buffer = BytesIO()

    image.convert("RGB").save(
        buffer,
        format="JPEG",
        quality=95
    )

    image_bytes = buffer.getvalue()

    encoded = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    return encoded


# =========================================================
# AI MEDICINE READER
# =========================================================

def analyze_medicine_image(image):

    image_base64 = image_to_base64(image)

    prompt = """
You are analyzing a photograph of a medicine package or medicine strip.

Read ONLY information that is actually visible in the image.

Do NOT guess missing information.

Return ONLY valid JSON using exactly these fields:

{
  "medicine_name": "",
  "active_ingredient": "",
  "strength": "",
  "dosage_form": "",
  "manufacturer": "",
  "batch_number": "",
  "manufacturing_date": "",
  "expiry_date": "",
  "mrp": "",
  "general_use_printed": "",
  "confidence": ""
}

Rules:

1. Read the medicine/brand name carefully.
2. Read the active ingredient if visible.
3. Read the strength such as 2.5 mg or 500 mg.
4. Identify the dosage form if visible.
5. Identify the manufacturer if visible.
6. Read the batch number only if it is clearly visible.
7. Read MFG/manufacturing date only if visible.
8. Read EXP/expiry date only if visible.
9. Read MRP only if visible.
10. "general_use_printed" should contain information about use ONLY if such information is actually printed on the package. Do not provide medical advice.
11. If something cannot be read, return "Not clearly visible".
12. Do not invent values.
13. Do not recommend whether a person should take the medicine.
14. Keep the answer concise.
15. "confidence" should be one of:
    "High", "Medium", or "Low".
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": prompt
                    },
                    {
                        "type": "input_image",
                        "image_url": (
                            "data:image/jpeg;base64,"
                            + image_base64
                        ),
                        "detail": "high"
                    }
                ]
            }
        ]
    )

    result = response.output_text.strip()

    # Remove ```json if model adds it
    result = re.sub(
        r"^```json\s*",
        "",
        result,
        flags=re.IGNORECASE
    )

    result = re.sub(
        r"\s*```$",
        "",
        result
    )

    return json.loads(result)


# =========================================================
# DISPLAY RESULT
# =========================================================

def display_result(data):

    st.divider()

    st.subheader(
        "💊 Detected Medicine Information"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.write("**Medicine Name**")
        st.info(
            data.get(
                "medicine_name",
                "Not clearly visible"
            )
        )

        st.write("**Active Ingredient**")
        st.info(
            data.get(
                "active_ingredient",
                "Not clearly visible"
            )
        )

        st.write("**Strength**")
        st.info(
            data.get(
                "strength",
                "Not clearly visible"
            )
        )

        st.write("**Dosage Form**")
        st.info(
            data.get(
                "dosage_form",
                "Not clearly visible"
            )
        )

        st.write("**Manufacturer**")
        st.info(
            data.get(
                "manufacturer",
                "Not clearly visible"
            )
        )

    with col2:

        st.write("**Batch Number**")
        st.info(
            data.get(
                "batch_number",
                "Not clearly visible"
            )
        )

        st.write("**Manufacturing Date**")
        st.info(
            data.get(
                "manufacturing_date",
                "Not clearly visible"
            )
        )

        st.write("**Expiry Date**")
        st.info(
            data.get(
                "expiry_date",
                "Not clearly visible"
            )
        )

        st.write("**MRP**")
        st.info(
            data.get(
                "mrp",
                "Not clearly visible"
            )
        )

    st.subheader("📌 Information Printed on Package")

    st.write(
        data.get(
            "general_use_printed",
            "Not clearly visible"
        )
    )

    st.subheader("🔍 Reading Confidence")

    confidence = data.get(
        "confidence",
        "Low"
    )

    if confidence == "High":
        st.success("High confidence")

    elif confidence == "Medium":
        st.warning("Medium confidence")

    else:
        st.warning("Low confidence")

    st.divider()

    st.info(
        "ℹ️ Please verify the detected information "
        "with the original medicine package."
    )


# =========================================================
# CAMERA
# =========================================================

st.divider()

st.subheader("📷 Scan Medicine Strip")

camera_photo = st.camera_input(
    "Take a clear picture of the medicine strip"
)

st.caption(
    "For best results, keep the printed side facing the camera "
    "and use good lighting."
)


# =========================================================
# IMAGE UPLOAD
# =========================================================

st.subheader("🖼️ Or Upload a Medicine Image")

uploaded_photo = st.file_uploader(
    "Choose an image",
    type=[
        "jpg",
        "jpeg",
        "png"
    ]
)


# Use camera photo first
photo = camera_photo or uploaded_photo


# =========================================================
# PROCESS IMAGE
# =========================================================

if photo:

    image = Image.open(photo)

    st.image(
        image,
        caption="Medicine image",
        use_container_width=True
    )

    # QR check
    qr_data = detect_qr(image)

    if qr_data:

        st.success(
            f"📱 QR Code detected: {qr_data}"
        )

    # AI analysis
    with st.spinner(
        "🤖 AI is reading the medicine package..."
    ):

        try:

            medicine_data = analyze_medicine_image(
                image
            )

            display_result(
                medicine_data
            )

        except json.JSONDecodeError:

            st.error(
                "The AI returned an unexpected format. "
                "Please try the image again."
            )

        except Exception as e:

            st.error(
                "Unable to analyze the image."
            )

            st.caption(
                str(e)
            )
