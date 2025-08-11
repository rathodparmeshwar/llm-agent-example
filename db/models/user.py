from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
from typing import Optional

Base = declarative_base()

from base import TimestampedModel

class User(TimestampedModel):
    """User model for authentication and authorization."""
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    user_type: Mapped[str] = mapped_column(String(50), nullable=False, default='recruiter_recruiter')  # e.g., 'wakura_admin', 'recruiter_admin', 'recruiter_manager', 'recruiter_recruiter', 'client', 'clinician'

    # Recruiter-specific relations
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('companies.id'), nullable=True)
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey('teams.id'), nullable=True)
