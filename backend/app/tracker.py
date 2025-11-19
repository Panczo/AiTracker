"""Vehicle detection and tracking using YOLOv11."""
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict
from ultralytics import YOLO
from app.config import (
    YOLO_MODEL,
    YOLO_CONFIDENCE,
    YOLO_IOU,
    COCO_TO_VEHICLE,
    MODELS_DIR,
)


class VehicleTracker:
    """Handles vehicle detection and tracking using YOLO."""

    def __init__(self, counting_line=None):
        """
        Initialize YOLO model and tracking data structures.

        Args:
            counting_line: Tuple of ((x1, y1), (x2, y2)) defining the counting line,
                          or None for no line crossing detection
        """
        self.model_path = MODELS_DIR / YOLO_MODEL
        self.model = None
        self.tracked_vehicles = {}  # track_id -> vehicle info
        self.vehicle_counts = defaultdict(int)
        self.counting_line = counting_line
        self.crossed_vehicles = set()  # Track IDs that crossed the line
        self.vehicle_positions = {}  # track_id -> previous position for line crossing detection

    def load_model(self):
        """Load YOLO model."""
        if self.model is None:
            # Download model if not exists
            if not self.model_path.exists():
                print(f"Downloading YOLO model: {YOLO_MODEL}")
                self.model = YOLO(YOLO_MODEL)
                # Model will be auto-downloaded by ultralytics
            else:
                self.model = YOLO(str(self.model_path))

            print(f"YOLO model loaded: {YOLO_MODEL}")

    def classify_vehicle(self, coco_class: int, bbox_area: float) -> str:
        """
        Classify vehicle based on COCO class and size.

        Args:
            coco_class: COCO dataset class ID
            bbox_area: Bounding box area (can be used for size-based classification)

        Returns:
            Vehicle category name
        """
        # Basic mapping from COCO to our categories
        vehicle_type = COCO_TO_VEHICLE.get(coco_class, 'inne')

        # TODO: Add size-based refinement for trucks
        # Example: Large trucks vs delivery vans based on bbox_area
        # if vehicle_type == 'samochod_dostawczy' and bbox_area > THRESHOLD:
        #     vehicle_type = 'samochod_ciezarowy'

        return vehicle_type

    def check_line_crossing(self, track_id: int, current_center: Tuple[float, float]) -> bool:
        """
        Check if a vehicle crossed the counting line.

        Args:
            track_id: Vehicle track ID
            current_center: Current center position (x, y) of the vehicle

        Returns:
            True if vehicle crossed the line in this frame, False otherwise
        """
        if self.counting_line is None:
            # No line defined, count on first detection
            if track_id not in self.crossed_vehicles:
                self.crossed_vehicles.add(track_id)
                return True
            return False

        if track_id in self.crossed_vehicles:
            # Already counted
            return False

        if track_id not in self.vehicle_positions:
            # First detection of this vehicle
            self.vehicle_positions[track_id] = current_center
            return False

        prev_center = self.vehicle_positions[track_id]
        self.vehicle_positions[track_id] = current_center

        # Check if the line segment from prev_center to current_center
        # intersects with the counting line
        (x1, y1), (x2, y2) = self.counting_line
        px1, py1 = prev_center
        px2, py2 = current_center

        # Line intersection using cross product
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

        line_a = (x1, y1)
        line_b = (x2, y2)
        movement_a = prev_center
        movement_b = current_center

        if ccw(line_a, movement_a, movement_b) != ccw(line_b, movement_a, movement_b) and \
           ccw(line_a, line_b, movement_a) != ccw(line_a, line_b, movement_b):
            # Lines intersect!
            self.crossed_vehicles.add(track_id)
            return True

        return False

    def process_frame(
        self, frame: np.ndarray, frame_number: int
    ) -> Tuple[np.ndarray, List[Dict]]:
        """
        Process a single frame: detect and track vehicles.

        Args:
            frame: Input frame
            frame_number: Current frame number

        Returns:
            Tuple of (annotated_frame, detections_list)
        """
        if self.model is None:
            self.load_model()

        # Run YOLO tracking (includes detection + tracking)
        results = self.model.track(
            frame,
            persist=True,
            conf=YOLO_CONFIDENCE,
            iou=YOLO_IOU,
            classes=[1, 2, 3, 5, 7],  # bicycle, car, motorcycle, bus, truck
            verbose=False,
        )

        detections = []
        annotated_frame = frame.copy()

        if results and len(results) > 0:
            result = results[0]

            # Check if tracking IDs are available
            if result.boxes.id is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                track_ids = result.boxes.id.cpu().numpy().astype(int)
                classes = result.boxes.cls.cpu().numpy().astype(int)
                confidences = result.boxes.conf.cpu().numpy()

                for box, track_id, cls, conf in zip(boxes, track_ids, classes, confidences):
                    x1, y1, x2, y2 = box
                    bbox_area = (x2 - x1) * (y2 - y1)

                    # Calculate center point for line crossing detection
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    current_center = (center_x, center_y)

                    # Classify vehicle
                    vehicle_type = self.classify_vehicle(cls, bbox_area)

                    # Check line crossing
                    crossed_line = self.check_line_crossing(track_id, current_center)

                    # Update or create tracked vehicle
                    if track_id not in self.tracked_vehicles:
                        self.tracked_vehicles[track_id] = {
                            'id': track_id,
                            'type': vehicle_type,
                            'first_seen': frame_number,
                            'last_seen': frame_number,
                            'max_confidence': conf,
                            'coco_class': cls,
                            'counted': crossed_line,
                        }
                        # Only count if crossed the line (or no line defined)
                        if crossed_line:
                            self.vehicle_counts[vehicle_type] += 1
                    else:
                        # Update existing track
                        self.tracked_vehicles[track_id]['last_seen'] = frame_number
                        self.tracked_vehicles[track_id]['max_confidence'] = max(
                            self.tracked_vehicles[track_id]['max_confidence'], conf
                        )
                        # Check if just crossed the line
                        if crossed_line and not self.tracked_vehicles[track_id]['counted']:
                            self.vehicle_counts[vehicle_type] += 1
                            self.tracked_vehicles[track_id]['counted'] = True

                    # Draw bounding box and label
                    color = self._get_color_for_type(vehicle_type)
                    cv2.rectangle(
                        annotated_frame,
                        (int(x1), int(y1)),
                        (int(x2), int(y2)),
                        color,
                        2,
                    )

                    # Prepare label
                    label = f"ID:{track_id} {vehicle_type} {conf:.2f}"
                    label_size, _ = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2
                    )

                    # Draw label background
                    cv2.rectangle(
                        annotated_frame,
                        (int(x1), int(y1) - label_size[1] - 10),
                        (int(x1) + label_size[0], int(y1)),
                        color,
                        -1,
                    )

                    # Draw label text
                    cv2.putText(
                        annotated_frame,
                        label,
                        (int(x1), int(y1) - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 255, 255),
                        2,
                    )

                    detections.append({
                        'track_id': track_id,
                        'type': vehicle_type,
                        'confidence': float(conf),
                        'bbox': [float(x1), float(y1), float(x2), float(y2)],
                    })

        # Draw counting line if defined
        if self.counting_line is not None:
            (x1, y1), (x2, y2) = self.counting_line
            cv2.line(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 3)
            # Draw arrow to indicate direction
            cv2.putText(
                annotated_frame,
                f"Zliczono: {len(self.crossed_vehicles)}",
                (int(x1), int(y1) - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )

        return annotated_frame, detections

    def _get_color_for_type(self, vehicle_type: str) -> Tuple[int, int, int]:
        """Get color for vehicle type (BGR format)."""
        colors = {
            'motocykl': (0, 255, 255),  # Yellow
            'samochod_osobowy': (0, 255, 0),  # Green
            'samochod_dostawczy': (255, 165, 0),  # Orange
            'samochod_ciezarowy': (255, 0, 0),  # Blue
            'autobus': (255, 0, 255),  # Magenta
            'rower': (0, 255, 255),  # Cyan
            'ciagnik': (128, 0, 128),  # Purple
            'przyczepa': (192, 192, 192),  # Silver
            'inne': (128, 128, 128),  # Gray
        }
        return colors.get(vehicle_type, (128, 128, 128))

    def get_summary(self) -> Dict:
        """Get tracking summary."""
        return {
            'total_vehicles': len(self.tracked_vehicles),
            'vehicle_counts': dict(self.vehicle_counts),
            'tracked_vehicles': self.tracked_vehicles,
        }

    def reset(self):
        """Reset tracker state."""
        self.tracked_vehicles = {}
        self.vehicle_counts = defaultdict(int)
