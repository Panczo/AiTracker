"""FastAPI application for vehicle tracking."""
import os
import json
import uuid
import shutil
import cv2
import base64
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    Form,
)
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.config import (
    UPLOADS_DIR,
    PROCESSED_DIR,
    MAX_FILE_SIZE_BYTES,
    MAX_TOTAL_DURATION_HOURS,
    ALLOWED_EXTENSIONS,
)
from app.models import ProcessingJob, VideoFile, init_db, get_db
from app.processor import VideoProcessor, BatchVideoProcessor

# Initialize FastAPI app
app = FastAPI(title="AiTracker - Vehicle Detection System")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        """Connect a WebSocket for a specific job."""
        await websocket.accept()
        self.active_connections[job_id] = websocket

    def disconnect(self, job_id: str):
        """Disconnect a WebSocket."""
        if job_id in self.active_connections:
            del self.active_connections[job_id]

    async def send_status(self, job_id: str, data: dict):
        """Send status update to a specific job's WebSocket."""
        if job_id in self.active_connections:
            try:
                await self.active_connections[job_id].send_json(data)
            except Exception as e:
                print(f"Error sending WebSocket message: {e}")
                self.disconnect(job_id)


manager = ConnectionManager()

# Thread pool for background processing
executor = ThreadPoolExecutor(max_workers=1)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()
    print("Database initialized")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "AiTracker API", "version": "1.0.0"}


@app.post("/api/upload")
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a video file for processing.

    Returns job_id for tracking.
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Nieprawidłowy format pliku. Dozwolone: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Save uploaded file
    upload_path = UPLOADS_DIR / f"{job_id}{file_ext}"

    try:
        # Read and save file in chunks (handle large files)
        file_size = 0
        with open(upload_path, "wb") as buffer:
            while chunk := await file.read(8192):  # 8KB chunks
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE_BYTES:
                    # Remove partial file
                    buffer.close()
                    upload_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"Plik zbyt duży. Maksymalny rozmiar: {MAX_FILE_SIZE_BYTES // (1024*1024)}MB",
                    )
                buffer.write(chunk)

    except Exception as e:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Błąd podczas uploadu: {str(e)}")

    # Create database entry
    job = ProcessingJob(
        job_id=job_id,
        original_filename=file.filename,
        original_filepath=str(upload_path),
        status="uploaded",
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "job_id": job_id,
        "filename": file.filename,
        "message": "Plik przesłany pomyślnie",
    }


@app.post("/api/upload-batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload multiple video files for batch processing.

    Returns job_id for tracking.
    """
    if not files:
        raise HTTPException(status_code=400, detail="Brak plików do przesłania")

    # Generate unique job ID for batch
    job_id = str(uuid.uuid4())

    # Validate and save all files
    video_files_data = []
    total_duration = 0.0

    for file_order, file in enumerate(files):
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Nieprawidłowy format pliku: {file.filename}. Dozwolone: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # Save uploaded file
        upload_path = UPLOADS_DIR / f"{job_id}_{file_order}{file_ext}"

        try:
            file_size = 0
            with open(upload_path, "wb") as buffer:
                while chunk := await file.read(8192):
                    file_size += len(chunk)
                    if file_size > MAX_FILE_SIZE_BYTES:
                        buffer.close()
                        upload_path.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=413,
                            detail=f"Plik zbyt duży: {file.filename}. Maksymalny rozmiar: {MAX_FILE_SIZE_BYTES // (1024*1024)}MB",
                        )
                    buffer.write(chunk)

            # Get video duration
            cap = cv2.VideoCapture(str(upload_path))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            cap.release()

            total_duration += duration

            video_files_data.append({
                "filename": file.filename,
                "filepath": str(upload_path),
                "file_order": file_order,
                "duration_seconds": duration,
                "fps": fps,
                "total_frames": frame_count,
            })

        except Exception as e:
            # Cleanup on error
            upload_path.unlink(missing_ok=True)
            for vf in video_files_data:
                Path(vf["filepath"]).unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=f"Błąd podczas uploadu: {str(e)}")

    # Check total duration
    max_duration = MAX_TOTAL_DURATION_HOURS * 3600
    if total_duration > max_duration:
        # Cleanup
        for vf in video_files_data:
            Path(vf["filepath"]).unlink(missing_ok=True)
        raise HTTPException(
            status_code=413,
            detail=f"Łączny czas nagrań zbyt długi: {total_duration/3600:.1f}h. Maksymalnie: {MAX_TOTAL_DURATION_HOURS}h",
        )

    # Create batch job in database
    job = ProcessingJob(
        job_id=job_id,
        status="uploaded",
        is_batch=True,
        total_files=len(files),
    )

    db.add(job)
    db.commit()

    # Add video files to database
    for vf_data in video_files_data:
        video_file = VideoFile(
            job_id_fk=job_id,
            filename=vf_data["filename"],
            filepath=vf_data["filepath"],
            file_order=vf_data["file_order"],
            duration_seconds=vf_data["duration_seconds"],
            fps=vf_data["fps"],
            total_frames=vf_data["total_frames"],
            status="pending",
        )
        db.add(video_file)

    db.commit()
    db.refresh(job)

    return {
        "job_id": job_id,
        "total_files": len(files),
        "total_duration": total_duration,
        "message": f"Przesłano {len(files)} plików pomyślnie",
    }


@app.get("/api/preview/{job_id}")
async def get_preview_frame(job_id: str, db: Session = Depends(get_db)):
    """
    Get first frame of video for line drawing.

    Returns base64 encoded JPEG image.
    """
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Zadanie nie znalezione")

    # Get first video file
    if job.is_batch:
        video_file = db.query(VideoFile).filter(
            VideoFile.job_id_fk == job_id,
            VideoFile.file_order == 0
        ).first()
        if not video_file:
            raise HTTPException(status_code=404, detail="Brak plików wideo")
        video_path = Path(video_file.filepath)
    else:
        if not job.original_filepath:
            raise HTTPException(status_code=404, detail="Plik wideo nie znaleziony")
        video_path = Path(job.original_filepath)

    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Plik wideo nie istnieje")

    # Extract first frame
    cap = cv2.VideoCapture(str(video_path))
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise HTTPException(status_code=500, detail="Nie można odczytać klatki wideo")

    # Resize for preview (max 1280px width)
    height, width = frame.shape[:2]
    if width > 1280:
        scale = 1280 / width
        new_width = 1280
        new_height = int(height * scale)
        frame = cv2.resize(frame, (new_width, new_height))

    # Encode to JPEG
    _, buffer = cv2.imencode('.jpg', frame)
    frame_base64 = base64.b64encode(buffer).decode('utf-8')

    return {
        "job_id": job_id,
        "frame": frame_base64,
        "width": frame.shape[1],
        "height": frame.shape[0],
    }


@app.post("/api/set-line/{job_id}")
async def set_counting_line(
    job_id: str,
    line_data: dict,
    db: Session = Depends(get_db),
):
    """
    Set counting line coordinates for a job.

    Expects: {"p1": {"x": float, "y": float}, "p2": {"x": float, "y": float}}
    """
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Zadanie nie znalezione")

    if job.status not in ["uploaded"]:
        raise HTTPException(status_code=400, detail="Nie można ustawić linii dla tego zadania")

    # Validate line data
    if "p1" not in line_data or "p2" not in line_data:
        raise HTTPException(status_code=400, detail="Brak współrzędnych linii")

    p1 = line_data["p1"]
    p2 = line_data["p2"]

    if "x" not in p1 or "y" not in p1 or "x" not in p2 or "y" not in p2:
        raise HTTPException(status_code=400, detail="Nieprawidłowe współrzędne")

    # Save line coordinates
    job.line_p1_x = float(p1["x"])
    job.line_p1_y = float(p1["y"])
    job.line_p2_x = float(p2["x"])
    job.line_p2_y = float(p2["y"])

    db.commit()

    return {
        "message": "Linia zliczająca ustawiona",
        "job_id": job_id,
        "line": {
            "p1": {"x": job.line_p1_x, "y": job.line_p1_y},
            "p2": {"x": job.line_p2_x, "y": job.line_p2_y},
        },
    }


@app.post("/api/set-options/{job_id}")
async def set_processing_options(
    job_id: str,
    enable_anonymization: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Set processing options like anonymization."""
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Zadanie nie znalezione")

    job.enable_anonymization = enable_anonymization
    db.commit()

    return {
        "message": "Opcje ustawione",
        "job_id": job_id,
        "enable_anonymization": enable_anonymization,
    }


@app.post("/api/process/{job_id}")
async def process_video(job_id: str, db: Session = Depends(get_db)):
    """Start processing a video."""
    # Get job from database
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Zadanie nie znalezione")

    if job.status not in ["uploaded", "failed"]:
        raise HTTPException(
            status_code=400, detail="Zadanie jest już przetwarzane lub zakończone"
        )

    # Update status
    job.status = "processing"
    job.started_at = datetime.utcnow()
    db.commit()

    # Start background processing
    asyncio.create_task(process_video_background(job_id))

    return {"message": "Przetwarzanie rozpoczęte", "job_id": job_id}


async def process_video_background(job_id: str):
    """Background task to process video (single or batch)."""
    # Create new database session for this task
    from app.models import SessionLocal
    db = SessionLocal()

    processor = None
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()

        if not job:
            return

        # Create output directory
        output_dir = PROCESSED_DIR / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Get counting line if set
        counting_line = None
        if job.line_p1_x is not None and job.line_p2_x is not None:
            counting_line = (
                (job.line_p1_x, job.line_p1_y),
                (job.line_p2_x, job.line_p2_y)
            )

        # Check if batch or single file processing
        if job.is_batch:
            # Batch processing
            video_files = db.query(VideoFile).filter(
                VideoFile.job_id_fk == job_id
            ).order_by(VideoFile.file_order).all()

            if not video_files:
                raise Exception("Brak plików wideo do przetworzenia")

            # Get total frames for progress tracking
            total_frames = sum(vf.total_frames or 0 for vf in video_files)
            job.total_frames = total_frames
            db.commit()

            # Prepare video files list
            video_files_list = [(Path(vf.filepath), vf.file_order) for vf in video_files]

            # Create batch processor
            batch_processor = BatchVideoProcessor(
                video_files=video_files_list,
                output_dir=output_dir,
                counting_line=counting_line,
                enable_anonymization=job.enable_anonymization or False,
            )

            # Progress callback for batch
            def sync_batch_progress_callback(current: int, total: int, step: str, file_idx: int, total_files: int):
                """Progress callback for batch processing."""
                # Calculate overall progress
                file_progress = (file_idx / total_files) * 100
                frame_progress = (current / total if total > 0 else 0) * (100 / total_files)
                overall_progress = file_progress + frame_progress

                job.progress = overall_progress
                job.current_step = step
                job.processed_files = file_idx
                db.commit()

                # Update video file status
                if file_idx < len(video_files):
                    video_files[file_idx].status = "processing"
                    video_files[file_idx].processed_frames = current
                    db.commit()

                # Send WebSocket update
                loop = asyncio.get_event_loop()
                asyncio.run_coroutine_threadsafe(
                    manager.send_status(job_id, {
                        "job_id": job_id,
                        "status": "processing",
                        "progress": overall_progress,
                        "current_step": step,
                        "processed_files": file_idx,
                        "total_files": total_files,
                        "current_file_frames": current,
                        "current_file_total_frames": total,
                    }),
                    loop
                )

            # Process batch in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                lambda: batch_processor.process_batch(progress_callback=sync_batch_progress_callback)
            )

            # Mark all video files as completed
            for vf in video_files:
                vf.status = "completed"
            db.commit()

        else:
            # Single file processing (legacy)
            if not job.original_filepath:
                raise Exception("Brak pliku wideo")

            video_path = Path(job.original_filepath)
            processor = VideoProcessor(
                video_path=video_path,
                output_dir=output_dir,
                counting_line=counting_line,
                enable_anonymization=job.enable_anonymization or False,
            )

            # Get video info
            video_info = processor.get_video_info()
            job.total_frames = video_info['total_frames']
            job.fps = video_info['fps']
            job.duration_seconds = video_info['duration']
            db.commit()

            # Progress callback for single file
            def sync_progress_callback(current: int, total: int, step: str):
                """Synchronous wrapper for progress updates."""
                progress = (current / total * 100) if total > 0 else 0
                job.progress = progress
                job.current_step = step
                job.processed_frames = current
                db.commit()

                # Schedule WebSocket update in event loop
                loop = asyncio.get_event_loop()
                asyncio.run_coroutine_threadsafe(
                    manager.send_status(job_id, {
                        "job_id": job_id,
                        "status": "processing",
                        "progress": progress,
                        "current_step": step,
                        "processed_frames": current,
                        "total_frames": total,
                    }),
                    loop
                )

            # Process video in thread pool (blocking operation)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                lambda: processor.process_video(progress_callback=sync_progress_callback)
            )

            # Delete original file
            if video_path.exists():
                video_path.unlink()
                job.original_filepath = None

        # Update job with results
        job.status = "completed"
        job.progress = 100
        job.current_step = "Zakończono"
        job.completed_at = datetime.utcnow()
        job.output_csv_path = result['output_csv_path']
        job.total_vehicles = result['total_vehicles']
        job.vehicle_counts = json.dumps(result['vehicle_counts'], ensure_ascii=False)
        db.commit()

        # Delete uploaded files for batch
        if job.is_batch:
            video_files = db.query(VideoFile).filter(VideoFile.job_id_fk == job_id).all()
            for vf in video_files:
                file_path = Path(vf.filepath)
                if file_path.exists():
                    file_path.unlink()
                vf.filepath = None
            db.commit()

        # Send completion WebSocket message
        await manager.send_status(job_id, {
            "job_id": job_id,
            "status": "completed",
            "progress": 100,
            "total_vehicles": result['total_vehicles'],
            "vehicle_counts": result['vehicle_counts'],
        })

    except Exception as e:
        # Handle errors
        job.status = "failed"
        job.error_message = str(e)
        db.commit()

        await manager.send_status(job_id, {
            "job_id": job_id,
            "status": "failed",
            "error_message": str(e),
        })

        print(f"Error processing video {job_id}: {e}")

    finally:
        if processor:
            processor.cleanup()
        db.close()


@app.get("/api/status/{job_id}")
async def get_status(job_id: str, db: Session = Depends(get_db)):
    """Get processing status for a job."""
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Zadanie nie znalezione")

    return job.to_dict()


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time status updates."""
    await manager.connect(job_id, websocket)

    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(job_id)


@app.get("/api/download/{job_id}/video")
async def download_video(job_id: str, db: Session = Depends(get_db)):
    """Download processed video."""
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Zadanie nie znalezione")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Przetwarzanie nie zakończone")

    if not job.output_video_path or not Path(job.output_video_path).exists():
        raise HTTPException(status_code=404, detail="Plik wideo nie znaleziony")

    return FileResponse(
        job.output_video_path,
        media_type="video/mp4",
        filename=f"{Path(job.original_filename).stem}_processed.mp4",
    )


@app.get("/api/download/{job_id}/csv")
async def download_csv(job_id: str, db: Session = Depends(get_db)):
    """Download CSV report."""
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Zadanie nie znalezione")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Przetwarzanie nie zakończone")

    if not job.output_csv_path or not Path(job.output_csv_path).exists():
        raise HTTPException(status_code=404, detail="Plik CSV nie znaleziony")

    return FileResponse(
        job.output_csv_path,
        media_type="text/csv",
        filename=f"{Path(job.original_filename).stem}_report.csv",
    )


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Delete a job and its associated files."""
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()

    if not job:
        raise HTTPException(status_code=404, detail="Zadanie nie znalezione")

    # Delete files
    if job.original_filepath:
        Path(job.original_filepath).unlink(missing_ok=True)

    output_dir = PROCESSED_DIR / job_id
    if output_dir.exists():
        shutil.rmtree(output_dir)

    # Delete database entry
    db.delete(job)
    db.commit()

    return {"message": "Zadanie usunięte"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
