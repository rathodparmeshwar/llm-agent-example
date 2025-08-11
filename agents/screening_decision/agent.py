"""Core Screening Decision Agent implementation - Post-Conversation Analysis."""

import logging
import time
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime
from uuid import UUID

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base.agent import BaseAgent
from .context_manager import ScreeningDecisionContextManager
from .tool_orchestrator import ScreeningDecisionToolOrchestrator
from .schemas import ConversationAnalysisInput, ConversationAnalysisResult
from .prompts import load_post_conversation_assets, get_conversation_analysis_prompt

logger = logging.getLogger(__name__)


class ScreeningDecisionAgent(BaseAgent):
    """Agent for post-conversation analysis to identify recruiter intervention needs."""    
    
    def __init__(self, client: AsyncAnthropic):
        """Initialize the post-conversation analysis agent.
        
        Args:
            client: Anthropic client for Claude API access
        """
        self.client = client
        self.tool_orchestrator = ScreeningDecisionToolOrchestrator()
        
        # Load system prompt and tools
        self.system_prompt, self.tool_definitions = load_post_conversation_assets()
        
        logger.info("Initialized ScreeningDecisionAgent for post-conversation analysis")
    
    @property
    def route_code(self) -> str:
        """The route code this agent handles.
        
        Returns:
            str: The unique route code for this agent type.
        """
        return "POST-CONVERSATION-ANALYSIS"
    
    async def process_message(
        self,
        message: str,
        conversation_id: UUID,
        context: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Process a message and yield response chunks.
        
        This method is not typically used for post-conversation analysis
        as it operates on completed conversations automatically.
        
        Args:
            message: The user message
            conversation_id: The conversation ID
            context: Additional context
            
        Yields:
            str: Response chunks
        """
        yield "Post-conversation analysis agent operates automatically on completed conversations."
    
    async def analyze_conversation(
        self,
        db_session: AsyncSession,
        conversation_id: UUID,
        job_posting_match_id: UUID,
        force_reanalysis: bool = False
    ) -> ConversationAnalysisResult:
        """Analyzes a completed conversation for recruiter intervention needs.
        
        Args:
            db_session: Database session
            conversation_id: ID of the conversation to analyze
            force_reanalysis: Force reanalysis even if already processed
            
        Returns:
            ConversationAnalysisResult with analysis outcome
        """
        start_time = time.time()
        logger.info(f"Starting post-conversation analysis for: {conversation_id}")

        try:
            input_data = ConversationAnalysisInput(
                conversation_id=conversation_id,
                match_id=job_posting_match_id,
                force_reanalysis=force_reanalysis
            )           
            
            # Check if already analyzed (unless forcing reanalysis)
            if not force_reanalysis:
                already_analyzed = await self._check_already_analyzed(db_session, input_data.conversation_id)
                if already_analyzed:
                    logger.info(f"Conversation {input_data.conversation_id} already analyzed, skipping")
                    return ConversationAnalysisResult(
                        conversation_id=input_data.conversation_id,
                        analysis_completed=True,
                        decisions_created=0,
                        decisions=[],
                        processing_time=time.time() - start_time,
                        error_message="Already analyzed (use force_reanalysis=True to override)"
                    )
            
            # Assemble context
            context_manager = ScreeningDecisionContextManager(input_data)
            context = await context_manager.assemble_analysis_context(db_session)
            
            if not context:
                error_msg = "Failed to assemble conversation context"
                logger.error(error_msg)
                return ConversationAnalysisResult(
                    conversation_id=input_data.conversation_id,
                    analysis_completed=False,
                    decisions_created=0,
                    decisions=[],
                    processing_time=time.time() - start_time,
                    error_message=error_msg
                )
            
            # Conduct analysis
            analysis_result = await self._conduct_analysis(context, db_session, input_data)
            
            processing_time = time.time() - start_time
            
            if analysis_result:
                decisions_created = analysis_result.get('decisions_created', 0)
                logger.info(f"Completed post-conversation analysis in {processing_time:.3f}s - "
                           f"Created {decisions_created} decisions")
                
                return ConversationAnalysisResult(
                    conversation_id=input_data.conversation_id,
                    analysis_completed=True,
                    decisions_created=decisions_created,
                    decisions=analysis_result.get('decisions', []),
                    processing_time=processing_time
                )
            else:
                error_msg = "Analysis failed to complete"
                logger.error(error_msg)
                return ConversationAnalysisResult(
                    conversation_id=input_data.conversation_id,
                    analysis_completed=False,
                    decisions_created=0,
                    decisions=[],
                    processing_time=processing_time,
                    error_message=error_msg
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Error in post-conversation analysis: {str(e)}"
            logger.error(f"{error_msg} after {processing_time:.3f}s", exc_info=True)
            
            return ConversationAnalysisResult(
                conversation_id=input_data.conversation_id,
                analysis_completed=False,
                decisions_created=0,
                decisions=[],
                processing_time=processing_time,
                error_message=error_msg
            )
    
    async def _check_already_analyzed(
        self, 
        db_session: AsyncSession, 
        conversation_id: UUID
    ) -> bool:
        """Checks if conversation has already been analyzed."""
        try:
            from db.models.chat import Conversation
            from sqlalchemy import select
            
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            result = await db_session.execute(stmt)
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                return False
            
            context = getattr(conversation, 'context', {}) or {}
            return context.get('post_analysis_completed', False)
            
        except Exception as e:
            logger.error(f"Error checking analysis status: {e}", exc_info=True)
            return False
    
    async def _conduct_analysis(
        self,
        context,
        db_session: AsyncSession,
        input_data: ConversationAnalysisInput
    ) -> Optional[Dict[str, Any]]:
        """Conducts the actual conversation analysis using Claude."""
        try:
            # Prepare analysis prompt
            analysis_prompt = get_conversation_analysis_prompt(context.__dict__)
            
            # Call Claude with tools
            response = await self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                system=self.system_prompt,
                messages=[{"role": "user", "content": analysis_prompt}],
                tools=self.tool_definitions,
                tool_choice="auto"
            )
            
            # Process tool calls
            decisions_created = 0
            tool_results = []
            
            if response.content:
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self.tool_orchestrator.execute_tool(
                            {
                                "name": block.name,
                                "input": block.input,
                                "id": block.id
                            },
                            db_session,
                            input_data
                        )
                        tool_results.append(result)
                        
                        # Count decisions created
                        if (result.get('success') and 
                            result.get('tool_name') == 'create_intervention_decision'):
                            decisions_created += 1
            
            return {
                "decisions_created": decisions_created,
                "tool_results": tool_results,
                "decisions": []  # Would be populated with actual decision objects
            }
            
        except Exception as e:
            logger.error(f"Error conducting analysis: {e}", exc_info=True)
            return None
