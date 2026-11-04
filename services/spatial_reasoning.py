"""Spatial Reasoning Engine & Natural Language Voice Guidance Generator.

Processes object detections, normalized bounding box coordinates, and approximate
depth estimations to determine 7-zone horizontal positioning, clock directions,
obstacle identification, walking path clearance, and concise spoken accessibility instructions.
"""

import re
from typing import List, Optional, Tuple, Dict, Any
from models.vision_result import BoundingBox, DetectedObject, VisionResult
from services.depth_estimation import DepthEstimator


class SpatialReasoningEngine:
    """Combines detections, positions, depth, and semantics into spatial guidance."""

    # 7-Zone Horizontal Thresholds (normalized 0.0 to 1.0)
    HORIZONTAL_THRESHOLDS = {
        "far_left": (0.00, 0.20),
        "left": (0.20, 0.35),
        "slightly_left": (0.35, 0.45),
        "center": (0.45, 0.55),
        "slightly_right": (0.55, 0.65),
        "right": (0.65, 0.80),
        "far_right": (0.80, 1.00),
    }

    # Vertical Thresholds (normalized 0.0 to 1.0)
    VERTICAL_THRESHOLDS = {
        "above": (0.00, 0.35),
        "middle": (0.35, 0.65),
        "below": (0.65, 1.00),
    }

    # Spatial Phrase Mappings for Voice & UI
    HORIZONTAL_PHRASES = {
        "far_left": "far to your left",
        "left": "to your left",
        "slightly_left": "slightly to your left",
        "center": "in front of you",
        "slightly_right": "slightly to your right",
        "right": "to your right",
        "far_right": "far to your right",
    }

    DIRECTION_LABELS = {
        "far_left": "far-left",
        "left": "left",
        "slightly_left": "slightly left",
        "center": "ahead",
        "slightly_right": "slightly right",
        "right": "right",
        "far_right": "far-right",
    }

    # Clock Position Mapping by Horizontal & Vertical Zone
    CLOCK_POSITIONS = {
        ("far_left", "above"): "10 o'clock",
        ("far_left", "middle"): "9 o'clock",
        ("far_left", "below"): "7–8 o'clock",
        ("left", "above"): "10 o'clock",
        ("left", "middle"): "9 o'clock",
        ("left", "below"): "8 o'clock",
        ("slightly_left", "above"): "11 o'clock",
        ("slightly_left", "middle"): "10–11 o'clock",
        ("slightly_left", "below"): "11 o'clock",
        ("center", "above"): "12 o'clock",
        ("center", "middle"): "12 o'clock",
        ("center", "below"): "12 o'clock",
        ("slightly_right", "above"): "1 o'clock",
        ("slightly_right", "middle"): "1–2 o'clock",
        ("slightly_right", "below"): "1 o'clock",
        ("right", "above"): "2 o'clock",
        ("right", "middle"): "3 o'clock",
        ("right", "below"): "4 o'clock",
        ("far_right", "above"): "2 o'clock",
        ("far_right", "middle"): "3 o'clock",
        ("far_right", "below"): "4–5 o'clock",
    }

    # Standard Obstacle Categories (items that interfere with walking if in path)
    OBSTACLE_KEYWORDS = {
        "chair", "table", "desk", "sofa", "couch", "wall", "door", "doorway",
        "person", "human", "man", "woman", "child", "stairs", "staircase", "step",
        "box", "trash can", "bin", "pole", "tree", "plant", "vehicle", "car",
        "bicycle", "bike", "motorcycle", "curb", "pillar", "obstacle", "backpack", "luggage", "suitcase"
    }

    # Small/Tabletop Items that are typically NOT walking obstacles unless lying on the floor
    NON_OBSTACLES = {
        "bottle", "water bottle", "cup", "mug", "glass", "can", "bowl", "plate",
        "keys", "keychain", "phone", "cell phone", "smartphone", "mouse", "keyboard",
        "book", "pen", "pencil", "wallet", "glasses", "spectacles", "pill bottle", "medicine"
    }

    @classmethod
    def calculate_horizontal_position(cls, xmin: float, xmax: float) -> str:
        """Calculates 7-zone horizontal category based on bounding box center."""
        center_x = max(0.0, min(1.0, (xmin + xmax) / 2.0))
        for zone, (low, high) in cls.HORIZONTAL_THRESHOLDS.items():
            if low <= center_x <= high:
                return zone
        return "center"

    @classmethod
    def calculate_vertical_position(cls, ymin: float, ymax: float) -> str:
        """Calculates vertical category based on bounding box center."""
        center_y = max(0.0, min(1.0, (ymin + ymax) / 2.0))
        for zone, (low, high) in cls.VERTICAL_THRESHOLDS.items():
            if low <= center_y <= high:
                return zone
        return "middle"

    @classmethod
    def map_to_3zone_position(cls, zone_7: str) -> str:
        """Maps 7-zone horizontal position to standard 3-zone (left, center, right)."""
        if "left" in zone_7:
            return "left"
        if "right" in zone_7:
            return "right"
        return "center"

    @classmethod
    def get_clock_position(cls, horiz_zone: str, vert_zone: str) -> str:
        """Determines clock face direction based on horizontal and vertical position."""
        return cls.CLOCK_POSITIONS.get((horiz_zone, vert_zone), "12 o'clock")

    @classmethod
    def is_obstacle_object(cls, name: str, horiz_zone: str, distance_m: Optional[float], landmark: Optional[str] = None) -> bool:
        """
        Determines whether a detected object interferes with movement.
        - Tabletop items (e.g. bottle on table) are NOT obstacles.
        - Large items (chair, table, wall, stairs, person) directly in or near path (< 2.5m) ARE obstacles.
        """
        clean_name = (name or "").strip().lower()
        clean_landmark = (landmark or "").strip().lower()

        # If it's explicitly on a table/desk/counter/shelf, it's not a walking obstacle
        if any(surf in clean_landmark for surf in ["on table", "on desk", "on counter", "on shelf", "on bed"]):
            return False

        # If it's a known small item and not explicitly on the floor
        if any(small in clean_name for small in cls.NON_OBSTACLES) and "floor" not in clean_landmark:
            return False

        # If it's a known obstacle category and in/near path (< 2.8m)
        is_known_obs = any(obs in clean_name for obs in cls.OBSTACLE_KEYWORDS)
        in_path = horiz_zone in ("center", "slightly_left", "slightly_right", "left", "right")
        dist = distance_m if distance_m is not None else 1.5

        if is_known_obs and in_path and dist <= 2.8:
            return True

        if "obstacle" in clean_name or "hazard" in clean_name:
            return True

        return False

    @classmethod
    def extract_target_from_query(cls, query: Optional[str]) -> Optional[str]:
        """Extracts target item from voice commands like 'Where is my bottle?' or 'Find keys'."""
        if not query:
            return None
        clean = query.strip()
        patterns = [
            r"^(?:where\s+is|where\s+are)\s+(?:my\s+|the\s+|a\s+|an\s+)?(.+?)(?:\?|\.|$)",
            r"^(?:find|locate|spot|search\s+for)\s+(?:my\s+|the\s+|a\s+|an\s+)?(.+?)(?:\?|\.|$)",
            r"^(?:help\s+me\s+find)\s+(?:my\s+|the\s+|a\s+|an\s+)?(.+?)(?:\?|\.|$)",
            r"^(?:look\s+for)\s+(?:my\s+|the\s+|a\s+|an\s+)?(.+?)(?:\?|\.|$)",
            r"^(?:can\s+you\s+see)\s+(?:my\s+|the\s+|a\s+|an\s+)?(.+?)(?:\?|\.|$)",
        ]
        for pat in patterns:
            match = re.search(pat, clean, re.IGNORECASE)
            if match and match.group(1):
                extracted = match.group(1).strip().rstrip("?.!").lower()
                if extracted not in ("this", "anything", "what", "something", "here", "ahead", "path"):
                    return extracted
        return None

    @classmethod
    def enrich_detected_object(cls, obj_data: Dict[str, Any]) -> DetectedObject:
        """Enriches raw detection dictionary with 7-zone spatial math, depth, and obstacle classification."""
        name = str(obj_data.get("name", "object")).strip()
        confidence = float(obj_data.get("confidence", 0.9))
        landmark = obj_data.get("landmark")

        # 1. Bounding Box extraction
        raw_box = obj_data.get("bounding_box") or obj_data.get("box_2d")
        bbox = None
        if isinstance(raw_box, dict):
            try:
                bbox = BoundingBox(
                    ymin=float(raw_box.get("ymin", 0.0)),
                    xmin=float(raw_box.get("xmin", 0.0)),
                    ymax=float(raw_box.get("ymax", 1.0)),
                    xmax=float(raw_box.get("xmax", 1.0)),
                )
            except Exception:
                bbox = None

        # 2. 7-Zone Horizontal & Vertical Positioning
        if bbox:
            horiz_zone = cls.calculate_horizontal_position(bbox.xmin, bbox.xmax)
            vert_zone = cls.calculate_vertical_position(bbox.ymin, bbox.ymax)
        else:
            raw_pos = str(obj_data.get("position", "center")).lower().replace(" ", "_")
            if "far_left" in raw_pos:
                horiz_zone = "far_left"
            elif "slightly_left" in raw_pos:
                horiz_zone = "slightly_left"
            elif "left" in raw_pos:
                horiz_zone = "left"
            elif "far_right" in raw_pos:
                horiz_zone = "far_right"
            elif "slightly_right" in raw_pos:
                horiz_zone = "slightly_right"
            elif "right" in raw_pos:
                horiz_zone = "right"
            else:
                horiz_zone = "center"

            raw_vpos = str(obj_data.get("vertical_position", "middle")).lower()
            vert_zone = "above" if "above" in raw_vpos else ("below" if "below" in raw_vpos else "middle")

        pos_3zone = cls.map_to_3zone_position(horiz_zone)
        clock_pos = obj_data.get("clock_position") or cls.get_clock_position(horiz_zone, vert_zone)
        dir_label = cls.DIRECTION_LABELS.get(horiz_zone, "ahead")

        # 3. Depth & Distance Estimation
        given_dist = obj_data.get("relative_distance") or obj_data.get("distance_category") or obj_data.get("distance")
        approx_m, dist_category, dist_display = DepthEstimator.estimate_distance(
            label=name, bbox=bbox, given_relative_distance=given_dist
        )

        clean_dist = dist_display.replace("~", "").strip()
        natural_distance = f"approximately {clean_dist}"

        # 4. Obstacle Classification
        is_obs = bool(obj_data.get("is_obstacle", False)) or cls.is_obstacle_object(
            name=name, horiz_zone=horiz_zone, distance_m=approx_m, landmark=landmark
        )

        # 5. Individual spatial instruction
        spatial_instruction = cls.generate_single_object_instruction(
            name=name, horiz_zone=horiz_zone, dist_display=dist_display, landmark=landmark, is_target=False
        )

        return DetectedObject(
            name=name,
            label=name,
            position=pos_3zone,
            horizontal_position=horiz_zone,
            direction=dir_label,
            vertical_position=vert_zone,
            relative_distance=dist_category,
            distance_category=dist_category,
            approximate_distance_m=approx_m,
            distance_display=dist_display,
            distance=natural_distance,
            is_obstacle=is_obs,
            bounding_box=bbox,
            confidence=confidence,
            landmark=landmark,
            clock_position=clock_pos,
            spatial_instruction=spatial_instruction,
        )

    @classmethod
    def generate_single_object_instruction(
        cls, name: str, horiz_zone: str, dist_display: str, landmark: Optional[str] = None, is_target: bool = False
    ) -> str:
        """Generates clean natural language sentence for an object."""
        pos_phrase = cls.HORIZONTAL_PHRASES.get(horiz_zone, "in front of you")
        clean_dist = dist_display.replace("~", "").strip()

        landmark_suffix = f", {landmark}" if landmark else ""

        if is_target:
            if horiz_zone == "center":
                return f"Your {name} is in front of you, approximately {clean_dist} away{landmark_suffix}."
            return f"Your {name} is {pos_phrase}, approximately {clean_dist} away{landmark_suffix}."

        if horiz_zone == "center":
            return f"A {name} is approximately {clean_dist} ahead{landmark_suffix}."
        return f"A {name} is {pos_phrase}, approximately {clean_dist} away{landmark_suffix}."

    @classmethod
    def process_scene_spatial_reasoning(
        cls,
        objects: List[DetectedObject],
        target_object: Optional[str] = None,
        query: Optional[str] = None,
        existing_summary: Optional[str] = None,
        hazard_alert: Optional[str] = None,
        path_status: Optional[str] = None,
        guidance: Optional[str] = None,
        is_text_reading: bool = False,
    ) -> VisionResult:
        """
        Executes top-level spatial reasoning:
        1. Evaluates target search intent (anti-hallucination + multi-object handling)
        2. Evaluates text reading / OCR intent (prioritizes extracted verbatim text)
        3. Evaluates obstacle proximity & path status (clear / partially_blocked / blocked)
        4. Generates actionable navigation guidance
        5. Synthesizes concise natural voice response and structured scene summary
        """
        effective_target = target_object or cls.extract_target_from_query(query)
        q_lower = (query or "").lower()
        is_text_mode = is_text_reading or any(
            t in q_lower for t in ["read", "text", "what does this say", "what does it say", "what's written", "what is written", "ocr"]
        )

        # -------------------------------------------------------------
        # 1. Text Reading / OCR Mode
        # -------------------------------------------------------------
        if is_text_mode and not effective_target:
            text_content = existing_summary.strip() if existing_summary and len(existing_summary.strip()) > 0 else "No readable text detected in view."
            return VisionResult(
                summary=text_content,
                scene_summary=text_content,
                path_status="clear",
                guidance=guidance or "Point camera steadily at text for additional details.",
                guidance_direction=guidance or "Point camera steadily at text for additional details.",
                voice_response=text_content,
                objects=objects,
                target_found=None,
                target_status="not_requested",
                hazard_alert=hazard_alert,
                spatial_instruction=text_content,
            )

        # -------------------------------------------------------------
        # 2. Target Search Mode (e.g. Find Bottle / Find Keys)
        # -------------------------------------------------------------
        if effective_target:
            clean_target = effective_target.strip().lower()
            matched_objects = []
            for obj in objects:
                obj_name = obj.name.lower()
                if clean_target in obj_name or obj_name in clean_target:
                    matched_objects.append(obj)

            if matched_objects:
                matched_objects.sort(key=lambda o: (o.approximate_distance_m or 99.0, -o.confidence))
                primary = matched_objects[0]
                landmark_phrase = f", {primary.landmark}" if primary.landmark else ""

                if len(matched_objects) == 1:
                    clean_d = primary.distance_display.replace("~", "").strip() if primary.distance_display else "1 meter"
                    pos_phr = cls.HORIZONTAL_PHRASES.get(primary.horizontal_position, "in front of you")
                    voice_text = f"{primary.name.capitalize()} detected {pos_phr}, approximately {clean_d} ahead{landmark_phrase}."
                else:
                    count_word = "two" if len(matched_objects) == 2 else f"{len(matched_objects)}"
                    other = matched_objects[1]
                    clean_d = primary.distance_display.replace("~", "").strip() if primary.distance_display else "1 meter"
                    voice_text = (
                        f"I see {count_word} {clean_target}s. One is {cls.HORIZONTAL_PHRASES.get(primary.horizontal_position, 'in front of you')}, "
                        f"and the other is {cls.HORIZONTAL_PHRASES.get(other.horizontal_position, 'nearby')}. "
                        f"The closest one is approximately {clean_d} away{landmark_phrase}."
                    )

                # Directional Pan Guidance
                if primary.horizontal_position in ("far_left", "left", "slightly_left"):
                    guidance_text = f"Pan camera left towards {primary.clock_position or '10 o\'clock'}"
                elif primary.horizontal_position in ("far_right", "right", "slightly_right"):
                    guidance_text = f"Pan camera right towards {primary.clock_position or '2 o\'clock'}"
                else:
                    guidance_text = "Target centered, reach forward"

                return VisionResult(
                    summary=voice_text,
                    scene_summary=voice_text,
                    path_status="clear",
                    guidance=guidance_text,
                    guidance_direction=guidance_text,
                    voice_response=voice_text,
                    objects=objects,
                    target_found=True,
                    target_status="found",
                    hazard_alert=hazard_alert,
                    spatial_instruction=voice_text,
                )
            else:
                # Anti-Hallucination: Target not in frame
                not_found_msg = f"I don't see a {clean_target} in the visible area. Please move the camera slowly."
                return VisionResult(
                    summary=not_found_msg,
                    scene_summary=not_found_msg,
                    path_status="uncertain",
                    guidance="Pan camera slowly around the room",
                    guidance_direction="Pan camera slowly around the room",
                    voice_response=not_found_msg,
                    objects=objects,
                    target_found=False,
                    target_status="not_found",
                    hazard_alert=hazard_alert,
                    spatial_instruction=not_found_msg,
                )

        # -------------------------------------------------------------
        # 2. Path Status & Obstacle Analysis
        # -------------------------------------------------------------
        obstacles_in_path = [o for o in objects if o.is_obstacle]
        center_close_obs = [
            o for o in obstacles_in_path
            if o.horizontal_position in ("center", "slightly_left", "slightly_right")
            and (o.approximate_distance_m or 1.5) <= 2.2
        ]

        computed_path_status = path_status or "clear"
        computed_guidance = guidance

        if center_close_obs:
            closest_obs = min(center_close_obs, key=lambda o: o.approximate_distance_m or 99.0)
            dist_val = closest_obs.approximate_distance_m or 1.5
            clean_d = closest_obs.distance_display.replace("~", "").strip() if closest_obs.distance_display else "1.5 meters"

            if dist_val <= 1.2 or "wall" in closest_obs.name.lower():
                computed_path_status = "blocked"
                computed_guidance = f"Stop. {closest_obs.name.capitalize()} directly ahead approximately {clean_d}."
            else:
                computed_path_status = "partially_blocked"
                # Determine freer side
                if closest_obs.horizontal_position in ("center", "slightly_right"):
                    computed_guidance = f"Move slightly left. The {closest_obs.name} is approximately {clean_d} ahead."
                else:
                    computed_guidance = f"Move slightly right. The {closest_obs.name} is approximately {clean_d} ahead."
        elif obstacles_in_path:
            computed_path_status = "clear"
            computed_guidance = "Continue forward. The path appears clear."
        else:
            computed_path_status = "clear"
            computed_guidance = "Path is clear ahead."

        # -------------------------------------------------------------
        # 3. Empty Scene Handling (Honest, Non-Generic)
        # -------------------------------------------------------------
        if not objects:
            empty_msg = "No significant objects or obstacles detected in the visible area. The path ahead appears clear."
            final_summary = existing_summary if existing_summary and len(existing_summary) > 15 and "scene analyzed" not in existing_summary.lower() else empty_msg
            return VisionResult(
                summary=final_summary,
                scene_summary=final_summary,
                path_status="clear",
                guidance="Continue forward. The path appears clear.",
                guidance_direction="Continue forward. The path appears clear.",
                voice_response=final_summary,
                objects=[],
                target_found=None,
                target_status="not_requested",
                hazard_alert=hazard_alert,
                spatial_instruction=final_summary,
            )

        # -------------------------------------------------------------
        # 4. Scene Summary & Voice Response Synthesis
        # -------------------------------------------------------------
        # Sort objects by proximity and prominence
        sorted_objs = sorted(objects, key=lambda o: (o.approximate_distance_m or 99.0, -o.confidence))
        
        object_sentences = []
        for obj in sorted_objs[:3]:
            object_sentences.append(
                cls.generate_single_object_instruction(
                    name=obj.name,
                    horiz_zone=obj.horizontal_position,
                    dist_display=obj.distance_display or "~1 meter",
                    landmark=obj.landmark,
                    is_target=False,
                )
            )

        # Path clearance sentence
        if computed_path_status == "clear":
            path_sentence = "The path ahead appears clear."
        elif computed_path_status == "partially_blocked":
            path_sentence = "The path ahead is partially blocked."
        elif computed_path_status == "blocked":
            path_sentence = "The path ahead is blocked."
        else:
            path_sentence = ""

        # Construct comprehensive Scene Summary
        scene_summary_parts = object_sentences.copy()
        if path_sentence:
            scene_summary_parts.append(path_sentence)

        constructed_summary = " ".join(scene_summary_parts)
        
        if existing_summary and len(existing_summary.strip()) > 15 and "scene analyzed" not in existing_summary.lower():
            # If the model provided a rich environmental description, blend it seamlessly
            scene_summary_text = f"{constructed_summary} {existing_summary}"
        else:
            scene_summary_text = constructed_summary

        # Concise voice response: 1-2 primary objects + guidance
        voice_parts = []
        if sorted_objs:
            primary_obj = sorted_objs[0]
            clean_d = primary_obj.distance_display.replace("~", "").strip() if primary_obj.distance_display else "1 meter"
            pos_phr = cls.HORIZONTAL_PHRASES.get(primary_obj.horizontal_position, "ahead")
            voice_parts.append(f"{primary_obj.name.capitalize()} is {pos_phr}, about {clean_d} ahead.")
            
            if len(sorted_objs) > 1:
                sec_obj = sorted_objs[1]
                sec_d = sec_obj.distance_display.replace("~", "").strip() if sec_obj.distance_display else "1.5 meters"
                sec_pos = cls.HORIZONTAL_PHRASES.get(sec_obj.horizontal_position, "nearby")
                voice_parts.append(f"{sec_obj.name.capitalize()} is {sec_pos}, about {sec_d} away.")

        if computed_guidance:
            voice_parts.append(computed_guidance)

        concise_voice_response = " ".join(voice_parts)

        return VisionResult(
            summary=scene_summary_text,
            scene_summary=scene_summary_text,
            path_status=computed_path_status,
            guidance=computed_guidance,
            guidance_direction=computed_guidance,
            voice_response=concise_voice_response,
            objects=objects,
            target_found=None,
            target_status="not_requested",
            hazard_alert=hazard_alert,
            spatial_instruction=concise_voice_response,
        )
