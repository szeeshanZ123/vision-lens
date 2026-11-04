"""Depth and Distance Estimation Service.

Provides monocular approximate depth and metric distance estimation using
camera geometry priors, normalized bounding box scale, and real-world physical
dimension priors for recognized object classes.

Explicitly labels all metric measurements as approximate (~X meters) to maintain
honesty and safety for visually impaired navigation.
"""

import math
from typing import Optional, Tuple
from models.vision_result import BoundingBox, DetectedObject


class DepthEstimator:
    """Estimates relative proximity and approximate metric distances for detected objects."""

    # Approximate real-world heights (in meters) for standard object categories
    REAL_WORLD_HEIGHT_PRIORS = {
        "bottle": 0.24,
        "water bottle": 0.24,
        "glass": 0.14,
        "cup": 0.12,
        "mug": 0.12,
        "can": 0.12,
        "bowl": 0.10,
        "person": 1.70,
        "human": 1.70,
        "man": 1.70,
        "woman": 1.65,
        "child": 1.20,
        "chair": 0.85,
        "couch": 0.85,
        "sofa": 0.85,
        "table": 0.75,
        "desk": 0.75,
        "dining table": 0.75,
        "laptop": 0.25,
        "computer": 0.45,
        "monitor": 0.40,
        "keyboard": 0.05,
        "mouse": 0.04,
        "phone": 0.15,
        "cell phone": 0.15,
        "smartphone": 0.15,
        "keys": 0.08,
        "keychain": 0.10,
        "bag": 0.45,
        "backpack": 0.48,
        "handbag": 0.30,
        "wallet": 0.10,
        "door": 2.05,
        "doorway": 2.05,
        "window": 1.20,
        "car": 1.50,
        "vehicle": 1.50,
        "bicycle": 1.00,
        "bike": 1.00,
        "motorcycle": 1.15,
        "traffic signal": 0.90,
        "traffic light": 0.90,
        "stop sign": 0.75,
        "fire hydrant": 0.75,
        "trash can": 0.80,
        "bin": 0.80,
        "stairs": 1.50,
        "staircase": 1.50,
        "obstacle": 0.80,
        "pole": 2.50,
        "tree": 3.50,
        "plant": 0.50,
        "book": 0.24,
        "plate": 0.05,
        "clock": 0.30,
        "pill bottle": 0.09,
        "medicine": 0.09,
        "glasses": 0.05,
        "spectacles": 0.05,
        "shoe": 0.12,
        "shoes": 0.12,
    }

    DEFAULT_REAL_HEIGHT: float = 0.50  # Default 50cm prior for unknown objects

    # Normalized camera focal length approximation based on standard mobile vertical FOV (~50°)
    # f_norm = 1.0 / (2 * tan(VFOV / 2)) ≈ 1.07
    CAMERA_FOCAL_NORM: float = 1.07

    # Distance Tier Thresholds (in meters)
    VERY_CLOSE_THRESHOLD: float = 0.65
    CLOSE_THRESHOLD: float = 1.80
    MEDIUM_THRESHOLD: float = 3.80

    @classmethod
    def get_real_world_height(cls, label: str) -> float:
        """Looks up the canonical real-world height in meters for a given object label."""
        clean = (label or "").strip().lower()
        if clean in cls.REAL_WORLD_HEIGHT_PRIORS:
            return cls.REAL_WORLD_HEIGHT_PRIORS[clean]

        for key, val in cls.REAL_WORLD_HEIGHT_PRIORS.items():
            if key in clean or clean in key:
                return val

        return cls.DEFAULT_REAL_HEIGHT

    @classmethod
    def estimate_distance(
        cls,
        label: str,
        bbox: Optional[BoundingBox] = None,
        given_relative_distance: Optional[str] = None,
    ) -> Tuple[float, str, str]:
        """
        Estimates approximate distance in meters and distance category.

        Args:
            label: Detected object name/label
            bbox: Normalized bounding box [ymin, xmin, ymax, xmax]
            given_relative_distance: Optional heuristic distance from detector/model

        Returns:
            Tuple of (approximate_distance_m, distance_category, distance_display_string)
        """
        real_height = cls.get_real_world_height(label)
        
        # Calculate from bounding box height if available and non-degenerate
        if bbox and (bbox.ymax - bbox.ymin) > 0.01:
            bbox_h = max(0.02, min(1.0, bbox.ymax - bbox.ymin))
            # d = (real_height * f_norm) / bbox_h
            raw_distance = (real_height * cls.CAMERA_FOCAL_NORM) / bbox_h
            # Clamp to practical bounds
            distance_m = max(0.3, min(20.0, raw_distance))
        elif given_relative_distance:
            # Fallback to category priors if bbox is missing
            dist_map = {
                "very_close": 0.45,
                "close": 1.10,
                "near": 1.10,
                "medium": 2.60,
                "far": 5.50,
            }
            norm_key = given_relative_distance.lower().replace(" ", "_")
            distance_m = dist_map.get(norm_key, 1.20)
        else:
            distance_m = 1.20

        # Classify into standard distance category
        if distance_m < cls.VERY_CLOSE_THRESHOLD:
            category = "very_close"
        elif distance_m < cls.CLOSE_THRESHOLD:
            category = "close"
        elif distance_m < cls.MEDIUM_THRESHOLD:
            category = "medium"
        else:
            category = "far"

        # Format display string honestly
        display_str = cls.format_distance_display(distance_m)

        return round(distance_m, 2), category, display_str

    @classmethod
    def format_distance_display(cls, distance_m: float) -> str:
        """Formats approximate numeric distance into accessible natural string."""
        if distance_m < 0.95:
            val = round(distance_m, 1)
            unit = "meter" if val == 1.0 else "meters"
            if val == 1.0:
                return "~1 meter"
            return f"~{val} {unit}"
        else:
            # For 1m and above, round to nearest 0.5 or integer
            if abs(distance_m - round(distance_m)) < 0.2:
                rounded = int(round(distance_m))
                unit = "meter" if rounded == 1 else "meters"
                return f"~{rounded} {unit}"
            else:
                val = round(distance_m, 1)
                return f"~{val} meters"
