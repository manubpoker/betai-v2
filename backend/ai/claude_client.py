"""
Claude AI Client for BetAI v2

CRITICAL: This client uses Claude API directly with NO FALLBACKS.
If API is unavailable, an exception is raised - never return mock data.
"""

import os
import anthropic
from datetime import datetime


class ClaudeClient:
    """
    Claude API client for AI chat functionality.

    IMPORTANT:
    - NO fallback responses
    - NO template/mock responses
    - If API fails, exception propagates to caller
    """

    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Set it with: export ANTHROPIC_API_KEY=your_key_here"
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"  # Primary model
        self.last_successful_call = None

    def chat(self, message: str, conversation_history: list = None) -> dict:
        """
        Send message to Claude API.

        Args:
            message: User message to send
            conversation_history: Previous messages in conversation

        Returns:
            dict with:
                - response: AI response text
                - model: Model ID used (MUST start with 'claude-')
                - response_source: MUST be 'claude_api'

        Raises:
            Exception if API call fails - NO FALLBACK TO MOCK
        """
        messages = []

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": message})

        # System prompt for betting assistant
        system_prompt = """You are BetAI, a helpful AI betting assistant for the BetAI platform.

You help users with:
- Understanding betting odds and terminology
- Analyzing events and providing insights
- Explaining back and lay betting (exchange)
- Discussing betting strategies responsibly
- Providing information about sports events

IMPORTANT: You have access to REAL betting data scraped from Betfair.
When discussing odds or events, reference the actual data available on the platform.

Always promote responsible gambling and remind users to:
- Only bet what they can afford to lose
- Set limits on their betting
- Take breaks if gambling becomes stressful

Never guarantee outcomes or claim to predict winners with certainty."""

        # Call Claude API - NO try/except with fallback
        # Let exceptions propagate to indicate service unavailable
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )

        self.last_successful_call = datetime.utcnow().isoformat() + 'Z'

        # Return response with source verification fields
        return {
            "response": response.content[0].text,
            "model": self.model,  # MUST contain 'claude-'
            "response_source": "claude_api"  # MUST be 'claude_api', never 'mock'
        }

    def get_status(self) -> dict:
        """
        Check Claude API connection status.

        Returns:
            dict with:
                - status: 'connected' or 'error'
                - model: Model ID if connected
                - api_key_present: Boolean
                - last_successful_call: ISO timestamp or None
        """
        try:
            # Make a minimal API call to verify connection
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )

            self.last_successful_call = datetime.utcnow().isoformat() + 'Z'

            return {
                "status": "connected",
                "model": self.model,
                "api_key_present": True,
                "last_successful_call": self.last_successful_call
            }

        except anthropic.AuthenticationError:
            return {
                "status": "error",
                "model": None,
                "api_key_present": True,
                "error": "Invalid API key",
                "last_successful_call": self.last_successful_call
            }

        except anthropic.RateLimitError:
            return {
                "status": "rate_limited",
                "model": self.model,
                "api_key_present": True,
                "error": "Rate limit exceeded",
                "last_successful_call": self.last_successful_call
            }

        except Exception as e:
            return {
                "status": "error",
                "model": None,
                "api_key_present": bool(self.api_key),
                "error": str(e),
                "last_successful_call": self.last_successful_call
            }
