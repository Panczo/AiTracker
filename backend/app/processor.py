"""Video processing pipeline for vehicle detection and tracking."""
import cv2
import pandas as pd
from pathlib import Path
from datetime import timedelta
from typing import Callable, Optional
from app.tracker import VehicleTracker
from app.config import OUTPUT_VIDEO_CODEC, OUTPUT_VIDEO_FPS, FRAME_SKIP


class VideoProcessor:
    """Handles video processing with vehicle detection and tracking."""

    def __init__(self, video_path: Path, output_dir: Path):
        """
        Initialize video processor.

        Args:
            video_path: Path to input video file
            output_dir: Directory for output files
        """
        self.video_path = video_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.tracker = VehicleTracker()
        self.cap = None
        self.writer = None

        # Video properties
        self.total_frames = 0
        self.fps = 0
        self.width = 0
        self.height = 0
        self.duration = 0

    def get_video_info(self) -> dict:
        """Get video metadata."""
        cap = cv2.VideoCapture(str(self.video_path))

        info = {
            'total_frames': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        }

        info['duration'] = info['total_frames'] / info['fps'] if info['fps'] > 0 else 0

        cap.release()
        return info

    def process_video(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> dict:
        """
        Process video: detect and track vehicles.

        Args:
            progress_callback: Callback function(current_frame, total_frames, step)

        Returns:
            Dictionary with processing results
        """
        # Get video info
        video_info = self.get_video_info()
        self.total_frames = video_info['total_frames']
        self.fps = video_info['fps']
        self.width = video_info['width']
        self.height = video_info['height']
        self.duration = video_info['duration']

        # Open video capture
        self.cap = cv2.VideoCapture(str(self.video_path))

        # Prepare output video path
        output_video_path = self.output_dir / f"{self.video_path.stem}_processed.mp4"

        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*OUTPUT_VIDEO_CODEC)
        self.writer = cv2.VideoWriter(
            str(output_video_path),
            fourcc,
            self.fps if self.fps > 0 else OUTPUT_VIDEO_FPS,
            (self.width, self.height),
        )

        # Load YOLO model
        if progress_callback:
            progress_callback(0, self.total_frames, "Ładowanie modelu YOLO...")
        self.tracker.load_model()

        # Process frames
        frame_number = 0
        processed_frames = 0

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            # Process frame (with optional frame skipping)
            if frame_number % FRAME_SKIP == 0:
                annotated_frame, detections = self.tracker.process_frame(
                    frame, frame_number
                )
                self.writer.write(annotated_frame)

                if progress_callback and processed_frames % 10 == 0:
                    step_msg = f"Przetwarzanie klatki {frame_number}/{self.total_frames}"
                    progress_callback(frame_number, self.total_frames, step_msg)

                processed_frames += 1
            else:
                self.writer.write(frame)

            frame_number += 1

        # Cleanup
        self.cap.release()
        self.writer.release()

        # Generate CSV report
        if progress_callback:
            progress_callback(
                self.total_frames, self.total_frames, "Generowanie raportu CSV..."
            )

        csv_path = self.generate_csv_report()

        # Get summary
        summary = self.tracker.get_summary()

        return {
            'output_video_path': str(output_video_path),
            'output_csv_path': str(csv_path),
            'total_frames': self.total_frames,
            'processed_frames': processed_frames,
            'duration': self.duration,
            'total_vehicles': summary['total_vehicles'],
            'vehicle_counts': summary['vehicle_counts'],
        }

    def generate_csv_report(self) -> Path:
        """
        Generate CSV report with vehicle tracking data.

        Returns:
            Path to CSV file
        """
        csv_path = self.output_dir / f"{self.video_path.stem}_report.csv"

        # Prepare data for CSV
        data = []
        for track_id, vehicle_info in self.tracker.tracked_vehicles.items():
            first_seen_sec = vehicle_info['first_seen'] / self.fps if self.fps > 0 else 0
            last_seen_sec = vehicle_info['last_seen'] / self.fps if self.fps > 0 else 0
            duration_sec = last_seen_sec - first_seen_sec

            data.append({
                'vehicle_id': track_id,
                'type': vehicle_info['type'],
                'confidence': round(vehicle_info['max_confidence'], 2),
                'first_seen': str(timedelta(seconds=int(first_seen_sec))),
                'last_seen': str(timedelta(seconds=int(last_seen_sec))),
                'duration_seconds': round(duration_sec, 2),
            })

        # Create DataFrame and save to CSV
        df = pd.DataFrame(data)

        # Sort by first_seen
        if not df.empty:
            df = df.sort_values('vehicle_id')

        df.to_csv(csv_path, index=False, encoding='utf-8')

        return csv_path

    def cleanup(self):
        """Release resources."""
        if self.cap is not None:
            self.cap.release()
        if self.writer is not None:
            self.writer.release()
        cv2.destroyAllWindows()
