import time
import base64
import os
import requests
from flask import Flask, request, jsonify
import logging

app = Flask(__name__)

# إعداد الـ Logging
logging.basicConfig(level=logging.INFO)

# لازم يكون موجود في Environment
LIGHTX_API_KEY = os.environ["550d0313b4314537bc60c5655bd5115c_679d7237f8ae40fcbb018e0dae2f7147_andoraitools"]

UPLOAD_URL = "https://api.lightxeditor.com/external/api/v2/uploadImageUrl"
TRYON_URL = "https://api.lightxeditor.com/external/api/v2/aivirtualtryon"
STATUS_URL = "https://api.lightxeditor.com/external/api/v2/order-status"


def upload_image(file_base64, mime_type):
    headers = {"Content-Type": "application/json", "x-api-key": LIGHTX_API_KEY}

    if file_base64.startswith("data:"):
        file_base64 = file_base64.split(",")[1]

    raw_bytes = base64.b64decode(file_base64)
    size_bytes = len(raw_bytes)

    data = {
        "uploadType": "imageUrl",
        "size": size_bytes,
        "contentType": mime_type
    }
    resp = requests.post(UPLOAD_URL, headers=headers, json=data)
    resp.raise_for_status()
    resp_json = resp.json()

    upload_link = resp_json["body"]["uploadImage"]
    image_url = resp_json["body"]["imageUrl"]

    put_headers = {
        "Content-Type": mime_type,
        "Content-Length": str(size_bytes)
    }
    put_resp = requests.put(upload_link, headers=put_headers, data=raw_bytes)
    put_resp.raise_for_status()

    return image_url


@app.route("/try-on", methods=["POST"])
def try_on():
    try:
        data = request.get_json()

        person_b64 = data.get("person_image")
        person_mime = data.get("person_mime_type")
        cloth_b64 = data.get("clothe_image")
        cloth_mime = data.get("clothe_mime_type")

        person_url = upload_image(person_b64, person_mime)
        cloth_url = upload_image(cloth_b64, cloth_mime)

        headers = {"Content-Type": "application/json",
                   "x-api-key": LIGHTX_API_KEY}
        payload = {
            "imageUrl": person_url,
            "outfitImageUrl": cloth_url,
            "segmentationType": 2
        }

        resp = requests.post(TRYON_URL, headers=headers, json=payload)
        resp.raise_for_status()
        resp_json = resp.json()
        order_id = resp_json["body"]["orderId"]

        for i in range(10):
            status_resp = requests.post(
                STATUS_URL, headers=headers, json={"orderId": order_id})
            status_json = status_resp.json()
            body = status_json.get("body")

            if body and body.get("status") == "active" and "output" in body:
                output_url = body["output"]
                img_data = requests.get(output_url).content
                result_b64 = base64.b64encode(img_data).decode("utf-8")
                return jsonify({"status": "success", "result_image_base64": result_b64})

            elif status_json.get("status") == "FAIL":
                error_msg = status_json.get(
                    "description", "LightX API failed to process the request.")
                return jsonify({"status": "error", "error": error_msg}), 500

            time.sleep(3)

        return jsonify({"status": "error", "error": "Timeout waiting for LightX result"}), 500

    except Exception as e:
        logging.error("Exception occurred: %s", str(e))
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
