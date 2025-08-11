"""Tool orchestrator for the Screening Decision Agent - Post-Conversation Analysis."""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import ConversationAnalysisInput, InterventionDecision, DecisionType, DecisionPriority

logger = logging.getLogger(__name__)


class ScreeningDecisionToolOrchestrator:
    """Orchestrates tool execution for post-conversation analysis and decision creation."""
    
    def __init__(self):
        """Initialize the tool orchestrator with available tools."""
        self.tool_functions = {
            "create_intervention_decision": self._create_intervention_decision,
            "check_duplicate_decision": self._check_duplicate_decision,
            "update_conversation_status": self._update_conversation_status,
            "notify_recruiters": self._notify_recruiters
        }
        
        logger.info(f"Initialized ScreeningDecisionToolOrchestrator with {len(self.tool_functions)} tools")
    
    async def execute_tool(
        self,
        tool_block: Dict[str, Any],
        db_session: AsyncSession,
        input_data: ConversationAnalysisInput
    ) -> Dict[str, Any]:
        """Executes a single tool and returns the result.
        
        Args:
            tool_block: Tool call information from LLM
            db_session: Database session
            input_data: Input context data
            
        Returns:
            Dictionary containing execution result
        """
        tool_name = tool_block.get("name")
        tool_input = tool_block.get("input", {})
        tool_id = tool_block.get("id")
        
        start_time = time.time()
        logger.info(f"Executing post-conversation tool: {tool_name} (ID: {tool_id})")
        logger.debug(f"Tool input received: {type(tool_input)} - {tool_input}")
        
        if tool_name not in self.tool_functions:
            logger.error(f"Tool function not found: {tool_name}")
            return {
                "success": False,
                "error": f"Tool function '{tool_name}' not found"
            }
        
        try:
            # Prepare tool arguments
            final_tool_args = await self._prepare_tool_arguments(
                tool_name,
                tool_input,
                db_session,
                input_data
            )
            
            # Execute the tool function
            tool_func = self.tool_functions[tool_name]
            result = await tool_func(**final_tool_args)
            
            execution_time = time.time() - start_time
            logger.info(f"Tool {tool_name} (ID: {tool_id}) completed successfully in {execution_time:.3f}s")
            
            return {
                "success": True,
                "result": result,
                "tool_name": tool_name,
                "tool_id": tool_id,
                "execution_time": execution_time
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing tool {tool_name} (ID: {tool_id}) after {execution_time:.3f}s: {e}", 
                        exc_info=True)
            
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name,
                "tool_id": tool_id,
                "execution_time": execution_time
            }
    
    async def _prepare_tool_arguments(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        db_session: AsyncSession,
        input_data: ConversationAnalysisInput
    ) -> Dict[str, Any]:
        """Prepares arguments for tool execution.
        
        Args:
            tool_name: Name of the tool being executed
            tool_input: Input from LLM tool call
            db_session: Database session
            input_data: Agent input context
            
        Returns:
            Dictionary of prepared arguments
        """
        # Base arguments that all tools receive
        base_args = {
            "db_session": db_session,
            "conversation_id": input_data.conversation_id
        }
        
        # Tool-specific argument preparation
        if tool_name == "create_intervention_decision":
            return {
                **base_args,
                "title": tool_input.get("title"),
                "body": tool_input.get("body"),
                "decision_type": tool_input.get("decision_type"),
                "priority": tool_input.get("priority"),
                "quoted_excerpts": tool_input.get("quoted_excerpts", []),
                "ai_reasoning": tool_input.get("ai_reasoning"),
                "team_id": tool_input.get("team_id"),
                "client_id": tool_input.get("client_id"),
                "job_posting_match_id": tool_input.get("job_posting_match_id"),
                "clinician_id": tool_input.get("clinician_id"),
                "related_message_ids": tool_input.get("related_message_ids", [])
            }
        
        elif tool_name == "check_duplicate_decision":
            return {
                **base_args,
                "decision_title": tool_input.get("decision_title"),
                "decision_type": tool_input.get("decision_type"),
                "job_posting_match_id": tool_input.get("job_posting_match_id"),
                "time_window_hours": tool_input.get("time_window_hours", 24)
            }
        
        elif tool_name == "update_conversation_status":
            return {
                **base_args,
                "status": tool_input.get("status"),
                "analysis_completed": tool_input.get("analysis_completed", True),
                "decisions_created": tool_input.get("decisions_created", 0)
            }
        
        elif tool_name == "notify_recruiters":
            return {
                **base_args,
                "decision_id": tool_input.get("decision_id"),
                "team_id": tool_input.get("team_id"),
                "client_id": tool_input.get("client_id"),
                "priority": tool_input.get("priority"),
                "notification_type": tool_input.get("notification_type", "new_decision")
            }
        
        # Default argument preparation
        return {**base_args, **tool_input}
    
    # Tool implementation methods
    async def _create_intervention_decision(
        self,
        db_session: AsyncSession,
        title: str,
        body: str,
        decision_type: str,
        priority: str,
        quoted_excerpts: List[str],
        ai_reasoning: str,
        team_id: UUID,
        client_id: UUID,
        job_posting_match_id: UUID,
        clinician_id: UUID,
        related_message_ids: List[str]
    ) -> Dict[str, Any]:
        """Creates an intervention decision record."""
        try:
            from db.models.decision import Decision
            
            # Create decision record
            decision = Decision(
                title=title,
                description=body,
                type=decision_type,
                priority=priority,                
                client_id=client_id,
                job_posting_id=job_posting_match_id,
                clinician_id=clinician_id,
                ai_rationale=ai_reasoning,
                context_data=quoted_excerpts,
                status="pending",
                created_by=clinician_id,
                decided_at=datetime.utcnow()
            )
            
            db_session.add(decision)
            await db_session.flush()
            
            logger.info(f"Created intervention decision record with ID: {decision.id}")
            
            return {
                "decision_id": str(decision.id),
                "title": title,
                "type": decision_type,
                "priority": priority,
                "created_at": decision.created_at.isoformat(),
                "team_id": str(team_id),
                "client_id": str(client_id),
                "job_posting_match_id": str(job_posting_match_id)
            }
            
        except Exception as e:
            logger.error(f"Error creating intervention decision: {e}", exc_info=True)
            raise
    
    async def _check_duplicate_decision(
        self,
        db_session: AsyncSession,
        conversation_id: UUID,
        decision_title: str,
        decision_type: str,
        job_posting_match_id: UUID,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Checks for duplicate decisions within a time window."""
        try:
            from db.models.decision import Decision
            from sqlalchemy import and_, select
            from datetime import timedelta
            
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            
            stmt = (
                select(Decision)
                .where(
                    and_(
                        Decision.job_posting_match_id == job_posting_match_id,
                        Decision.decision_type == decision_type,
                        Decision.created_at >= cutoff_time,
                        Decision.title.ilike(f"%{decision_title.lower()}%")
                    )
                )
                .order_by(Decision.created_at.desc())
                .limit(5)
            )
            
            result = await db_session.execute(stmt)
            existing_decisions = result.scalars().all()
            
            is_duplicate = len(existing_decisions) > 0
            
            duplicate_info = []
            if is_duplicate:
                for decision in existing_decisions:
                    duplicate_info.append({
                        "id": str(decision.id),
                        "title": decision.title,
                        "created_at": decision.created_at.isoformat(),
                        "similarity_score": self._calculate_title_similarity(decision_title, decision.title)
                    })
            
            return {
                "is_duplicate": is_duplicate,
                "duplicate_count": len(existing_decisions),
                "duplicate_decisions": duplicate_info,
                "time_window_hours": time_window_hours
            }
            
        except Exception as e:
            logger.error(f"Error checking duplicate decision: {e}", exc_info=True)
            return {
                "is_duplicate": False,
                "duplicate_count": 0,
                "duplicate_decisions": [],
                "error": str(e)
            }
    
    async def _update_conversation_status(
        self,
        db_session: AsyncSession,
        conversation_id: UUID,
        status: str,
        analysis_completed: bool = True,
        decisions_created: int = 0
    ) -> Dict[str, Any]:
        """Updates conversation status after analysis."""
        try:
            from db.models.chat import Conversation
            from sqlalchemy import select
            
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            result = await db_session.execute(stmt)
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                raise ValueError(f"Conversation not found with ID: {conversation_id}")
            
            # Update conversation metadata
            conversation_metadata = getattr(conversation, 'metadata', {}) or {}
            conversation_metadata.update({
                'post_analysis_completed': analysis_completed,
                'decisions_created': decisions_created,
                'analysis_status': status,
                'analyzed_at': datetime.utcnow().isoformat()
            })
            
            conversation.metadata = conversation_metadata
            conversation.updated_at = datetime.utcnow()
            
            await db_session.flush()
            
            logger.info(f"Updated conversation status for: {conversation_id}")
            
            return {
                "conversation_id": str(conversation_id),
                "status": status,
                "analysis_completed": analysis_completed,
                "decisions_created": decisions_created,
                "updated_at": conversation.updated_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating conversation status: {e}", exc_info=True)
            raise
    
    async def _notify_recruiters(
        self,
        db_session: AsyncSession,
        conversation_id: UUID,
        decision_id: UUID,
        team_id: UUID,
        client_id: UUID,
        priority: str,
        notification_type: str = "new_decision"
    ) -> Dict[str, Any]:
        """Notifies relevant recruiters about new decisions (placeholder implementation)."""
        logger.info(f"Notifying recruiters about {notification_type} for decision: {decision_id}")
        logger.info(f"Team: {team_id}, Client: {client_id}, Priority: {priority}")
        
        # TODO: Implement actual notification logic
        # This could integrate with:
        # - WebSocket notifications for real-time updates
        # - Email notifications for high-priority decisions
        # - Slack/Teams integration
        # - In-app notification system
        
        # Check recruiter mute preferences
        # This would query the user preferences table to see if recruiters have muted this client
        
        return {
            "notification_sent": True,
            "notification_type": notification_type,
            "decision_id": str(decision_id),
            "team_id": str(team_id),
            "client_id": str(client_id),
            "priority": priority,
            "sent_at": datetime.utcnow().isoformat(),
            "recipients": []  # Would be populated with actual recipient list
        }
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculates similarity between two decision titles."""
        # Simple word-based similarity calculation
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
