"""Schemas for the Screening Decision Agent - Post-Conversation Analysis."""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from enum import Enum


class DecisionType(str, Enum):
    """Types of recruiter intervention decisions."""
    CLINICIAN_QUESTION = "clinician_question"
    INFORMATION_REQUEST = "information_request"
    SPECIAL_ACCOMMODATION = "special_accommodation"
    SCHEDULING_CONFLICT = "scheduling_conflict"


class DecisionPriority(str, Enum):
    """Priority levels for recruiter decisions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConversationMetadata(BaseModel):
    """Metadata for conversation analysis."""
    conversation_id: UUID = Field(description="ID of the conversation")
    clinician_id: UUID = Field(description="ID of the clinician")
    job_posting_match_id: UUID = Field(description="ID of the job posting match")
    team_id: UUID = Field(description="ID of the team")
    client_id: UUID = Field(description="ID of the client")
    start_timestamp: datetime = Field(description="Conversation start time")
    end_timestamp: datetime = Field(description="Conversation end time")
    message_count: int = Field(description="Total number of messages")
    note_count: int = Field(description="Total number of notes")
    notes_start_timestamp: datetime = Field(description="Timestamp of the first note")
    notes_end_timestamp: datetime = Field(description="Timestamp of the last note")


class MessageAnalysis(BaseModel):
    """Analysis of a specific message requiring intervention."""
    message_id: UUID = Field(description="ID of the message")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(description="Message timestamp")
    role: str = Field(description="Message role (user/assistant)")
    requires_intervention: bool = Field(description="Whether this message needs intervention")
    intervention_reason: str = Field(description="Reason for intervention")
    quoted_excerpt: str = Field(description="Key excerpt from the message")


class InterventionDecision(BaseModel):
    """Decision record for recruiter intervention."""
    title: str = Field(description="Descriptive title for the decision")
    body: str = Field(description="Detailed body of the decision")
    decision_type: DecisionType = Field(description="Type of intervention needed")
    priority: DecisionPriority = Field(description="Priority level")
    quoted_excerpts: List[str] = Field(description="Quoted excerpts from conversation")
    ai_reasoning: str = Field(description="AI reasoning for escalation")
    
    # Context
    conversation_metadata: ConversationMetadata = Field(description="Source conversation metadata")
    related_messages: List[MessageAnalysis] = Field(description="Messages that triggered this decision")
    
    # Organizational scope
    team_id: UUID = Field(description="Team ID for access control")
    client_id: UUID = Field(description="Client ID for access control")
    job_posting_match_id: UUID = Field(description="Job posting match ID for access control")


class ConversationAnalysisInput(BaseModel):
    """Input for conversation analysis."""
    conversation_id: UUID = Field(description="ID of the conversation to analyze")
    match_id: UUID = Field(description="ID of the match to analyze")
    force_reanalysis: bool = Field(default=False, description="Force reanalysis even if already processed")


class ConversationAnalysisResult(BaseModel):
    """Result of conversation analysis."""
    conversation_id: UUID = Field(description="ID of the analyzed conversation")
    analysis_completed: bool = Field(description="Whether analysis completed successfully")
    decisions_created: int = Field(description="Number of decisions created")
    decisions: List[InterventionDecision] = Field(description="Created intervention decisions")
    processing_time: float = Field(description="Processing time in seconds")
    error_message: Optional[str] = Field(default=None, description="Error message if analysis failed")


class AnalysisContext(BaseModel):
    """Context for analyzing conversation messages."""
    conversation_id: UUID
    clinician_id: UUID
    job_posting_match_id: UUID
    team_id: UUID
    client_id: UUID
    messages: List[Dict[str, Any]] = Field(description="Conversation messages")
    notes: List[Dict[str, Any]] = Field(description="Conversation notes")
    conversation_metadata: ConversationMetadata
    existing_decisions: List[Dict[str, Any]] = Field(default_factory=list, description="Existing decisions for deduplication") 