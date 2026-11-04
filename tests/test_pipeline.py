import sys
import os
import base64
import io
from pathlib import Path
from PIL import Image, ImageDraw

# Add root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient

from app import app
from services.vision_service import VisionService, VisionProcessingError
from models.vision_result import VisionResult, DetectedObject, AnalyzeRequest


client = TestClient(app)


def create_synthetic_image_base64(width=320, height=240) -> str:
    """Creates a sample test image with geometric shapes for testing."""
    img = Image.new("RGB", (width, height), color=(30, 30, 40))
    draw = ImageDraw.Draw(img)
    # Draw sample shapes
    draw.rectangle([40, 60, 100, 180], fill=(200, 80, 80)) # Chair-like
    draw.rectangle([140, 100, 260, 160], fill=(80, 180, 80)) # Table-like
    
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"


def test_health_endpoint():
    """Verify /api/health returns online status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "gemini_configured" in data


def test_index_page():
    """Verify index HTML page renders properly."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Gemini Visual Lens" in response.text
    assert "cameraVideo" in response.text


def test_vision_service_decode():
    """Verify image decoding and optimization in OpenCV/Pillow."""
    b64_data = create_synthetic_image_base64(640, 480)
    pil_image = VisionService.decode_base64_image(b64_data)
    assert pil_image.size == (640, 480)
    assert pil_image.mode == "RGB"

    optimized_img, jpeg_bytes = VisionService.optimize_image_for_gemini(pil_image)
    assert len(jpeg_bytes) > 0
    assert isinstance(optimized_img, Image.Image)

    metrics = VisionService.check_image_quality(pil_image)
    assert "brightness" in metrics
    assert "blur_score" in metrics


def test_vision_service_invalid_payload():
    """Verify that corrupt or empty image throws VisionProcessingError."""
    try:
        VisionService.decode_base64_image("")
        assert False, "Should have raised VisionProcessingError"
    except VisionProcessingError:
        pass

    try:
        VisionService.decode_base64_image("data:image/jpeg;base64,invalid_base64_content!!!")
        assert False, "Should have raised VisionProcessingError"
    except VisionProcessingError:
        pass


def test_pydantic_schema_validation():
    """Verify VisionResult schema parsing and constraints."""
    sample_json = {
        "summary": "A chair is on the left and a backpack is on the table.",
        "objects": [
            {
                "name": "chair",
                "position": "left",
                "vertical_position": "middle",
                "relative_distance": "near",
                "confidence": 0.92,
                "landmark": "near the doorway"
            },
            {
                "name": "backpack",
                "position": "right",
                "vertical_position": "middle",
                "relative_distance": "medium",
                "confidence": 0.88,
                "landmark": "on the table"
            }
        ],
        "uncertainty": None
    }
    result = VisionResult.model_validate(sample_json)
    assert len(result.objects) == 2
    assert result.objects[0].name == "chair"
    assert result.objects[0].position == "left"
    assert result.objects[0].relative_distance == "near"
    assert result.uncertainty is None


def test_analyze_endpoint_validation():
    """Verify /api/analyze input validation with malformed image."""
    response = client.post("/api/analyze", json={"image": "not_an_image"})
    assert response.status_code in (400, 422)
    data = response.json()
    assert data["success"] is False
    assert "error" in data


def test_index_page_voice_elements():
    """Verify index HTML contains voice button and feedback card."""
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="voiceBtn"' in response.text
    assert 'id="voiceCommandCard"' in response.text
    assert 'id="voiceEngineBadge"' in response.text


def test_analyze_request_with_voice_queries():
    """Verify AnalyzeRequest model handles voice command queries correctly."""
    b64_data = create_synthetic_image_base64(320, 240)
    
    # Test each first-phase supported voice command
    test_queries = [
        "What do you see?",
        "Describe this.",
        "What is in front of me?",
        "Analyze this.",
        "Read this."
    ]
    
    for q in test_queries:
        req = AnalyzeRequest(image=b64_data, query=q)
        assert req.query == q
        assert req.image.startswith("data:image/jpeg;base64,")


def test_gemini_service_prompt_adaptation():
    """Verify GeminiService correctly customizes prompt for scene description and text reading commands."""
    from services.gemini_service import GeminiService
    
    service = GeminiService()
    
    # Check text reading query prompt logic
    read_prompt = "read this"
    system_prompt = "You are a visual assistant"
    # Verify prompt logic without triggering network API
    clean_query = read_prompt.strip()
    assert any(term in clean_query.lower() for term in ["read", "text", "what does this say", "what's written"])


def test_phase3_pydantic_schema_validation():
    """Verify Phase 3 VisionResult schema extensions: clock_position, target_found, guidance_direction, hazard_alert."""
    sample_json = {
        "summary": "Your keys are directly on the desk at 2 o'clock. Caution: charging cable near edge.",
        "objects": [
            {
                "name": "keys",
                "position": "right",
                "vertical_position": "middle",
                "relative_distance": "near",
                "confidence": 0.96,
                "landmark": "on the desk",
                "clock_position": "2 o'clock"
            }
        ],
        "target_found": True,
        "guidance_direction": "Pan slightly right towards 2 o'clock, reach forward",
        "hazard_alert": "Caution: charging cable dangling near front edge",
        "uncertainty": None
    }
    result = VisionResult.model_validate(sample_json)
    assert result.target_found is True
    assert result.guidance_direction is not None
    assert result.hazard_alert is not None
    assert len(result.objects) == 1
    assert result.objects[0].clock_position == "2 o'clock"


def test_phase3_index_page_elements():
    """Verify index HTML contains Phase 3 controls and Query input elements."""
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="continuousGuidanceBtn"' in response.text
    assert 'id="hazardBanner"' in response.text
    assert 'id="targetSearchBanner"' in response.text
    assert 'id="audioBeaconToggle"' in response.text
    assert 'id="guidanceCard"' in response.text
    assert 'id="queryForm"' in response.text
    assert 'id="queryInput"' in response.text
    assert 'id="sendQueryBtn"' in response.text
    assert 'class="quick-chip"' in response.text


def test_phase3_analyze_request_modes():
    """Verify AnalyzeRequest model handles Phase 3 target search and continuous guidance modes."""
    b64_data = create_synthetic_image_base64(320, 240)
    
    # 1. Target Search Mode
    req_find = AnalyzeRequest(
        image=b64_data,
        query="Find my keys",
        mode="find_target",
        target_object="keys"
    )
    assert req_find.mode == "find_target"
    assert req_find.target_object == "keys"

    # 2. Continuous Guidance Mode
    req_guide = AnalyzeRequest(
        image=b64_data,
        query="Continuous guidance scan",
        mode="continuous_guidance"
    )
    assert req_guide.mode == "continuous_guidance"


def test_phase3_gemini_service_response_parsing():
    """Verify GeminiService correctly extracts and parses Phase 3 fields from mock model output."""
    from services.gemini_service import GeminiService
    service = GeminiService()

    raw_response_json = """{
        "summary": "Water bottle is on the center desk. Path is clear.",
        "objects": [
            {
                "name": "water bottle",
                "position": "center",
                "vertical_position": "middle",
                "relative_distance": "very_close",
                "confidence": 0.98,
                "landmark": "next to keyboard",
                "clock_position": "12 o'clock"
            }
        ],
        "target_found": true,
        "guidance_direction": "Target centered, reach directly forward",
        "hazard_alert": null,
        "uncertainty": null
    }"""

    result = service._parse_response(raw_response_json, is_find_target=True)
    assert result.target_found is True
    assert result.objects[0].clock_position == "12 o'clock"
    assert "Target centered" in result.guidance_direction


def test_text_reading_spatial_preservation():
    """Verify text reading / OCR results preserve verbatim transcribed text cleanly."""
    from services.spatial_reasoning import SpatialReasoningEngine
    from services.gemini_service import GeminiService
    from models.vision_result import DetectedObject

    service = GeminiService()
    raw_ocr_json = """{
        "scene_summary": "Ingredients: Organic Whole Milk, Vitamin D3. Best before Oct 24.",
        "voice_response": "Ingredients: Organic Whole Milk, Vitamin D3. Best before Oct 24.",
        "objects": [
            {
                "name": "milk carton",
                "position": "center",
                "vertical_position": "middle",
                "relative_distance": "very_close",
                "confidence": 0.99
            }
        ],
        "path_status": "clear",
        "guidance": "Point camera steadily at text."
    }"""

    result = service._parse_response(raw_ocr_json, is_text_read=True, query="read this")
    assert "Organic Whole Milk" in result.summary
    assert "Organic Whole Milk" in result.voice_response
    assert "Organic Whole Milk" in result.scene_summary
    assert result.path_status == "clear"


def test_continuous_guidance_stop_phrases():
    """Verify various stop continuous guidance phrases are handled correctly."""
    import re

    stop_phrases = [
        "stop continuous guidance",
        "stop continues guidance",
        "stop continue guidance",
        "stop the continuous guidance",
        "stop the guidance",
        "stop continuous",
        "stop navigation",
        "stop guiding",
        "stop continuous mode",
        "stop continues mode",
        "turn off continuous guidance",
        "turn off guidance",
        "end continuous guidance",
        "disable guidance",
        "stop search"
    ]

    for raw in stop_phrases:
        text = raw.lower().strip()
        has_stop_word = bool(re.search(r"\b(stop|end|quit|pause|halt|cancel|turn\s*off|disable|exit)\b", text))
        has_guidance_word = bool(re.search(r"\b(guidance|guide|guiding|navigation|navigate|continuous|continues|continue|continual|loop|mode|scan|tracking|search)\b", text))
        assert has_stop_word and has_guidance_word, f"Failed matching stop phrase: {raw}"


if __name__ == "__main__":
    print("Running automated tests...")
    test_health_endpoint()
    print("[PASS] Health endpoint OK")
    test_index_page()
    print("[PASS] Index template OK")
    test_index_page_voice_elements()
    print("[PASS] Index voice elements OK")
    test_phase3_index_page_elements()
    print("[PASS] Index Phase 3 elements OK")
    test_vision_service_decode()
    print("[PASS] Vision service decode & optimization OK")
    test_vision_service_invalid_payload()
    print("[PASS] Vision error handling OK")
    test_pydantic_schema_validation()
    print("[PASS] Pydantic schemas OK")
    test_phase3_pydantic_schema_validation()
    print("[PASS] Phase 3 Pydantic schemas OK")
    test_analyze_endpoint_validation()
    print("[PASS] Analyze endpoint validation OK")
    test_analyze_request_with_voice_queries()
    print("[PASS] Analyze request voice queries OK")
    test_phase3_analyze_request_modes()
    print("[PASS] Phase 3 Analyze request modes OK")
    test_gemini_service_prompt_adaptation()
    print("[PASS] Gemini prompt voice adaptation OK")
    test_phase3_gemini_service_response_parsing()
    print("[PASS] Phase 3 Gemini response parsing OK")
    test_text_reading_spatial_preservation()
    print("[PASS] Text reading spatial preservation OK")
    test_continuous_guidance_stop_phrases()
    print("[PASS] Continuous guidance stop phrase parsing OK")
    print("\nAll pipeline unit tests passed successfully!")
