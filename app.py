import streamlit as st
import base64
import json
import re
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
from openai import OpenAI


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="MediScan",
    page_icon="💊",
    layout="centered"
)


# =========================================================
# OPENAI CLIENT
# =========================================================

try:
    client = OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"]
    )
except Exception:
    client = None


# =========================================================
# TITLE
# =========================================================

st.title("💊 MediScan")
st.subheader("Scan. Verify. Understand.")

st.write(
    "Take a photo of a medicine strip or upload an image. "
    "MediScan will try to identify the information printed "
    "on the package."
)


# =========================================================
# QR CODE DETECTION
# =========================================================

def detect_qr(image):

    try:
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

    except Exception:
        return None


# =========================================================
# IMAGE TO BASE64
# =========================================================

def image_to_base64(image):

    buffer = BytesIO()

    image.convert("RGB").save(
        buffer,
        format="JPEG",
        quality=95
    )

    image_bytes = buffer.getvalue()

    return base64.b64encode(
        image_bytes
    ).decode("utf-8")


# =========================================================
# AI MEDICINE IMAGE ANALYSIS
# =========================================================

def analyze_medicine_image(image):

    if client is None:
        raise RuntimeError(
            "OpenAI client is not configured. "
            "Please add OPENAI_API_KEY to Streamlit Secrets."
        )

    image_base64 = image_to_base64(image)

    prompt = """
You are analyzing a photograph of a medicine package or
medicine strip.

Carefully read the visible text from the image.

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

IMPORTANT RULES:

1. Read only information that is actually visible.
2. Do NOT guess or invent information.
3. If a field cannot be read clearly, write:
   "Not clearly visible".
4. Read the medicine or brand name carefully.
5. Read the active ingredient if visible.
6. Read the strength, such as 2.5 mg or 500 mg.
7. Identify the dosage form if visible.
8. Identify the manufacturer if visible.
9. Read the batch number only if it is clearly visible.
10. Read the manufacturing date only if visible.
11. Read the expiry date only if visible.
12. Read the MRP only if visible.
13. general_use_printed must contain only information
    about use that is actually printed on the package.
14. Do not provide medical advice.
15. Do not tell the user whether they personally should
    take the medicine.
16. confidence must be exactly one of:
    "High", "Medium", "Low".
17. Keep each field concise.
"""

    try:

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
                            "image_url":
                                "data:image/jpeg;base64,"
                                + image_base64
                        }
                    ]
                }
            ]
        )

    except Exception as e:

        raise RuntimeError(
            f"OpenAI API request failed: {e}"
        )

    result = response.output_text.strip()

    # Remove markdown JSON fences
    result = re.sub(
        r"^```json\s*",
        "",
        result,
        flags=re.IGNORECASE
    )

    result = re.sub(
        r"^```\s*",
        "",
        result
    )

    result = re.sub(
        r"\s*```$",
        "",
        result
    )

    result = result.strip()

    # Convert response to JSON
    try:

        return json.loads(result)

    except json.JSONDecodeError:

        start = result.find("{")
        end = result.rfind("}")

        if start != -1 and end != -1:

            json_text = result[
                start:end + 1
            ]

            return json.loads(json_text)

        raise RuntimeError(
            "The AI returned an unexpected response format:\n\n"
            + result
        )


# =========================================================
# DISPLAY MEDICINE INFORMATION
# =========================================================

def display_result(data):

    st.divider()

    st.subheader(
        "💊 Detected Medicine Information"
    )

    def get_value(key):

        value = data.get(
            key,
            "Not clearly visible"
        )

        if value is None:
            return "Not clearly visible"

        if str(value).strip() == "":
            return "Not clearly visible"

        return str(value)

    col1, col2 = st.columns(2)

    with col1:

        st.write("**💊 Medicine Name**")

        st.info(
            get_value("medicine_name")
        )

        st.write("**🧪 Active Ingredient**")

        st.info(
            get_value("active_ingredient")
        )

        st.write("**💊 Strength**")

        st.info(
            get_value("strength")
        )

        st.write("**💊 Dosage Form**")

        st.info(
            get_value("dosage_form")
        )

        st.write("**🏭 Manufacturer**")

        st.info(
            get_value("manufacturer")
        )

    with col2:

        st.write("**📦 Batch Number**")

        st.info(
            get_value("batch_number")
        )

        st.write("**📅 Manufacturing Date**")

        st.info(
            get_value("manufacturing_date")
        )

        st.write("**📅 Expiry Date**")

        st.info(
            get_value("expiry_date")
        )

        st.write("**💰 MRP**")

        st.info(
            get_value("mrp")
        )

    st.subheader(
        "📌 Information Printed on Package"
    )

    st.write(
        get_value("general_use_printed")
    )

    st.subheader(
        "🔍 Reading Confidence"
    )

    confidence = get_value(
        "confidence"
    )

    if confidence.lower() == "high":

        st.success(
            "🟢 High confidence"
        )

    elif confidence.lower() == "medium":

        st.warning(
            "🟡 Medium confidence"
        )

    else:

        st.warning(
            "🔴 Low confidence"
        )

    st.divider()

    st.info(
        "ℹ️ Please verify the detected information "
        "with the original medicine package."
    )


# =========================================================
# CAMERA
# =========================================================

st.divider()

st.subheader(
    "📷 Scan Medicine Strip"
)

camera_photo = st.camera_input(
    "Take a clear picture of the medicine strip"
)

st.caption(
    "For best results, keep the printed side facing "
    "the camera and use good lighting."
)


# =========================================================
# IMAGE UPLOAD
# =========================================================

st.subheader(
    "🖼️ Or Upload a Medicine Image"
)

uploaded_photo = st.file_uploader(
    "Choose a medicine image",
    type=[
        "jpg",
        "jpeg",
        "png"
    ]
)


# =========================================================
# SELECT IMAGE
# =========================================================

photo = camera_photo or uploaded_photo


# =========================================================
# PROCESS IMAGE
# =========================================================

if photo:

    try:

        image = Image.open(photo)

        image = image.convert("RGB")

    except Exception:

        st.error(
            "❌ Unable to open this image."
        )

        st.stop()

    st.image(
        image,
        caption="Medicine image",
        use_container_width=True
    )

    # QR Detection
    qr_data = detect_qr(image)

    if qr_data:

        st.success(
            f"📱 QR Code detected: {qr_data}"
        )

    # AI Analysis
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

        except json.JSONDecodeError as e:

            st.error(
                "❌ The AI returned invalid JSON."
            )

            st.code(
                str(e),
                language="text"
            )

        except Exception as e:

            st.error(
                "❌ Unable to analyze the image."
            )

            st.write(
                "Here is the actual error:"
            )

            st.code(
                str(e),
                language="text"
            )
