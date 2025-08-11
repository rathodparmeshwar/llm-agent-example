"""Prompt templates for the Screening Decision Agent - Post-Conversation Analysis."""

import json
from typing import Dict, Any, List
from pathlib import Path

# Tool definitions for post-conversation analysis
POST_CONVERSATION_ANALYSIS_TOOLS = [
    {
        "name": "create_intervention_decision",
        "description": "Creates a decision record when recruiter intervention is needed",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Descriptive title for the intervention decision"
                },
                "body": {
                    "type": "string", 
                    "description": "Detailed body explaining the intervention need"
                },
                "decision_type": {
                    "type": "string",
                    "enum": ["clinician_question", "information_request", "special_accommodation", "scheduling_conflict"],
                    "description": "Type of intervention needed"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Priority level for the intervention"
                },
                "quoted_excerpts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Relevant quoted excerpts from the conversation"
                },
                "ai_reasoning": {
                    "type": "string",
                    "description": "AI reasoning for why this intervention is needed"
                },
                "team_id": {"type": "string", "description": "Team ID for access control"},
                "client_id": {"type": "string", "description": "Client ID for access control"},
                "job_posting_match_id": {"type": "string", "description": "Job posting match ID"},
                "clinician_id": {"type": "string", "description": "Clinician ID"},
                "related_message_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "IDs of messages that triggered this decision"
                }
            },
            "required": ["title", "body", "decision_type", "priority", "quoted_excerpts", "ai_reasoning", "team_id", "client_id", "job_posting_match_id", "clinician_id"]
        }
    },
    {
        "name": "check_duplicate_decision",
        "description": "Checks if a similar decision already exists to prevent duplicates",
        "input_schema": {
            "type": "object",
            "properties": {
                "decision_title": {"type": "string", "description": "Title of the decision to check"},
                "decision_type": {"type": "string", "description": "Type of decision"},
                "job_posting_match_id": {"type": "string", "description": "Job posting match ID"},
                "time_window_hours": {"type": "number", "default": 24, "description": "Time window in hours to check for duplicates"}
            },
            "required": ["decision_title", "decision_type", "job_posting_match_id"]
        }
    },
    {
        "name": "update_conversation_status",
        "description": "Updates the conversation status after analysis completion",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Analysis status"},
                "analysis_completed": {"type": "boolean", "description": "Whether analysis completed successfully"},
                "decisions_created": {"type": "number", "description": "Number of decisions created"}
            },
            "required": ["status", "analysis_completed", "decisions_created"]
        }
    }
]


def get_post_conversation_system_prompt() -> str:
    """Returns the system prompt for post-conversation analysis."""
    return """You are a specialized AI agent in the Wakura Healthcare Recruiting Platform. Your role is to analyze completed conversations between clinicians and the Clinician Agent (Wakura) to identify situations that require human recruiter intervention.

## Core Responsibilities

1. **Conversation Analysis**: Analyze complete chat transcripts to identify intervention needs
2. **Pattern Recognition**: Detect when Wakura reached its limits or deflected questions
3. **Escalation Detection**: Identify situations requiring human expertise
4. **Decision Creation**: Create structured decision records for recruiter review
5. **Duplicate Prevention**: Avoid creating duplicate decisions for similar issues

## Intervention Detection Criteria

### 1. Clinician Question (`clinician_question`)
- Clinician asks questions that Wakura explicitly deflects or cannot answer
- AI admits uncertainty or redirects to human contact
- Questions about complex policies, procedures, or company-specific information
- **Priority**: Usually medium to high depending on urgency

### 2. Information Request (`information_request`)
- Requests for detailed information beyond AI's knowledge base
- Specific client policies, benefits details, or role-specific information
- Documentation requests or forms that require human processing
- **Priority**: Usually low to medium

### 3. Special Accommodation (`special_accommodation`)
- Requests for exceptions to standard hiring workflows
- Accommodation needs for disabilities or special circumstances
- Negotiation requests for compensation, schedules, or terms
- **Priority**: Usually medium to high

### 4. Scheduling Conflict (`scheduling_conflict`)
- Complex scheduling issues that require manual coordination
- Multiple stakeholder calendar conflicts
- Urgent scheduling changes or availability issues
- **Priority**: Usually medium, high if urgent

## Analysis Process

1. **Read the full conversation** from start to finish
2. **Identify deflection patterns** where Wakura says it cannot help
3. **Extract key quotes** that demonstrate the intervention need
4. **Categorize the intervention type** based on the content
5. **Assess priority level** based on urgency and impact
6. **Check for duplicates** to avoid redundant decisions
7. **Create decision record** with proper access controls

## Decision Quality Standards

### Title Requirements
- Clear, descriptive, and specific
- Include key context (clinician name, job type, or main issue)
- 50-80 characters for optimal readability

### Body Requirements
- Provide context about the conversation
- Explain what the clinician needs
- Indicate why AI intervention was insufficient
- Include actionable next steps for recruiters

### Quote Selection
- Choose 1-3 most relevant excerpts
- Focus on the specific request or question
- Include any AI deflection responses
- Keep quotes concise but meaningful

### Priority Assignment
- **High**: Urgent needs, time-sensitive issues, critical questions
- **Medium**: Important but not urgent, standard intervention needs
- **Low**: Informational requests, non-urgent clarifications

## Access Control and Scope

Every decision must be properly scoped to:
- **Team ID**: The recruiting team handling this match
- **Client ID**: The healthcare client/organization
- **Job Posting Match ID**: The specific candidate-job pairing

Only recruiters with access to that specific team-client-job combination should see the decision.

## Quality Checks

Before creating a decision:
1. **Relevance**: Does this truly need human intervention?
2. **Clarity**: Is the need clearly articulated?
3. **Completeness**: Are all required fields populated?
4. **Duplication**: Has a similar decision been created recently?
5. **Access**: Are the organizational IDs correct?

## Communication Style

- Be professional and clear in all decision records
- Focus on facts and specific needs rather than assumptions
- Provide enough context for recruiters to take immediate action
- Use recruiting terminology and healthcare industry language appropriately

Remember: Your goal is to make recruiters more efficient by surfacing the right decisions at the right time to the right people, ensuring nothing falls through the cracks while respecting organizational boundaries and recruiter preferences."""


def get_conversation_analysis_prompt(context: Dict[str, Any]) -> str:
    """Generates the analysis prompt with conversation context."""
    
    conversation_metadata = context.get('conversation_metadata', {})
    messages = context.get('messages', [])
    existing_decisions = context.get('existing_decisions', [])
    notes = context.get('notes', [])
    
    clinician_id = conversation_metadata.get('clinician_id', 'Unknown')
    job_posting_match_id = conversation_metadata.get('job_posting_match_id', 'Unknown')
    team_id = conversation_metadata.get('team_id', 'Unknown')
    client_id = conversation_metadata.get('client_id', 'Unknown')
    
    return f"""# POST-CONVERSATION ANALYSIS REQUEST

## Conversation Metadata
- **Conversation ID**: {conversation_metadata.get('conversation_id', 'Unknown')}
- **Clinician ID**: {clinician_id}
- **Job Posting Match ID**: {job_posting_match_id}
- **Team ID**: {team_id}
- **Client ID**: {client_id}
- **Duration**: {conversation_metadata.get('start_timestamp', 'Unknown')} to {conversation_metadata.get('end_timestamp', 'Unknown')}
- **Message Count**: {conversation_metadata.get('message_count', 0)}
- **Note Count**: {conversation_metadata.get('note_count', 0)}

## Existing Decisions (for deduplication)
{json.dumps(existing_decisions, indent=2) if existing_decisions else "No existing decisions found."}

## Full Conversation Transcript

{chr(10).join([f"**{msg['role'].upper()} ({msg['timestamp']})**: {msg['content']}" for msg in messages])}

## Clinician Notes

{chr(10).join([f"**NOTE ({note['timestamp']}) - {note['note_type']}**: {note['content']}" for note in notes]) if notes else "No notes found."}

## Analysis Instructions

1. **Carefully read the entire conversation** from start to finish
2. **Review all clinician notes** for additional context and concerns
3. **Identify any moments** where the clinician asks questions that Wakura:
   - Cannot answer due to knowledge limitations
   - Explicitly deflects to human contact
   - Provides insufficient or vague responses
   - Admits uncertainty about company-specific information

4. **Look for specific patterns** indicating intervention needs:
   - "I don't have access to that information"
   - "You'll need to contact your recruiter"
   - "That's outside my scope"
   - "I'd recommend speaking with someone who can..."
   - Requests for specific documentation or forms
   - Complex scheduling or accommodation requests
   - Issues or concerns documented in clinician notes

5. **For each intervention need identified**:
   - Determine the appropriate decision type
   - Assess the priority level
   - Extract relevant quotes that demonstrate the need
   - Include relevant note content if applicable
   - Create a decision record with proper organizational scope

6. **Check for duplicates** before creating any decisions to avoid redundancy

7. **Update conversation status** to indicate analysis completion

Focus on genuine intervention needs where human expertise, access, or authority is required. Do not create decisions for routine interactions or questions that were adequately answered by the AI.

Use the provided tools to create decision records and update conversation status."""


def load_post_conversation_assets() -> tuple[str, List[Dict[str, Any]]]:
    """Loads the system prompt and tool definitions for post-conversation analysis.
    
    Returns:
        Tuple of (system_prompt, tool_definitions)
    """
    try:
        # Get the directory containing this file
        current_dir = Path(__file__).parent
        
        # Try to load system prompt from file first
        prompt_path = current_dir / "prompt_assets" / "system_prompt.md"
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
        else:
            # Fallback to built-in prompt
            system_prompt = get_post_conversation_system_prompt()
        
        # Try to load tool definitions from file first
        tools_path = current_dir / "prompt_assets" / "tools.json"
        if tools_path.exists():
            with open(tools_path, 'r', encoding='utf-8') as f:
                tool_definitions = json.load(f)
        else:
            # Fallback to built-in tools
            tool_definitions = POST_CONVERSATION_ANALYSIS_TOOLS
        
        return system_prompt, tool_definitions
        
    except Exception as e:
        # Fallback to built-in assets
        return get_post_conversation_system_prompt(), POST_CONVERSATION_ANALYSIS_TOOLS
