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
        self.model = "claude-sonnet-4-20250514"  # Primary model
        self.last_successful_call = None

        # Extended tools including web search and code interpreter
        self.tools = TOOLS + [
            {
                "name": "web_search",
                "description": "Search the web for current information about teams, players, recent form, injuries, and other betting-relevant data. Use this to research match intelligence.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        }
                    },
                    "required": ["query"]
                }
            },
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
            # Call Claude API with tools
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages,
                tools=self.tools
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

                        # Execute the tool
                        if tool_name == "web_search":
                            result = self._web_search(tool_input.get("query", ""))
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

                # Add tool results to messages
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

    def _web_search(self, query: str) -> str:
        """
        Perform a web search using DuckDuckGo.
        Uses the duckduckgo_search library for real search results.
        """
        import time

        try:
            # Try using duckduckgo_search library first (best results)
            try:
                from duckduckgo_search import DDGS
                from duckduckgo_search.exceptions import DuckDuckGoSearchException

                # Add small delay to avoid rate limits
                time.sleep(0.5)

                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=5))

                if results:
                    result = f"**Web Search Results for: {query}**\n\n"
                    for i, r in enumerate(results, 1):
                        title = r.get('title', 'No title')
                        body = r.get('body', 'No description')
                        href = r.get('href', '')
                        result += f"{i}. **{title}**\n"
                        result += f"   {body[:300]}{'...' if len(body) > 300 else ''}\n"
                        if href:
                            result += f"   Source: {href}\n"
                        result += "\n"
                    return result

            except ImportError:
                pass  # Fall through to backup method
            except Exception as ddg_error:
                # Handle rate limiting or other DDG errors
                if "Ratelimit" in str(ddg_error):
                    # Wait and retry once
                    time.sleep(2)
                    try:
                        with DDGS() as ddgs:
                            results = list(ddgs.text(query, max_results=3))
                        if results:
                            result = f"**Web Search Results for: {query}**\n\n"
                            for i, r in enumerate(results, 1):
                                title = r.get('title', 'No title')
                                body = r.get('body', 'No description')
                                href = r.get('href', '')
                                result += f"{i}. **{title}**\n"
                                result += f"   {body[:300]}{'...' if len(body) > 300 else ''}\n"
                                if href:
                                    result += f"   Source: {href}\n"
                                result += "\n"
                            return result
                    except:
                        pass  # Fall through to backup method
                # For other errors, fall through to backup

            # Fallback: Try DuckDuckGo HTML search with scraping
            import requests
            from urllib.parse import quote_plus

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            # Use DuckDuckGo lite (simpler to parse)
            response = requests.get(
                f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}",
                headers=headers,
                timeout=15
            )

            if response.status_code == 200:
                # Basic HTML parsing for results
                import re
                text = response.text

                # Extract result snippets (simplified parsing)
                result_pattern = r'class="result-snippet"[^>]*>([^<]+)<'
                snippets = re.findall(result_pattern, text)

                # Extract result links and titles
                link_pattern = r'class="result-link"[^>]*href="([^"]+)"[^>]*>([^<]+)<'
                links = re.findall(link_pattern, text)

                if links or snippets:
                    result = f"**Web Search Results for: {query}**\n\n"
                    for i, (href, title) in enumerate(links[:5], 1):
                        snippet = snippets[i-1] if i <= len(snippets) else ""
                        result += f"{i}. **{title.strip()}**\n"
                        if snippet:
                            result += f"   {snippet.strip()[:200]}...\n"
                        result += f"   Source: {href}\n\n"
                    return result

            # Final fallback - provide useful guidance
            return f"""**Web Search Results for: {query}**

Unable to fetch live search results. Here's how to research this:

1. **Recent Form**: Check ESPN, BBC Sport, or FlashScore for recent match results
2. **Team News**: Look for injury reports on the team's official website or Twitter
3. **Head-to-Head**: Sites like SofaScore or FootyStats have historical matchup data
4. **Expert Analysis**: Check betting-focused sites like Oddschecker or Betfair's insights

For accurate value bet analysis, combine the odds data from this platform with your own research on team form and conditions."""

        except Exception as e:
            return f"""**Web Search Error**

Search failed: {str(e)}

For match research, manually check:
- ESPN.com for team form and news
- BBC Sport for injury updates
- FlashScore for head-to-head stats
- Twitter for real-time team news"""

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
