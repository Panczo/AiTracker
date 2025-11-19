"""Video processing pipeline for vehicle detection and tracking."""
import cv2
import pandas as pd
from pathlib import Path
from datetime import timedelta
from typing import Callable, Optional, Tuple, List
from collections import defaultdict
from app.tracker import VehicleTracker
from app.anonymizer import Anonymizer
from app.config import OUTPUT_VIDEO_CODEC, OUTPUT_VIDEO_FPS, FRAME_SKIP, INTERVAL_MINUTES, SECONDS_PER_INTERVAL


class VideoProcessor:
    """Handles video processing with vehicle detection and tracking."""

    def __init__(
        self,
        video_path: Path,
        output_dir: Path,
        counting_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
        enable_anonymization: bool = False,
        time_offset: float = 0.0,
    ):
        """
        Initialize video processor.

        Args:
            video_path: Path to input video file
            output_dir: Directory for output files
            counting_line: Counting line coordinates ((x1,y1), (x2,y2)) or None
            enable_anonymization: Whether to anonymize faces/plates
            time_offset: Time offset in seconds for this video in batch
        """
        self.video_path = video_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.tracker = VehicleTracker(counting_line=counting_line)
        self.anonymizer = Anonymizer() if enable_anonymization else None
        self.cap = None
        self.writer = None
        self.time_offset = time_offset

        # Video properties
        self.total_frames = 0
        self.fps = 0
        self.width = 0
        self.height = 0
        self.duration = 0

        # Time interval tracking
        self.interval_counts = defaultdict(lambda: defaultdict(int))  # interval_idx -> {vehicle_type: count}

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
        last_counted_vehicles = set()  # Track which vehicles were counted in previous interval

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            # Calculate current time in video (including offset for batch processing)
            current_time = self.time_offset + (frame_number / self.fps if self.fps > 0 else 0)
            current_interval = int(current_time // SECONDS_PER_INTERVAL)

            # Process frame (with optional frame skipping)
            if frame_number % FRAME_SKIP == 0:
                # Apply anonymization if enabled
                if self.anonymizer:
                    frame = self.anonymizer.anonymize_frame(frame)

                annotated_frame, detections = self.tracker.process_frame(
                    frame, frame_number
                )

                # Track new vehicles counted in this interval
                current_counted = self.tracker.crossed_vehicles.copy()
                new_vehicles = current_counted - last_counted_vehicles

                for track_id in new_vehicles:
                    if track_id in self.tracker.tracked_vehicles:
                        vehicle_type = self.tracker.tracked_vehicles[track_id]['type']
                        self.interval_counts[current_interval][vehicle_type] += 1

                last_counted_vehicles = current_counted

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
        Generate CSV report with 5-minute interval counts.

        Returns:
            Path to CSV file
        """
        csv_path = self.output_dir / f"{self.video_path.stem}_report.csv"

        # Get all vehicle types
        from app.config import VEHICLE_CLASSES
        vehicle_types = list(VEHICLE_CLASSES.keys())

        # Prepare data for CSV with 5-minute intervals
        data = []

        if self.interval_counts:
            max_interval = max(self.interval_counts.keys())

            for interval_idx in range(max_interval + 1):
                # Calculate time range for this interval
                start_seconds = interval_idx * SECONDS_PER_INTERVAL
                end_seconds = (interval_idx + 1) * SECONDS_PER_INTERVAL

                start_time = str(timedelta(seconds=int(start_seconds)))
                end_time = str(timedelta(seconds=int(end_seconds)))

                # Get hour and interval within hour
                hour = interval_idx // (60 // INTERVAL_MINUTES)
                interval_in_hour = (interval_idx % (60 // INTERVAL_MINUTES)) + 1

                # Create row with counts for each vehicle type
                row = {
                    'Godzina': hour,
                    'Przedzial': interval_in_hour,
                    'Czas_Od': start_time,
                    'Czas_Do': end_time,
                }

                total = 0
                for vtype in vehicle_types:
                    count = self.interval_counts[interval_idx].get(vtype, 0)
                    row[vtype.replace('_', ' ').title()] = count
                    total += count

                row['SUMA'] = total
                data.append(row)

        # Create DataFrame and save to CSV
        df = pd.DataFrame(data)

        if df.empty:
            # Create empty structure if no data
            df = pd.DataFrame(columns=['Godzina', 'Przedzial', 'Czas_Od', 'Czas_Do'] +
                                     [vt.replace('_', ' ').title() for vt in vehicle_types] +
                                     ['SUMA'])

        df.to_csv(csv_path, index=False, encoding='utf-8')

        return csv_path

    def cleanup(self):
        """Release resources."""
        if self.cap is not None:
            self.cap.release()
        if self.writer is not None:
            self.writer.release()
        cv2.destroyAllWindows()


class BatchVideoProcessor:
    """Handles batch processing of multiple video files."""

    def __init__(
        self,
        video_files: List[Tuple[Path, int]],  # List of (filepath, file_order)
        output_dir: Path,
        counting_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None,
        enable_anonymization: bool = False,
    ):
        """
        Initialize batch video processor.

        Args:
            video_files: List of (video_path, file_order) tuples
            output_dir: Directory for output files
            counting_line: Counting line coordinates
            enable_anonymization: Whether to anonymize
        """
        self.video_files = sorted(video_files, key=lambda x: x[1])  # Sort by order
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.counting_line = counting_line
        self.enable_anonymization = enable_anonymization

        # Accumulated interval counts across all files
        self.total_interval_counts = defaultdict(lambda: defaultdict(int))

    def process_batch(
        self,
        progress_callback: Optional[Callable[[int, int, str, int, int], None]] = None,
    ) -> dict:
        """
        Process all videos in batch.

        Args:
            progress_callback: Callback(current_frame, total_frames, step, file_idx, total_files)

        Returns:
            Dictionary with processing results
        """
        total_files = len(self.video_files)
        cumulative_time_offset = 0.0
        all_results = []

        for file_idx, (video_path, file_order) in enumerate(self.video_files):
            if progress_callback:
                progress_callback(0, 1, f"Przetwarzanie pliku {file_idx + 1}/{total_files}: {video_path.name}",
                                file_idx, total_files)

            # Create processor for this file
            processor = VideoProcessor(
                video_path=video_path,
                output_dir=self.output_dir,
                counting_line=self.counting_line,
                enable_anonymization=self.enable_anonymization,
                time_offset=cumulative_time_offset,
            )

            # Process video
            result = processor.process_video(
                progress_callback=lambda c, t, s: progress_callback(c, t, s, file_idx, total_files)
                if progress_callback else None
            )

            # Merge interval counts
            for interval_idx, counts in processor.interval_counts.items():
                for vehicle_type, count in counts.items():
                    self.total_interval_counts[interval_idx][vehicle_type] += count

            # Update cumulative time
            cumulative_time_offset += processor.duration

            all_results.append(result)
            processor.cleanup()

        # Generate combined CSV report
        combined_csv_path = self.generate_combined_csv()

        # Calculate totals
        total_vehicles = sum(r['total_vehicles'] for r in all_results)
        combined_counts = defaultdict(int)
        for r in all_results:
            for vtype, count in r['vehicle_counts'].items():
                combined_counts[vtype] += count

        return {
            'output_csv_path': str(combined_csv_path),
            'total_files': total_files,
            'total_vehicles': total_vehicles,
            'vehicle_counts': dict(combined_counts),
            'individual_results': all_results,
        }

    def generate_combined_csv(self) -> Path:
        """
        Generate combined CSV report for all videos.

        Returns:
            Path to combined CSV file
        """
        csv_path = self.output_dir / "combined_report.csv"

        # Get all vehicle types
        from app.config import VEHICLE_CLASSES
        vehicle_types = list(VEHICLE_CLASSES.keys())

        # Prepare data for CSV
        data = []

        if self.total_interval_counts:
            max_interval = max(self.total_interval_counts.keys())

            for interval_idx in range(max_interval + 1):
                # Calculate time range
                start_seconds = interval_idx * SECONDS_PER_INTERVAL
                end_seconds = (interval_idx + 1) * SECONDS_PER_INTERVAL

                start_time = str(timedelta(seconds=int(start_seconds)))
                end_time = str(timedelta(seconds=int(end_seconds)))

                # Get hour and interval within hour
                hour = interval_idx // (60 // INTERVAL_MINUTES)
                interval_in_hour = (interval_idx % (60 // INTERVAL_MINUTES)) + 1

                # Create row
                row = {
                    'Godzina': hour,
                    'Przedzial': interval_in_hour,
                    'Czas_Od': start_time,
                    'Czas_Do': end_time,
                }

                total = 0
                for vtype in vehicle_types:
                    count = self.total_interval_counts[interval_idx].get(vtype, 0)
                    row[vtype.replace('_', ' ').title()] = count
                    total += count

                row['SUMA'] = total
                data.append(row)

        # Create DataFrame and save
        df = pd.DataFrame(data)

        if df.empty:
            df = pd.DataFrame(columns=['Godzina', 'Przedzial', 'Czas_Od', 'Czas_Do'] +
                                     [vt.replace('_', ' ').title() for vt in vehicle_types] +
                                     ['SUMA'])

        df.to_csv(csv_path, index=False, encoding='utf-8')

        return csv_path
