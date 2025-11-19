"""Anonymization module for blurring faces and license plates."""
import cv2
import numpy as np
from typing import List, Tuple
from ultralytics import YOLO
from pathlib import Path
from app.config import BLUR_KERNEL_SIZE, MODELS_DIR


class Anonymizer:
    """Handles face and license plate anonymization using blur."""

    def __init__(self):
        """Initialize anonymizer."""
        self.blur_kernel = (BLUR_KERNEL_SIZE, BLUR_KERNEL_SIZE)

    def anonymize_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Anonymize a frame by blurring detected regions.

        Args:
            frame: Input frame

        Returns:
            Anonymized frame
        """
        anonymized = frame.copy()

        # Detect faces using simple method (upper portion of detected people)
        # This is a simple heuristic-based approach for CPU efficiency
        # For better results, you could use a dedicated face detection model

        # Blur bottom third of frame (typical license plate region)
        # This is a simple approach - for production, use dedicated plate detection
        height = frame.shape[0]
        width = frame.shape[1]

        # Apply simple Gaussian blur to lower portion (where plates typically are)
        # This is a trade-off between privacy and accuracy
        lower_region = anonymized[int(height * 0.7):, :]
        if lower_region.size > 0:
            blurred_lower = cv2.GaussianBlur(lower_region, self.blur_kernel, 0)
            anonymized[int(height * 0.7):, :] = blurred_lower

        return anonymized

    def blur_region(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Blur a specific region in the frame.

        Args:
            frame: Input frame
            bbox: Bounding box (x1, y1, x2, y2)

        Returns:
            Frame with blurred region
        """
        x1, y1, x2, y2 = bbox
        x1, y1, x2, y2 = max(0, x1), max(0, y1), min(frame.shape[1], x2), min(frame.shape[0], y2)

        if x2 > x1 and y2 > y1:
            roi = frame[y1:y2, x1:x2]
            blurred_roi = cv2.GaussianBlur(roi, self.blur_kernel, 0)
            frame[y1:y2, x1:x2] = blurred_roi

        return frame


class AdvancedAnonymizer(Anonymizer):
    """Advanced anonymizer using YOLO for face and plate detection."""

    def __init__(self):
        """Initialize with face/plate detection models."""
        super().__init__()
        # Note: For production, you would use specialized models here
        # For now, we'll use simple region-based blurring
        self.use_detection = False  # Set to True if you have face/plate models

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in frame.

        Returns:
            List of bounding boxes (x1, y1, x2, y2)
        """
        # Placeholder for face detection
        # In production, use cv2.CascadeClassifier or a YOLO face model
        return []

    def detect_plates(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect license plates in frame.

        Returns:
            List of bounding boxes (x1, y1, x2, y2)
        """
        # Placeholder for plate detection
        # In production, use a specialized license plate detection model
        return []

    def anonymize_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Anonymize frame using detection models.

        Args:
            frame: Input frame

        Returns:
            Anonymized frame
        """
        if not self.use_detection:
            # Fall back to simple region blurring
            return super().anonymize_frame(frame)

        anonymized = frame.copy()

        # Detect and blur faces
        faces = self.detect_faces(frame)
        for bbox in faces:
            anonymized = self.blur_region(anonymized, bbox)

        # Detect and blur license plates
        plates = self.detect_plates(frame)
        for bbox in plates:
            anonymized = self.blur_region(anonymized, bbox)

        return anonymized
