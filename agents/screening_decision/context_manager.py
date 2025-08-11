"""Context manager for the Screening Decision Agent - Post-Conversation Analysis."""

import logging
import time
from typing import Dict, Any, Optional, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload, joinedload

from db.models.chat import Conversation, Message
from db.models.clinician_note import ClinicianNote
from db.models.job_posting_match import JobPostingMatch
from db.models.clinician import Clinician
from db.models.job_posting import JobPosting
from db.models.client import Client
from db.models.organization import Team
from db.models.decision import Decision
from .schemas import ConversationAnalysisInput, AnalysisContext, ConversationMetadata

logger = logging.getLogger(__name__)


class ScreeningDecisionContextManager:
    """Manages context assembly for post-conversation analysis."""
    
    def __init__(self, input_data: ConversationAnalysisInput):
        self.input_data = input_data
        self.conversation_id = input_data.conversation_id
        self.match_id = input_data.match_id
    
    async def assemble_analysis_context(
        self, 
        db_session: AsyncSession
    ) -> Optional[AnalysisContext]:
        """Assembles comprehensive context for post-conversation analysis.
        
        Args:
            db_session: Database session
            
        Returns:
            AnalysisContext or None if context cannot be assembled
        """
        start_time = time.time()
        logger.info(f"POST_CONV_ANALYSIS: Starting context assembly for conversation_id={self.conversation_id}")
        
        try:
            # 1. Get conversation with messages
            step_start = time.time()
            conversation_data = await self._get_conversation_data(db_session)
            step_time = time.time() - step_start
            
            if not conversation_data:
                logger.error(f"POST_CONV_ANALYSIS: Conversation not found: {self.conversation_id}")
                return None
            
            message_count, note_count = len(conversation_data['messages']), len(conversation_data['notes'])
            logger.info(f"POST_CONV_ANALYSIS: Loaded conversation data in {step_time:.3f}s - "
                       f"messages={message_count}, notes={note_count}")
            
            # 2. Get job posting match and related data
            step_start = time.time()
            match_data = await self._get_match_data(db_session, conversation_data['conversation'])
            step_time = time.time() - step_start
            
            if not match_data:
                logger.error(f"POST_CONV_ANALYSIS: Could not find match data for conversation: {self.conversation_id}")
                return None
            
            logger.info(f"POST_CONV_ANALYSIS: Loaded match data in {step_time:.3f}s - "
                       f"match_id={match_data['match'].id}, client='{match_data['client_name']}'")
            
            # 3. Get existing decisions for deduplication
            step_start = time.time()
            existing_decisions = await self._get_existing_decisions(db_session, match_data['match'].id)
            step_time = time.time() - step_start
            
            logger.info(f"POST_CONV_ANALYSIS: Loaded {len(existing_decisions)} existing decisions in {step_time:.3f}s")
            
            # 4. Prepare conversation metadata
            conversation_metadata = self._prepare_conversation_metadata(
                conversation_data['conversation'],
                conversation_data['messages'],
                match_data
            )
            
            # 5. Create context object
            context = AnalysisContext(
                conversation_id=self.conversation_id,
                clinician_id=match_data['match'].clinician_id,
                job_posting_match_id=match_data['match'].id,
                team_id=match_data['team_id'],
                client_id=match_data['client_id'],
                messages=self._format_messages_for_analysis(conversation_data['messages']),
                notes=self._format_notes_for_analysis(conversation_data['notes']),
                conversation_metadata=conversation_metadata,
                existing_decisions=existing_decisions,
            )
            
            total_time = time.time() - start_time
            logger.info(f"POST_CONV_ANALYSIS: SUCCESS - Assembled analysis context in {total_time:.3f}s")
            return context
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"POST_CONV_ANALYSIS: EXCEPTION - Error assembling context "
                        f"after {total_time:.3f}s: {e}", exc_info=True)
            return None
    
    async def _get_conversation_data(self, db_session: AsyncSession) -> Optional[Dict[str, Any]]:
        """Fetches conversation with all messages."""
        try:
            # Get conversation
            conv_stmt = select(Conversation).where(Conversation.id == self.conversation_id)
            conv_result = await db_session.execute(conv_stmt)
            conversation = conv_result.scalar_one_or_none()
            
            if not conversation:
                return None
            
            # Get messages ordered by timestamp
            msg_stmt = (
                select(Message)
                .where(Message.conversation_id == self.conversation_id)
                .order_by(Message.created_at)
            )
            msg_result = await db_session.execute(msg_stmt)
            messages = msg_result.scalars().all()
            
            # Get notes for the conversation
            note_stmt = select(ClinicianNote).where(ClinicianNote.conversation_id == self.conversation_id)
            note_result = await db_session.execute(note_stmt)
            notes = note_result.scalars().all()
            
            return {
                'conversation': conversation,
                'messages': messages,
                'notes': notes
            }
            
        except Exception as e:
            logger.error(f"Error fetching conversation data: {e}", exc_info=True)
            return None
    
    async def _get_match_data(
        self, 
        db_session: AsyncSession, 
        conversation: Conversation
    ) -> Optional[Dict[str, Any]]:
        """Fetches job posting match and related organizational data."""
        try:
            # Get match_id from conversation metadata or related fields
            # This assumes the conversation has a reference to the match
            match_id = getattr(conversation.context, 'match_id', None)
            
            if not match_id:
                # Try to get from conversation metadata or context
                # This might be stored differently in your system
                logger.warning(f"No match_id found for conversation: {self.conversation_id}")
                return None
            
            # Fetch match with all related data
            stmt = (
                select(JobPostingMatch)
                .where(JobPostingMatch.id == match_id)
                .options(
                    joinedload(JobPostingMatch.job_posting).joinedload(JobPosting.client),
                    joinedload(JobPostingMatch.clinician)
                )
            )
            
            result = await db_session.execute(stmt)
            match = result.scalar_one_or_none()
            
            if not match:
                return None
            
            # Get team information (assuming job posting has team_id)
            team_id = getattr(match.job_posting, 'team_id', None)
            team_name = "Unknown Team"
            
            if team_id:
                team_stmt = select(Team).where(Team.id == team_id)
                team_result = await db_session.execute(team_stmt)
                team = team_result.scalar_one_or_none()
                if team:
                    team_name = team.name
            
            return {
                'match': match,
                'job_posting': match.job_posting,
                'client': match.job_posting.client,
                'client_id': match.job_posting.client_id,
                'client_name': match.job_posting.client.name if match.job_posting.client else 'Unknown',
                'clinician': match.clinician,
                'team_id': team_id,
                'team_name': team_name
            }
            
        except Exception as e:
            logger.error(f"Error fetching match data: {e}", exc_info=True)
            return None
    
    async def _get_existing_decisions(
        self, 
        db_session: AsyncSession, 
        job_posting_match_id: UUID
    ) -> List[Dict[str, Any]]:
        """Fetches existing decisions for the same job posting match to prevent duplicates."""
        try:
            stmt = (
                select(Decision)
                .where(Decision.job_posting_match_id == job_posting_match_id)
                .order_by(Decision.created_at.desc())
            )
            
            result = await db_session.execute(stmt)
            decisions = result.scalars().all()
            
            existing_decisions = []
            for decision in decisions:
                existing_decisions.append({
                    'id': decision.id,
                    'title': decision.title,
                    'decision_type': decision.decision_type,
                    'created_at': decision.created_at,
                    'body': decision.body[:200] + '...' if len(decision.body) > 200 else decision.body
                })
            
            return existing_decisions
            
        except Exception as e:
            logger.error(f"Error fetching existing decisions: {e}", exc_info=True)
            return []
    
    def _prepare_conversation_metadata(
        self,
        conversation: Conversation,
        messages: List[Message],
        notes: List[ClinicianNote],
        match_data: Dict[str, Any]
    ) -> ConversationMetadata:
        """Prepares conversation metadata for analysis."""
        
        # Calculate timestamps
        start_timestamp = conversation.created_at
        end_timestamp = conversation.updated_at or conversation.created_at
        
        if messages:
            # Use actual message timestamps if available
            start_timestamp = messages[0].created_at
            end_timestamp = messages[-1].created_at
        
        return ConversationMetadata(
            conversation_id=conversation.id,
            clinician_id=match_data['match'].clinician_id,
            job_posting_match_id=match_data['match'].id,
            team_id=match_data['team_id'],
            client_id=match_data['client_id'],
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            message_count=len(messages),
            note_count=len(notes),
            notes_start_timestamp=notes[0].created_at if notes else None,
            notes_end_timestamp=notes[-1].created_at if notes else None
        )
    
    def _format_messages_for_analysis(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Formats messages for analysis."""
        formatted_messages = []
        
        for msg in messages:
            formatted_messages.append({
                'id': str(msg.id),
                'content': msg.content,
                'role': msg.role,
                'timestamp': msg.created_at.isoformat(),
                'metadata': getattr(msg, 'metadata', {})
            })
        
        return formatted_messages

    def _format_notes_for_analysis(self, notes: List[ClinicianNote]) -> List[Dict[str, Any]]:
        """Formats notes for analysis."""
        formatted_notes = []
        
        for note in notes:
            formatted_notes.append({
                'id': str(note.id),
                'content': note.content,
                'timestamp': note.created_at.isoformat(),
                'metadata': getattr(note, 'metadata', {}),
                'note_type': note.note_type
            })
        
        return formatted_notes