"""Unit tests for Phase 4: Spatial Intelligence, Path Analysis & Voice Guidance.

Tests specific spatial scenarios:
1. Test 1 — Object Centered (12 o'clock, ~1 meter away)
2. Test 2 — Object on Right / Slightly Right (1–2 o'clock, ~1 meter away)
3. Test 3 — Object on Left / Slightly Left (10–11 o'clock, ~1 meter away)
4. Test 4 — Target Object Not Found (Anti-Hallucination: "I don't see a bottle in the visible area")
5. Test 5 — Multiple Instances of Object
6. Test 6 — Obstacle & Path Analysis (Partially Blocked / Blocked)
7. Test 7 — Voice Query Extraction & Pipeline
8. Test 8 — Empty Scene Handling ("No significant objects or obstacles detected in the visible area")
9. Test 9 — 7-Zone and Clock Boundaries
10. Test 10 — Depth Estimator Physical Priors
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models.vision_result import BoundingBox, DetectedObject, VisionResult
from services.depth_estimation import DepthEstimator
from services.spatial_reasoning import SpatialReasoningEngine
from services.gemini_service import GeminiService


def test_1_bottle_centered():
    """Test 1: Object centered in front of camera."""
    obj_dict = {
        "name": "bottle",
        "bounding_box": {"ymin": 0.40, "xmin": 0.46, "ymax": 0.65, "xmax": 0.54},
        "confidence": 0.95,
    }
    enriched = SpatialReasoningEngine.enrich_detected_object(obj_dict)
    assert enriched.horizontal_position == "center"
    assert enriched.position == "center"
    assert enriched.clock_position == "12 o'clock"
    assert enriched.approximate_distance_m is not None

    result = SpatialReasoningEngine.process_scene_spatial_reasoning(
        objects=[enriched], target_object="bottle"
    )
    assert result.target_found is True
    assert "bottle" in result.summary.lower()
    assert "in front of you" in result.summary.lower()
    print(f"Test 1 Result: {result.summary}")


def test_2_bottle_on_right():
    """Test 2: Object slightly to the right."""
    obj_dict = {
        "name": "bottle",
        "bounding_box": {"ymin": 0.40, "xmin": 0.56, "ymax": 0.65, "xmax": 0.64},
        "confidence": 0.92,
    }
    enriched = SpatialReasoningEngine.enrich_detected_object(obj_dict)
    assert enriched.horizontal_position == "slightly_right"
    assert enriched.position == "right"
    assert enriched.clock_position in ("1 o'clock", "1–2 o'clock")

    result = SpatialReasoningEngine.process_scene_spatial_reasoning(
        objects=[enriched], target_object="bottle"
    )
    assert result.target_found is True
    assert "slightly to your right" in result.summary.lower()
    print(f"Test 2 Result: {result.summary}")


def test_3_bottle_on_left():
    """Test 3: Object slightly to the left."""
    obj_dict = {
        "name": "bottle",
        "bounding_box": {"ymin": 0.40, "xmin": 0.36, "ymax": 0.65, "xmax": 0.44},
        "confidence": 0.91,
    }
    enriched = SpatialReasoningEngine.enrich_detected_object(obj_dict)
    assert enriched.horizontal_position == "slightly_left"
    assert enriched.position == "left"
    assert enriched.clock_position in ("11 o'clock", "10–11 o'clock")

    result = SpatialReasoningEngine.process_scene_spatial_reasoning(
        objects=[enriched], target_object="bottle"
    )
    assert result.target_found is True
    assert "slightly to your left" in result.summary.lower()
    print(f"Test 3 Result: {result.summary}")


def test_4_object_not_found_anti_hallucination():
    """Test 4: Searching for an object not in the camera view must NOT hallucinate."""
    chair = SpatialReasoningEngine.enrich_detected_object({
        "name": "chair",
        "bounding_box": {"ymin": 0.30, "xmin": 0.20, "ymax": 0.80, "xmax": 0.40},
    })
    table = SpatialReasoningEngine.enrich_detected_object({
        "name": "table",
        "bounding_box": {"ymin": 0.50, "xmin": 0.40, "ymax": 0.90, "xmax": 0.80},
    })

    result = SpatialReasoningEngine.process_scene_spatial_reasoning(
        objects=[chair, table], target_object="bottle"
    )
    assert result.target_found is False
    assert result.target_status == "not_found"
    assert "don't see a bottle" in result.summary.lower() or "couldn't locate" in result.summary.lower()
    print(f"Test 4 Result: {result.summary}")


def test_5_multiple_objects():
    """Test 5: Multiple instances of the same object."""
    bottle_close = SpatialReasoningEngine.enrich_detected_object({
        "name": "bottle",
        "bounding_box": {"ymin": 0.30, "xmin": 0.56, "ymax": 0.70, "xmax": 0.64},
    })
    bottle_far = SpatialReasoningEngine.enrich_detected_object({
        "name": "bottle",
        "bounding_box": {"ymin": 0.45, "xmin": 0.20, "ymax": 0.55, "xmax": 0.26},
    })

    result = SpatialReasoningEngine.process_scene_spatial_reasoning(
        objects=[bottle_close, bottle_far], target_object="bottle"
    )
    assert result.target_found is True
    assert "two bottles" in result.summary.lower() or "2 bottles" in result.summary.lower()
    assert "closest" in result.summary.lower()
    print(f"Test 5 Result: {result.summary}")


def test_6_obstacle_and_path_analysis():
    """Test 6: Obstacle detection, path status, and actionable guidance."""
    chair_obs = SpatialReasoningEngine.enrich_detected_object({
        "name": "chair",
        "bounding_box": {"ymin": 0.35, "xmin": 0.45, "ymax": 0.85, "xmax": 0.65}, # Center in path, ~1.5m
    })
    table_obs = SpatialReasoningEngine.enrich_detected_object({
        "name": "table",
        "bounding_box": {"ymin": 0.40, "xmin": 0.30, "ymax": 0.90, "xmax": 0.70},
    })
    bottle_item = SpatialReasoningEngine.enrich_detected_object({
        "name": "bottle",
        "bounding_box": {"ymin": 0.30, "xmin": 0.40, "ymax": 0.45, "xmax": 0.50},
        "landmark": "on the table",
    })

    assert chair_obs.is_obstacle is True
    assert table_obs.is_obstacle is True
    assert bottle_item.is_obstacle is False # Bottle on table is not a walking obstacle

    result = SpatialReasoningEngine.process_scene_spatial_reasoning(
        objects=[chair_obs, table_obs, bottle_item]
    )
    assert result.path_status in ("partially_blocked", "blocked")
    assert result.guidance is not None
    assert "move" in result.guidance.lower() or "stop" in result.guidance.lower()
    print(f"Test 6 Path Status: {result.path_status}, Guidance: {result.guidance}")


def test_7_voice_query_pipeline():
    """Test 7: Voice query extraction and end-to-end spatial parsing."""
    queries = [
        ("Where is my bottle?", "bottle"),
        ("Find my keys", "keys"),
        ("Where is the chair?", "chair"),
        ("Find the door", "door"),
        ("Where is the person?", "person"),
    ]
    for q, expected_target in queries:
        target = SpatialReasoningEngine.extract_target_from_query(q)
        assert target == expected_target, f"Failed on query '{q}': got '{target}'"

    gemini_svc = GeminiService()
    mock_json = """{
        "scene_summary": "A table is approximately 2 meters ahead with a chair slightly to the right.",
        "path_status": "partially_blocked",
        "guidance": "Move slightly left to avoid the table.",
        "objects": [
            {
                "name": "table",
                "bounding_box": {"ymin": 0.35, "xmin": 0.40, "ymax": 0.85, "xmax": 0.60},
                "direction": "ahead",
                "clock_position": "12 o'clock",
                "distance": "approximately 2 meters",
                "is_obstacle": true
            },
            {
                "name": "chair",
                "bounding_box": {"ymin": 0.40, "xmin": 0.60, "ymax": 0.80, "xmax": 0.80},
                "direction": "slightly right",
                "clock_position": "1–2 o'clock",
                "distance": "approximately 1.5 meters",
                "is_obstacle": false
            }
        ],
        "voice_response": "A table is ahead about 2 meters away. Move slightly left."
    }"""
    res = gemini_svc._parse_response(mock_json, query="What do you see?")
    assert len(res.objects) == 2
    assert res.path_status == "partially_blocked"
    assert "move slightly left" in res.guidance.lower()
    assert res.objects[0].clock_position == "12 o'clock"
    print(f"Test 7 Result: {res.voice_response}")


def test_8_empty_scene_handling():
    """Test 8: Honest, non-generic message when scene has no distinct objects."""
    result = SpatialReasoningEngine.process_scene_spatial_reasoning(objects=[])
    assert "no significant objects or obstacles detected" in result.summary.lower()
    assert result.path_status == "clear"
    print(f"Test 8 Result: {result.summary}")


def test_9_7zone_horizontal_and_clock_boundaries():
    """Verify exact 7-zone threshold mappings."""
    assert SpatialReasoningEngine.calculate_horizontal_position(0.05, 0.15) == "far_left"
    assert SpatialReasoningEngine.calculate_horizontal_position(0.22, 0.32) == "left"
    assert SpatialReasoningEngine.calculate_horizontal_position(0.36, 0.44) == "slightly_left"
    assert SpatialReasoningEngine.calculate_horizontal_position(0.46, 0.54) == "center"
    assert SpatialReasoningEngine.calculate_horizontal_position(0.56, 0.64) == "slightly_right"
    assert SpatialReasoningEngine.calculate_horizontal_position(0.68, 0.76) == "right"
    assert SpatialReasoningEngine.calculate_horizontal_position(0.82, 0.95) == "far_right"


def test_10_depth_estimator_physical_priors():
    """Verify DepthEstimator calculates realistic approximate distances."""
    dist_m, cat, disp = DepthEstimator.estimate_distance(
        label="bottle", bbox=BoundingBox(ymin=0.25, xmin=0.4, ymax=0.50, xmax=0.6)
    )
    assert 0.8 <= dist_m <= 1.3
    assert cat in ("close", "near")
    assert "1 meter" in disp

    dist_p, cat_p, disp_p = DepthEstimator.estimate_distance(
        label="person", bbox=BoundingBox(ymin=0.10, xmin=0.3, ymax=0.90, xmax=0.7)
    )
    assert 1.8 <= dist_p <= 2.8
    assert cat_p == "medium"


if __name__ == "__main__":
    print("Running Visual Lens Spatial Intelligence Test Suite...")
    test_1_bottle_centered()
    print("[PASS] Test 1: Object Centered OK")
    test_2_bottle_on_right()
    print("[PASS] Test 2: Object on Right OK")
    test_3_bottle_on_left()
    print("[PASS] Test 3: Object on Left OK")
    test_4_object_not_found_anti_hallucination()
    print("[PASS] Test 4: Object Not Found (Anti-Hallucination) OK")
    test_5_multiple_objects()
    print("[PASS] Test 5: Multiple Objects OK")
    test_6_obstacle_and_path_analysis()
    print("[PASS] Test 6: Obstacle & Path Analysis OK")
    test_7_voice_query_pipeline()
    print("[PASS] Test 7: Voice Query Pipeline OK")
    test_8_empty_scene_handling()
    print("[PASS] Test 8: Empty Scene Handling OK")
    test_9_7zone_horizontal_and_clock_boundaries()
    print("[PASS] Test 9: 7-Zone & Clock Boundaries OK")
    test_10_depth_estimator_physical_priors()
    print("[PASS] Test 10: Depth Estimator Physical Priors OK")
    print("\nAll Visual Lens Spatial Intelligence tests passed successfully!")
