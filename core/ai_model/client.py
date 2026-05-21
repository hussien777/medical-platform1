import requests
from django.conf import settings


def format_ai_result(ai_response):
    """
    Convert AI API JSON response into readable text
    to store inside ai_result field.
    """

    result = ai_response.get("result", {})

    class_name = result.get("class_name", "Unknown")
    confidence = result.get("confidence", 0)
    probabilities = result.get("probabilities", {})

    confidence_percent = round(confidence * 100, 2)

    lines = [
        f"AI Prediction: {class_name}",
        f"Confidence: {confidence_percent}%",
        "",
        "Probabilities:"
    ]

    for disease_class, probability in probabilities.items():
        probability_percent = round(probability * 100, 2)
        lines.append(f"- {disease_class}: {probability_percent}%")

    return "\n".join(lines)


def send_scan_to_ai_model(uploaded_image):
    """
    Send uploaded eye scan image to external AI model API.

    Django receives the image as: uploaded_image
    AI API expects the image as: file
    """

    try:
        uploaded_image.seek(0)

        files = {
            "file": (
                uploaded_image.name,
                uploaded_image,
                uploaded_image.content_type
            )
        }

        response = requests.post(
          settings.AI_MODEL_PREDICT_URL,
          files=files,
          timeout=settings.AI_MODEL_TIMEOUT,
          headers={
          "ngrok-skip-browser-warning": "true"
    }
)

        response_data = response.json()

        if response.status_code != 200:
            return {
                "success": False,
                "ai_result": f"AI model request failed. Status code: {response.status_code}",
                "raw_response": response_data
            }

        if response_data.get("success") is True:
            return {
                "success": True,
                "ai_result": format_ai_result(response_data),
                "raw_response": response_data
            }

        error_code = response_data.get("code", "UNKNOWN_ERROR")
        error_message = response_data.get("message", "Unknown AI model error")

        return {
            "success": False,
            "ai_result": f"AI analysis failed: {error_code} - {error_message}",
            "raw_response": response_data
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "ai_result": "AI analysis failed: AI model request timed out.",
            "raw_response": None
        }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "ai_result": "AI analysis failed: Could not connect to AI model API.",
            "raw_response": None
        }

    except Exception as e:
        return {
            "success": False,
            "ai_result": f"AI analysis failed: {str(e)}",
            "raw_response": None
        }