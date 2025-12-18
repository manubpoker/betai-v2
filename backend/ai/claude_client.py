"""
Claude AI Client for BetAI v2

CRITICAL: This client uses Claude API directly with NO FALLBACKS.
If API is unavailable, an exception is raised - never return mock data.

Features:
- Tool use for database queries and live scraping
- Web search capability for match research
- Code interpreter for odds analysis
"""

import os
import json
import anthropic
from datetime import datetime
from .tools import TOOLS, execute_tool


class ClaudeClient:
    """
    Claude API client for AI chat functionality with tool use.

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
        self.model = "claude-opus-4-5-20251101"  # Primary model
        self.last_successful_call = None

        # Extended tools including web search and code interpreter
        # Use Claude's native web search (server-side, more reliable than DuckDuckGo)
        self.web_search_tool = {
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 5
        }

        self.tools = TOOLS + [
            {
                "name": "analyze_odds",
                "description": "Execute Python code to analyze odds, calculate expected value, compare bookmaker margins, or perform statistical analysis. Returns the code output.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute for odds analysis"
                        },
                        "description": {
                            "type": "string",
                            "description": "Brief description of what the analysis does"
                        }
                    },
                    "required": ["code"]
                }
            }
        ]

    def chat(self, message: str, conversation_history: list = None, context: dict = None) -> dict:
        """
        Send message to Claude API with tool use support.

        Args:
            message: User message to send
            conversation_history: Previous messages in conversation
            context: Optional context like event data for match intelligence

        Returns:
            dict with:
                - response: AI response text
                - model: Model ID used (MUST start with 'claude-')
                - response_source: MUST be 'claude_api'
                - tool_calls: List of tools that were called

        Raises:
            Exception if API call fails - NO FALLBACK TO MOCK
        """
        messages = []

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": message})

        # System prompt for betting assistant with tool capabilities
        system_prompt = """You are BetAI, an intelligent betting research assistant. You HAVE ACCESS TO REAL TOOLS that you MUST use to provide accurate, data-driven responses. DO NOT say you don't have access to data - USE YOUR TOOLS.

**CRITICAL: You have the following tools available - USE THEM:**

1. `query_events` - Search the betting database for events. Use this to find matches.
2. `get_event_odds` - Get detailed odds for a specific event by ID. Use after finding an event.
3. `get_sports_summary` - Get overview of available sports and event counts.
4. `refresh_odds` - Trigger a live scrape from Betfair for fresh data.
5. `get_data_freshness` - Check how current the database data is.
6. `web_search` - Search the web for team news, form, injuries, head-to-head stats.
7. `analyze_odds` - Execute Python code for statistical analysis and expected value calculations.

**IMPORTANT BEHAVIOR:**
- When asked about ANY event, FIRST use `query_events` to search for it
- When asked about odds, use `get_event_odds` with the event ID
- When asked for match intelligence or value bets, use MULTIPLE tools:
  1. First `query_events` to find the match
  2. Then `get_event_odds` for current odds
  3. Then `web_search` for team form, injuries, news
  4. Optionally `analyze_odds` to calculate expected value

- NEVER say "I don't have access to real-time data" - YOU DO, use the tools!
- NEVER provide generic advice without first using tools to get real data
- ALWAYS use tools before answering questions about specific matches

**Value Bet Analysis Framework:**
When analyzing value bets, use tools to gather:
- Current odds from database (get_event_odds)
- Recent form via web search
- Injury news via web search
- Head-to-head records via web search
Then calculate implied probability vs estimated true probability.

Promote responsible gambling. Never guarantee outcomes."""

        # Add context to system prompt if provided
        if context:
            system_prompt += f"\n\n**Current Context:**\n{json.dumps(context, indent=2)}"

        tool_calls = []
        max_iterations = 8  # Allow more iterations for comprehensive research

        for iteration in range(max_iterations):
            # Call Claude API with tools (including native web search)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=self.tools + [self.web_search_tool]
            )

            self.last_successful_call = datetime.utcnow().isoformat() + 'Z'

            # Check if we need to handle tool calls
            if response.stop_reason == "tool_use":
                # Extract assistant message with tool calls
                assistant_content = response.content
                messages.append({"role": "assistant", "content": assistant_content})

                # Process each tool call
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_id = block.id

                        # Native web_search is handled automatically by Claude API
                        # We only need to execute our custom tools
                        if tool_name == "web_search":
                            # Native web search - results come in response content
                            # Just log it for tracking
                            tool_calls.append({
                                "name": tool_name,
                                "input": tool_input,
                                "result": "(native web search - handled by Claude)"
                            })
                            continue  # Skip manual execution
                        elif tool_name == "analyze_odds":
                            result = self._execute_code(
                                tool_input.get("code", ""),
                                tool_input.get("description", "")
                            )
                        else:
                            result = execute_tool(tool_name, tool_input)

                        tool_calls.append({
                            "name": tool_name,
                            "input": tool_input,
                            "result": result[:1000] if len(result) > 1000 else result  # Truncate long results
                        })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": result
                        })

                # Add tool results to messages (if any custom tools were executed)
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})

            else:
                # No more tool calls, extract final response
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text

                return {
                    "response": final_text,
                    "model": self.model,
                    "response_source": "claude_api",
                    "tool_calls": tool_calls
                }

        # Max iterations reached - make a final synthesis call WITHOUT tools
        # This forces Claude to produce a text response summarizing what was found
        messages.append({
            "role": "user",
            "content": "You've gathered the data above. Now provide your final analysis and recommendations based on all the information collected. Do NOT call any more tools - just synthesize and present your findings."
        })

        final_response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages
            # No tools parameter = forces text response
        )

        final_text = ""
        for block in final_response.content:
            if hasattr(block, "text"):
                final_text += block.text

        return {
            "response": final_text,
            "model": self.model,
            "response_source": "claude_api",
            "tool_calls": tool_calls
        }

    def _execute_code(self, code: str, description: str = "") -> str:
        """
        Execute Python code for odds analysis.
        Limited to mathematical/statistical operations for safety.
        """
        # Safety: only allow math-related operations
        forbidden = ['import os', 'import sys', 'subprocess', 'exec(', 'eval(',
                     'open(', '__import__', 'file', 'input(', 'raw_input']

        for f in forbidden:
            if f in code.lower():
                return f"Code execution blocked: {f} is not allowed for security reasons."

        try:
            # Create a restricted namespace
            import math
            safe_namespace = {
                'math': math,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'len': len,
                'range': range,
                'list': list,
                'dict': dict,
                'float': float,
                'int': int,
                'str': str,
                'print': print,
            }

            # Capture output
            from io import StringIO
            import sys

            old_stdout = sys.stdout
            sys.stdout = StringIO()

            # Execute
            exec(code, safe_namespace)

            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            result = f"**Analysis: {description}**\n\n" if description else "**Code Analysis Result:**\n\n"
            result += f"```python\n{code}\n```\n\n"
            result += f"**Output:**\n{output if output else 'Code executed successfully (no output)'}"

            return result

        except Exception as e:
            return f"Code execution error: {str(e)}"

    def get_status(self) -> dict:
        """
        Check Claude API connection status.

        Returns:
            dict with:
                - status: 'connected' or 'error'
                - model: Model ID if connected
                - api_key_present: Boolean
                - last_successful_call: ISO timestamp or None
                - tools_available: List of available tool names
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
                "last_successful_call": self.last_successful_call,
                "tools_available": [t["name"] for t in self.tools]
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
