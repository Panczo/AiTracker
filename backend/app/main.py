"""FastAPI application for vehicle tracking."""
import os
import json
import uuid
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Depends,
)
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.config import (
    UPLOADS_DIR,
    PROCESSED_DIR,
    MAX_FILE_SIZE_BYTES,
    ALLOWED_EXTENSIONS,
)
from app.models import ProcessingJob, init_db, get_db
from app.processor import VideoProcessor

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
    """Background task to process video."""
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

        # Initialize processor
        video_path = Path(job.original_filepath)
        processor = VideoProcessor(video_path, output_dir)

        # Get video info
        video_info = processor.get_video_info()
        job.total_frames = video_info['total_frames']
        job.fps = video_info['fps']
        job.duration_seconds = video_info['duration']
        db.commit()

        # Create a sync callback wrapper for thread safety
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

        # Update job with results
        job.status = "completed"
        job.progress = 100
        job.current_step = "Zakończono"
        job.completed_at = datetime.utcnow()
        job.output_video_path = result['output_video_path']
        job.output_csv_path = result['output_csv_path']
        job.total_vehicles = result['total_vehicles']
        job.vehicle_counts = json.dumps(result['vehicle_counts'], ensure_ascii=False)
        db.commit()

        # Delete original file
        if video_path.exists():
            video_path.unlink()
            job.original_filepath = None
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
