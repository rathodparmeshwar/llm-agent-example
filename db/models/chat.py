# backend/db/models/chat.py

import uuid

from sqlalchemy import JSON, UUID, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import TimestampedModel


class Conversation(TimestampedModel):
    """Represents a chat conversation between a user and the AI assistant."""
    __tablename__ = 'conversations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    title = Column(String(200), nullable=False)
    last_activity = Column(DateTime, default=func.now(), onupdate=func.now())
    context = Column(JSON, nullable=True)
    current_summary_id = Column(UUID(as_uuid=True), ForeignKey('conversation_summaries.id'), nullable=True)

    # Relationships
    user = relationship('User', back_populates='conversations')
    messages = relationship('Message', back_populates='conversation', cascade='all, delete-orphan', order_by='Message.created_at.asc()')
    summaries = relationship('ConversationSummary', 
                           back_populates='conversation',
                           foreign_keys='ConversationSummary.conversation_id',
                           cascade='all, delete-orphan')
    current_summary = relationship('ConversationSummary',
                                 foreign_keys=[current_summary_id],
                                 post_update=True)

class ConversationSummary(TimestampedModel):
    """Represents an LLM-generated narrative summary of the conversation up to a specific point."""
    __tablename__ = 'conversation_summaries'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id'), nullable=False)
    narrative = Column(String, nullable=False)
    last_message_id = Column(UUID(as_uuid=True), ForeignKey('messages.id'), nullable=False)
    meta_data = Column(JSON, nullable=True)

    # Relationships
    conversation = relationship('Conversation', 
                              back_populates='summaries',
                              foreign_keys=[conversation_id])
    last_message = relationship('Message')

class Message(TimestampedModel):
    """Represents a single message within a conversation."""
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(String, nullable=False)
    meta_data = Column(JSON, nullable=True)
    display_in_ui = Column(Boolean, default=True)
    include_in_context = Column(Boolean, default=True)  # Whether to include in context for LLM

    # Relationships
    conversation = relationship('Conversation', back_populates='messages')

# Create indexes for better query performance
from sqlalchemy import Index

Index('idx_conversation_user', Conversation.user_id)
Index('idx_conversation_last_activity', Conversation.last_activity)
Index('idx_message_conversation', Message.conversation_id)
Index('idx_summary_conversation', ConversationSummary.conversation_id)
Index('idx_summary_last_message', ConversationSummary.last_message_id) 