"""Gemini Vision AI Service using the official Google GenAI Python SDK.

Fast, structured spatial intelligence engine with bounding box extraction,
depth estimation, obstacle identification, path analysis, and spatial guidance.
"""

import os
import json
import re
from typing import Optional, List, Dict, Any
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from models.vision_result import VisionResult, DetectedObject, BoundingBox
from services.spatial_reasoning import SpatialReasoningEngine
from services.depth_estimation import DepthEstimator


class GeminiConfigurationError(Exception):
    """Raised when the Gemini API key is missing or not configured."""
    pass


class GeminiAnalysisError(Exception):
    """Raised when the Gemini API call fails or returns an invalid payload."""
    pass


SYSTEM_PROMPT = """You are an advanced real-time AI spatial visual assistant for visually impaired users.
Analyze the camera image carefully and provide specific, actionable spatial understanding of the visible environment.

DO NOT return generic statements like "Scene analyzed" or "Path is clear ahead" without checking the image.
If the scene genuinely contains no objects or obstacles, state "No significant objects or obstacles detected in the visible area."

For every visible object in the scene, identify:
- name: clear object label (e.g. "table", "chair", "bottle", "person", "bag", "laptop", "door", "wall", "stairs")
- bounding_box: normalized {"ymin": float, "xmin": float, "ymax": float, "xmax": float} from 0.0 to 1.0
- direction: intuitive direction ("ahead", "slightly left", "slightly right", "left", "right", "far-left", "far-right")
- clock_position: clock direction relative to user ("12 o'clock", "1–2 o'clock", "3 o'clock", "4–5 o'clock", "10–11 o'clock", "9 o'clock", "7–8 o'clock")
- distance: approximate distance string (e.g. "approximately 1 meter", "about 2 meters ahead", "1–2 meters away", or "a short distance ahead")
- is_obstacle: boolean (true if it interferes with walking path like a chair/table/wall/person/stairs directly ahead; false for small items like bottles on tables or side walls)
- landmark: placement context (e.g. "on the table", "on the floor", "next to chair", or null)
- confidence: score between 0.0 and 1.0

Path & Navigation Analysis:
- path_status: "clear", "partially_blocked", "blocked", or "uncertain"
- guidance: short actionable instruction (e.g. "Move slightly left to avoid the table.", "Continue forward. The path appears clear.", "Stop. Obstacle directly ahead.")

You MUST respond ONLY with valid JSON matching this exact structure:
{
  "scene_summary": "A table is approximately 2 meters ahead. A chair is slightly to your right, about 1.5 meters away. A bottle is on the table. The path on your left appears clear.",
  "path_status": "partially_blocked",
  "guidance": "Move slightly left to avoid the table.",
  "objects": [
    {
      "name": "table",
      "bounding_box": {"ymin": 0.35, "xmin": 0.35, "ymax": 0.85, "xmax": 0.65},
      "direction": "ahead",
      "clock_position": "12 o'clock",
      "distance": "approximately 2 meters",
      "is_obstacle": true,
      "landmark": "in walking path",
      "confidence": 0.95
    },
    {
      "name": "chair",
      "bounding_box": {"ymin": 0.40, "xmin": 0.60, "ymax": 0.80, "xmax": 0.80},
      "direction": "slightly right",
      "clock_position": "1–2 o'clock",
      "distance": "approximately 1.5 meters",
      "is_obstacle": false,
      "landmark": "next to table",
      "confidence": 0.92
    },
    {
      "name": "bottle",
      "bounding_box": {"ymin": 0.30, "xmin": 0.45, "ymax": 0.45, "xmax": 0.55},
      "direction": "ahead",
      "clock_position": "12 o'clock",
      "distance": "approximately 2 meters",
      "is_obstacle": false,
      "landmark": "on the table",
      "confidence": 0.96
    }
  ],
  "voice_response": "A table is ahead about 2 meters away. Move slightly left to avoid it.",
  "target_found": true,
  "hazard_alert": null,
  "uncertainty": null
}"""


class GeminiService:
    """Service to interact with Google Gemini Vision models with Spatial Reasoning."""

    # Default to ultra-fast low-latency multimodal model
    DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    FALLBACK_MODELS = [
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.1-pro-preview",
        "gemini-flash-latest",
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key or self.api_key.strip() in ("", "YOUR_GEMINI_API_KEY_HERE"):
            self.client = None
        else:
            self._init_client()

    def _init_client(self):
        if not GENAI_AVAILABLE:
            raise GeminiConfigurationError("The google-genai library is not installed.")
        self.client = genai.Client(api_key=self.api_key)

    def is_configured(self) -> bool:
        """Returns True if a valid API key is present and client initialized."""
        current_env_key = os.getenv("GEMINI_API_KEY")
        if current_env_key and current_env_key != self.api_key and current_env_key != "YOUR_GEMINI_API_KEY_HERE":
            self.api_key = current_env_key
            self._init_client()
        return bool(self.client and self.api_key and self.api_key != "YOUR_GEMINI_API_KEY_HERE")

    def analyze_scene(
        self,
        image: Image.Image,
        query: Optional[str] = None,
        mode: Optional[str] = "standard",
        target_object: Optional[str] = None,
    ) -> VisionResult:
        """
        Sends camera frame to Gemini Vision with rapid spatial prompts,
        then processes through SpatialReasoningEngine and DepthEstimator.
        """
        if not self.is_configured():
            raise GeminiConfigurationError(
                "Gemini API key is not configured. Please add your GEMINI_API_KEY to the .env file."
            )

        prompt = SYSTEM_PROMPT

        clean_query = (query or "").strip()
        q_lower = clean_query.lower()

        extracted_target = target_object or SpatialReasoningEngine.extract_target_from_query(clean_query)
        is_find_target = mode == "find_target" or bool(extracted_target)
        is_text_read = mode == "text_reading" or any(
            term in q_lower for term in [
                "read", "text", "what does this say", "what does it say", "what's written",
                "what is written", "ocr", "words", "sign", "label", "document", "read this",
                "read out", "read aloud"
            ]
        )
        is_continuous = mode == "continuous_guidance" or "guidance" in q_lower or "navigate" in q_lower

        if is_find_target:
            target_name = extracted_target or re.sub(r"^(find|where is|where are|locate|spot|my)\s+", "", clean_query, flags=re.IGNORECASE).strip()
            prompt += (
                f"\n\n--- TARGET SEARCH TASK: '{target_name}' ---\n"
                f"1. Check if '{target_name}' is visible in the frame.\n"
                f"2. If visible, specify its bounding_box, direction, distance, and surface placement in objects list.\n"
                f"3. If NOT visible, set 'target_found': false and state in voice_response: 'I don't see {target_name} in the visible area.'"
            )
        elif is_text_read:
            prompt += (
                f"\n\n--- TEXT READING & OCR EXTRACTION TASK ---\n"
                f"1. Carefully read and extract ALL visible text, signage, labels, packaging, notices, books, screens, or documents verbatim.\n"
                f"2. In 'scene_summary' and 'voice_response', provide the exact transcribed text clearly and naturally so it can be read aloud directly.\n"
                f"3. If there are headings, prices, or ingredients, preserve their logical reading order.\n"
                f"4. If NO readable text is detected, clearly state: 'No readable text detected in the visible area.' in 'scene_summary' and 'voice_response'.\n"
                f"5. In 'objects', list any text-bearing objects with bounding boxes."
            )
        elif is_continuous:
            prompt += (
                f"\n\n--- FAST CONTINUOUS GUIDANCE TASK ---\n"
                "Provide a short micro-guidance (under 12 words) focusing on immediate obstacles and path clearance."
            )
        elif clean_query and clean_query.lower() not in ("what do you see?", "describe", "explain"):
            prompt += f"\n\nUser Question: '{clean_query}'. Answer specifically in 'scene_summary' and 'voice_response'."

        # Try fast primary model, then fallbacks
        models_to_try = [self.DEFAULT_MODEL] + [m for m in self.FALLBACK_MODELS if m != self.DEFAULT_MODEL]
        last_err = None

        for model_name in models_to_try:
            try:
                response_text = self._call_gemini(image, prompt, model=model_name)
                return self._parse_response(
                    response_text,
                    target_object=extracted_target,
                    query=clean_query,
                    is_find_target=is_find_target,
                    is_text_read=is_text_read
                )
            except Exception as err:
                last_err = err
                continue

        raise GeminiAnalysisError(f"Gemini API analysis failed: {str(last_err)}") from last_err

    def _call_gemini(self, image: Image.Image, prompt: str, model: str) -> str:
        """Invokes Gemini generate_content API with robust configuration."""
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=1000,
            )
            response = self.client.models.generate_content(
                model=model,
                contents=[image, prompt],
                config=config,
            )
            if not response or not response.text:
                raise GeminiAnalysisError("Gemini returned an empty response.")
            return response.text
        except Exception as e:
            raise e

    def _parse_response(
        self,
        text: str,
        target_object: Optional[str] = None,
        query: Optional[str] = None,
        is_find_target: bool = False,
        is_text_read: bool = False,
    ) -> VisionResult:
        """Cleans JSON, enriches bounding boxes and distances, and runs spatial reasoning."""
        clean_text = text.strip()
        if clean_text.startswith("```"):
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text)

        data = {}
        try:
            data = json.loads(clean_text)
        except json.JSONDecodeError:
            # Try partial JSON recovery
            try:
                start_idx = clean_text.find("{")
                if start_idx != -1:
                    partial = clean_text[start_idx:]
                    summary_match = re.search(r'"(?:scene_summary|summary)"\s*:\s*"([^"]+)"', partial)
                    summary_val = summary_match.group(1) if summary_match else None
                    
                    objs_match = re.findall(
                        r'\{\s*"name"\s*:\s*"([^"]+)"[^}]*?"direction"\s*:\s*"([^"]+)"[^}]*?\}',
                        partial
                    )
                    recovered_objs = []
                    for name_val, pos_val in objs_match:
                        recovered_objs.append({"name": name_val, "position": pos_val})
                    
                    data = {
                        "scene_summary": summary_val or "Visual scene analyzed.",
                        "objects": recovered_objs
                    }
            except Exception:
                data = {}

        if not data:
            clean_summary = re.sub(r'[{}\[\]""]', '', clean_text)[:250].strip()
            return VisionResult(
                summary=clean_summary or "No significant objects detected.",
                scene_summary=clean_summary,
                path_status="clear",
                guidance="Path is clear ahead.",
                guidance_direction="Path is clear ahead.",
                voice_response=clean_summary,
                objects=[],
                uncertainty=None,
                spatial_instruction=clean_summary,
            )

        raw_objects = data.get("objects", []) or data.get("detected_objects", []) or []
        if not isinstance(raw_objects, list):
            raw_objects = []

        # Enrich every detected object with 7-zone spatial math, depth estimation, and obstacle detection
        enriched_objects: List[DetectedObject] = []
        for raw_obj in raw_objects:
            if not isinstance(raw_obj, dict):
                continue
            enriched = SpatialReasoningEngine.enrich_detected_object(raw_obj)
            enriched_objects.append(enriched)

        existing_summary = data.get("scene_summary") or data.get("summary")
        if existing_summary and (existing_summary.strip().startswith("{") or "{" in existing_summary):
            existing_summary = None

        # Pass through top-level Spatial Reasoning Engine
        reasoning_result = SpatialReasoningEngine.process_scene_spatial_reasoning(
            objects=enriched_objects,
            target_object=target_object,
            query=query,
            existing_summary=existing_summary,
            hazard_alert=data.get("hazard_alert"),
            path_status=data.get("path_status"),
            guidance=data.get("guidance") or data.get("guidance_direction"),
            is_text_reading=is_text_read,
        )

        # Preserve explicit model fields if provided in response
        if "target_found" in data and data["target_found"] is not None:
            reasoning_result.target_found = bool(data["target_found"])
            reasoning_result.target_status = "found" if reasoning_result.target_found else "not_found"
        elif is_find_target and reasoning_result.target_found is None:
            reasoning_result.target_found = len(enriched_objects) > 0
            reasoning_result.target_status = "found" if reasoning_result.target_found else "not_found"

        if data.get("guidance_direction") or data.get("guidance"):
            guidance_val = data.get("guidance_direction") or data.get("guidance")
            reasoning_result.guidance_direction = guidance_val
            reasoning_result.guidance = guidance_val

        if data.get("voice_response"):
            reasoning_result.voice_response = data["voice_response"]
            reasoning_result.spatial_instruction = data["voice_response"]
            if is_text_read and (not reasoning_result.scene_summary or reasoning_result.scene_summary == "No readable text detected in view."):
                reasoning_result.scene_summary = data["voice_response"]
                reasoning_result.summary = data["voice_response"]

        if data.get("uncertainty"):
            reasoning_result.uncertainty = data.get("uncertainty")

        return reasoning_result
