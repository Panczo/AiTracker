"""Database models for the AiTracker application."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

Base = declarative_base()


class ProcessingJob(Base):
    """Model representing a video processing job."""

    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)

    # File info
    original_filename = Column(String, nullable=False)
    original_filepath = Column(String, nullable=True)

    # Output files
    output_video_path = Column(String, nullable=True)
    output_csv_path = Column(String, nullable=True)

    # Status tracking
    status = Column(String, default="uploaded")  # uploaded, processing, completed, failed
    progress = Column(Float, default=0.0)  # 0-100
    current_step = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    # Video metadata
    total_frames = Column(Integer, nullable=True)
    processed_frames = Column(Integer, default=0)
    duration_seconds = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)

    # Vehicle counts
    total_vehicles = Column(Integer, default=0)
    vehicle_counts = Column(Text, nullable=True)  # JSON string

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "job_id": self.job_id,
            "original_filename": self.original_filename,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "error_message": self.error_message,
            "total_frames": self.total_frames,
            "processed_frames": self.processed_frames,
            "total_vehicles": self.total_vehicles,
            "vehicle_counts": self.vehicle_counts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# Database engine and session
engine = None
SessionLocal = None


def init_db():
    """Initialize the database."""
    global engine, SessionLocal

    # Remove async from URL for sync operations
    sync_url = DATABASE_URL.replace("+aiosqlite", "")

    engine = create_engine(sync_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
