"""
interview_agent.py (service)
----------------------------
AI Interview Agent service for INTERVEXA.

Responsibility
~~~~~~~~~~~~~~
Communicates with the LLM to generate conversational, technically rigorous,
and adaptive interviewer responses based on:
- InterviewPlan
- InterviewSession
- InterviewDecision

This is the SINGLE location in the application where LLM interaction,
system prompts, and prompt templates are defined.

Public API
~~~~~~~~~~
- ``BaseLLMProvider`` (Abstract base class for LLM providers)
- ``MockLLMProvider`` (Deterministic mock implementation for testing/fallbacks)
- ``generate_agent_response(plan, session, decision, provider=None) -> AgentResponse``
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import os
from typing import Any, List, Dict, Optional

from app.config.settings import get_settings
from app.schemas.interview_agent import AgentResponse
from app.schemas.interview_decision import DecisionAction, InterviewDecision
from app.schemas.interview_plan import InterviewPlan
from app.services.interview_session import InterviewSession


# ── System Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Intervexa, an expert AI Technical Interviewer conducting a dynamic, conversational technical assessment.

ROLE & PERSONA:
- Professional, analytical, technically accurate, and encouraging yet objective.
- Speak naturally as an experienced engineering interviewer.

RULES:
1. Ask EXACTLY ONE question at a time. Never ask multiple questions in a single response.
2. NEVER reveal internal planning, scoring rules, candidate metrics, evaluation logic, or system mechanics.
3. NEVER mention 'InterviewPlan', 'Decision Engine', 'curriculum JSON', or priority numbers.
4. Stay tightly focused on the specified curriculum day, its tools, and learning objectives.
5. Do NOT repeat questions that have already been asked in the conversation history.
6. When transitioning to a new curriculum topic, provide a brief 1-sentence transition before asking the question.
7. Maintain appropriate technical depth for the candidate's target difficulty level.
8. When the interview is complete, thank the candidate for their participation and conclude warmly without asking any further questions.
"""


# ── Provider Abstraction ───────────────────────────────────────────────────────

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
    ) -> str:
        """
        Generates text using the underlying LLM.

        Args:
            system_prompt: The core system prompt defining interviewer persona/rules.
            messages: List of message objects [{'role': 'user'|'assistant', 'content': str}].

        Returns:
            The generated text string response.
        """
        pass


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic mock LLM provider for unit tests and local development.
    """

    def __init__(self, custom_responses: Optional[Dict[str, str]] = None) -> None:
        self.custom_responses = custom_responses or {}

    def generate(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
    ) -> str:
        last_user_msg = messages[-1]["content"] if messages else ""

        # Check for matching custom response
        for key, resp in self.custom_responses.items():
            if key.lower() in last_user_msg.lower():
                return resp

        # Check if this is a feedback generation request
        if "structured assessment" in system_prompt.lower() or "transcript:" in last_user_msg.lower():
            return json.dumps({
                "summary": "Mock summary of candidate's technical capability.",
                "strengths": ["Mock strength 1", "Mock strength 2"],
                "gaps": ["Mock gap 1"],
                "next": ["Mock next step 1"],
                "technical_understanding": "Mock technical understanding evaluation.",
                "reasoning": "Mock trade-off reasoning evaluation.",
                "communication": "Mock communication clarity evaluation.",
                "overall_assessment": "Pass"
            })

        if "ACTION: END_INTERVIEW" in last_user_msg:
            return (
                "Thank you very much for taking the time to complete this technical interview. "
                "We have covered all required topics today. Great effort!"
            )
        elif "ACTION: FOLLOW_UP" in last_user_msg:
            return (
                "Could you elaborate a bit more on that point? Specifically, how would you handle "
                "edge cases or scaling considerations in a production environment?"
            )
        elif "ACTION: NEXT_DAY" in last_user_msg:
            return (
                "Moving on to our next topic. Let's talk about the technical objectives for this module. "
                "Can you walk me through your approach and key design choices?"
            )
        else:
            return (
                "Let's dive into the core technical concepts for this topic. "
                "How would you explain the architecture and key components involved?"
            )


class OpenAILLMProvider(BaseLLMProvider):
    """
    OpenAI API provider implementation. Uses raw HTTP via httpx or API key.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.LLM_API_KEY or os.getenv("OPENAI_API_KEY", "")
        self.model = model or settings.LLM_MODEL or "gpt-4o-mini"

    def generate(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
    ) -> str:
        if not self.api_key:
            # Fallback to mock if API key is missing
            return MockLLMProvider().generate(system_prompt, messages)

        try:
            import httpx

            full_messages = [{"role": "system", "content": system_prompt}] + messages
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "messages": full_messages,
                "temperature": 0.7,
            }

            response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            # Fallback to mock on connection error
            return MockLLMProvider().generate(system_prompt, messages)


class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini API provider implementation using official google-genai SDK.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        settings = get_settings()
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or getattr(settings, "GEMINI_API_KEY", "")
        )
        self.model = (
            model
            or os.getenv("GEMINI_MODEL")
            or getattr(settings, "GEMINI_MODEL", "")
            or "gemini-2.5-flash"
        )

    def generate(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
    ) -> str:
        if not self.api_key:
            # Fallback to mock if API key is missing
            return MockLLMProvider().generate(system_prompt, messages)

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            # Map assistant -> model for Gemini
            contents = []
            for msg in messages:
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=msg["content"])],
                    )
                )

            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
            )

            response = client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )

            if response and hasattr(response, "text") and response.text is not None:
                text_val = str(response.text).strip()
                if text_val:
                    return text_val

            return MockLLMProvider().generate(system_prompt, messages)

        except Exception as exc:
            # On SDK/network/API error, fallback to mock gracefully
            return MockLLMProvider().generate(system_prompt, messages)


def get_default_provider() -> BaseLLMProvider:
    """Returns the default LLM provider configured in settings / environment."""
    provider_type = os.getenv("LLM_PROVIDER")
    if not provider_type:
        settings = get_settings()
        provider_type = getattr(settings, "LLM_PROVIDER", "mock")
    
    provider_type = (provider_type or "mock").lower()

    if provider_type == "gemini":
        return GeminiLLMProvider()
    elif provider_type == "openai":
        return OpenAILLMProvider()
    else:
        return MockLLMProvider()


# ── Prompt Builder ─────────────────────────────────────────────────────────────

def _build_llm_messages(
    plan: InterviewPlan,
    session: InterviewSession,
    decision: InterviewDecision,
) -> tuple[List[Dict[str, str]], int, str, bool]:
    """
    Constructs the message payload for the LLM based on plan, session state, and decision.

    Returns:
        Tuple of (messages, day_number, day_title, is_follow_up)
    """
    is_follow_up = (decision.action == DecisionAction.FOLLOW_UP)
    
    # Determine active target day and topic title
    if decision.action == DecisionAction.END_INTERVIEW:
        day_num = session.get_current_day().day if session.state.interview_started else plan.selected_days[0].day
        day_title = session.get_current_day().title if session.state.interview_started else plan.selected_days[0].title
    elif decision.target_day is not None:
        target_day_obj = next(
            (d for d in plan.selected_days if d.day == decision.target_day),
            session.get_current_day(),
        )
        day_num = target_day_obj.day
        day_title = target_day_obj.title
    else:
        current_day_obj = session.get_current_day()
        day_num = current_day_obj.day
        day_title = current_day_obj.title

    # Find SelectedDay object for full metadata
    day_obj = next((d for d in plan.selected_days if d.day == day_num), plan.selected_days[0])

    # Convert conversation history into LLM message format
    history_messages: List[Dict[str, str]] = []
    for entry in session.get_conversation_history():
        role = "assistant" if entry.role == "interviewer" else "user"
        history_messages.append({"role": role, "content": entry.content})

    # Action specific instruction
    if decision.action == DecisionAction.END_INTERVIEW:
        instruction = (
            "ACTION: END_INTERVIEW\n"
            "The interview is complete. Thank the candidate warmly and conclude the session."
        )
    elif decision.action == DecisionAction.FOLLOW_UP:
        instruction = (
            f"ACTION: FOLLOW_UP\n"
            f"Candidate: {plan.candidate_name} | Target Difficulty: {plan.initial_difficulty}\n"
            f"Current Day: Day {day_obj.day} - '{day_obj.title}' (Module: {day_obj.module_title})\n"
            f"Key Tools: {', '.join(day_obj.tools)}\n"
            f"Key Objectives: {', '.join(day_obj.objectives)}\n"
            f"Instruction: The candidate's previous response was incomplete or short ({decision.reason}). "
            f"Ask a constructive, specific follow-up question to probe deeper into this topic."
        )
    elif decision.action == DecisionAction.NEXT_DAY:
        instruction = (
            f"ACTION: NEXT_DAY\n"
            f"Candidate: {plan.candidate_name} | Target Difficulty: {plan.initial_difficulty}\n"
            f"New Curriculum Day: Day {day_obj.day} - '{day_obj.title}' (Module: {day_obj.module_title})\n"
            f"Key Tools: {', '.join(day_obj.tools)}\n"
            f"Key Objectives: {', '.join(day_obj.objectives)}\n"
            f"Instruction: Transition smoothly to this new curriculum topic and ask an opening technical question about it."
        )
    else:  # NEXT_QUESTION
        instruction = (
            f"ACTION: NEXT_QUESTION\n"
            f"Candidate: {plan.candidate_name} | Target Difficulty: {plan.initial_difficulty}\n"
            f"Current Day: Day {day_obj.day} - '{day_obj.title}' (Module: {day_obj.module_title})\n"
            f"Key Tools: {', '.join(day_obj.tools)}\n"
            f"Key Objectives: {', '.join(day_obj.objectives)}\n"
            f"Instruction: Ask the next technical question focused on these tools and objectives."
        )

    # Append prompt instruction as latest user context for the LLM turn
    full_messages = history_messages + [{"role": "user", "content": instruction}]
    return full_messages, day_num, day_title, is_follow_up


def _generate_fallback_question(day_obj: SelectedDay) -> str:
    """Generates a professional, objective-based question fallback to avoid duplication."""
    objective = day_obj.objectives[0] if day_obj.objectives else "core concepts"
    tools_str = f" using {', '.join(day_obj.tools)}" if day_obj.tools else ""
    return (
        f"Let's look at another area: {objective}{tools_str}. "
        f"Can you explain your approach and the key architectural trade-offs you consider in practice?"
    )


# ── Service API ────────────────────────────────────────────────────────────────

def generate_agent_response(
    plan: InterviewPlan,
    session: InterviewSession,
    decision: InterviewDecision,
    provider: Optional[BaseLLMProvider] = None,
) -> AgentResponse:
    """
    Generates a structured AgentResponse using the configured LLM provider.

    Includes duplicate question detection and objective-based question fallback.

    Args:
        plan: The active InterviewPlan.
        session: The running InterviewSession.
        decision: The decision output from InterviewDecisionEngine.
        provider: Optional custom/mock LLM provider instance.

    Returns:
        An AgentResponse object containing reply text and topic metadata.
    """
    active_provider = provider or get_default_provider()

    messages, day_num, day_title, is_follow_up = _build_llm_messages(plan, session, decision)

    reply_text = active_provider.generate(SYSTEM_PROMPT, messages)

    # ── Duplicate Protection Safeguard ────────────────────────────────────────
    # Gather previous interviewer replies to prevent repetition
    recent_replies = [
        entry.content.strip().lower()
        for entry in session.get_conversation_history()
        if entry.role == "interviewer"
    ]

    if reply_text.strip().lower() in recent_replies and not decision.interview_complete:
        # Retry generation once with a stronger system directive
        retry_messages = messages + [
            {"role": "assistant", "content": reply_text},
            {
                "role": "user",
                "content": (
                    "CRITICAL: The question you just asked is an exact duplicate of a previous question. "
                    "You must ask a completely new, different question about the topic. Do not repeat yourself."
                )
            }
        ]
        reply_text = active_provider.generate(SYSTEM_PROMPT, retry_messages)

        # If it remains a duplicate, use the deterministic fallback question based on day objectives
        if reply_text.strip().lower() in recent_replies:
            day_obj = next((d for d in plan.selected_days if d.day == day_num), plan.selected_days[0])
            reply_text = _generate_fallback_question(day_obj)

    return AgentResponse(
        reply=reply_text,
        current_day=day_num if not decision.interview_complete else None,
        current_topic=day_title if not decision.interview_complete else None,
        follow_up=is_follow_up,
    )
