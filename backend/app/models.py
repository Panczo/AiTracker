"""Database models for the AiTracker application."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from app.config import DATABASE_URL

Base = declarative_base()


class ProcessingJob(Base):
    """Model representing a video processing job."""

    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)

    # Batch processing
    is_batch = Column(Boolean, default=False)
    total_files = Column(Integer, default=1)
    processed_files = Column(Integer, default=0)

    # Line crossing configuration
    line_p1_x = Column(Float, nullable=True)  # Line point 1 X
    line_p1_y = Column(Float, nullable=True)  # Line point 1 Y
    line_p2_x = Column(Float, nullable=True)  # Line point 2 X
    line_p2_y = Column(Float, nullable=True)  # Line point 2 Y

    # Anonymization
    enable_anonymization = Column(Boolean, default=False)

    # Output files
    output_csv_path = Column(String, nullable=True)
    output_excel_path = Column(String, nullable=True)

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

    # Relationships
    video_files = relationship("VideoFile", back_populates="job", cascade="all, delete-orphan")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "error_message": self.error_message,
            "is_batch": self.is_batch,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "total_frames": self.total_frames,
            "processed_frames": self.processed_frames,
            "total_vehicles": self.total_vehicles,
            "vehicle_counts": self.vehicle_counts,
            "enable_anonymization": self.enable_anonymization,
            "video_files": [vf.to_dict() for vf in self.video_files] if self.video_files else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class VideoFile(Base):
    """Model representing an individual video file in a batch job."""

    __tablename__ = "video_files"

    id = Column(Integer, primary_key=True, index=True)
    job_id_fk = Column(String, ForeignKey("processing_jobs.job_id"), nullable=False)

    # File info
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    file_order = Column(Integer, default=0)  # Order in batch

    # Video metadata
    duration_seconds = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)
    total_frames = Column(Integer, nullable=True)

    # Processing status
    status = Column(String, default="pending")  # pending, processing, completed, failed
    processed_frames = Column(Integer, default=0)

    # Output
    output_video_path = Column(String, nullable=True)

    # Relationship
    job = relationship("ProcessingJob", back_populates="video_files")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "filename": self.filename,
            "file_order": self.file_order,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "processed_frames": self.processed_frames,
            "total_frames": self.total_frames,
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
