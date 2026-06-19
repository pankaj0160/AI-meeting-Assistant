# server/core/agent/meeting_agent.py
#
# WHAT IS A ReAct AGENT?
# ──────────────────────
# ReAct = Reason + Act. It's a loop:
#
#   1. THINK: The LLM reads the question and decides what to do
#   2. ACT:   The LLM calls a tool (or says "I'm done")
#   3. OBSERVE: Your code runs the tool and sends the result back to the LLM
#   4. REPEAT: The LLM reads the result and decides what to do next
#   5. STOP: When the LLM produces a final answer instead of a tool call
#
# Visualized:
#
#   User question
#       ↓
#   [LLM] "I need to look up the action items"
#       ↓  tool_call: get_action_items()
#   [Your code] runs get_action_items(meeting_id=5)
#       ↓  result: "Found 3 action items..."
#   [LLM] "I also need the decisions"
#       ↓  tool_call: get_decisions()
#   [Your code] runs get_decisions(meeting_id=5)
#       ↓  result: "Found 2 decisions..."
#   [LLM] "I have enough info now"
#       ↓  final answer (no tool_call this time)
#   "Based on the meeting, here are the action items: ..."
#
# The conversation history grows with each loop iteration.
# The LLM sees the FULL history — every tool call and every result —
# so it always has context for its next decision.
#
# MAX_ITERATIONS = 5 is a safety valve.
# Without it, a confused LLM could loop forever and burn your API quota.

import json
import os
import time
import logging

from groq import Groq
from dotenv import load_dotenv
from langfuse import Langfuse

from server.core.agent.tools import TOOL_DEFINITIONS, execute_tool

load_dotenv()

logger = logging.getLogger(__name__)

MODEL          = "llama-3.3-70b-versatile"
MAX_ITERATIONS = 5   # Safety limit — stop after this many tool calls even if not done

# ── Clients ──────────────────────────────────────────────────────────────────
# Same pattern as agents.py — one plain Groq client for this file.
_groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
_langfuse    = Langfuse()


# =============================================================================
# SYSTEM PROMPT
# =============================================================================
# The system prompt defines the agent's personality and rules.
# Key rules:
#   - Always use a tool before answering (don't guess)
#   - Multiple tools allowed in one session
#   - Be concise and professional

SYSTEM_PROMPT = """You are Summly, an expert AI meeting intelligence assistant.
You have access to tools that let you query a specific meeting's data.

Your job: answer the user's question accurately using the available tools.

Rules:
- ALWAYS use at least one tool before giving a final answer. Never guess.
- You may call multiple tools if needed to fully answer the question.
- When you have enough information, give a clear, concise answer.
- Be specific — include names, deadlines, numbers from the data.
- If a tool returns no data, say so honestly. Don't make things up.
- Keep answers professional but conversational.
- Do not mention which tools you used in your final answer."""


# =============================================================================
# AGENT LOOP
# =============================================================================

def run_agent(query: str, meeting_id: int) -> dict:
    """
    Run the ReAct agent loop to answer a question about a meeting.

    This is the main function. It:
      1. Initialises a conversation with the system prompt + user question
      2. Calls the LLM with the tool definitions
      3. If the LLM calls a tool → runs it, appends result, loops back to step 2
      4. If the LLM gives a final answer → returns it

    Args:
        query      : the user's question ("What were the action items?")
        meeting_id : which meeting to answer about

    Returns:
        {
            "answer":     str,           # The agent's final answer
            "tools_used": list[str],     # Which tools were called (for debugging/logging)
            "iterations": int,           # How many loop iterations it took
        }
    """
    start_time  = time.time()
    tools_used  = []
    iterations  = 0

    # ── Langfuse trace — wraps the entire agent session ──────────────────────
    # One trace per user question. Tool calls become child spans inside it.
    trace = _langfuse.trace(
        name="meeting_agent",
        input={"query": query, "meeting_id": meeting_id},
    )

    # ── Build the initial conversation ───────────────────────────────────────
    # messages is the full conversation history.
    # We start with: system prompt + user question.
    # Each loop iteration APPENDS to this list.
    # The LLM always sees the COMPLETE history — that's why it knows what
    # tools it already called and what results it got.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": query},
    ]

    # ── ReAct loop ────────────────────────────────────────────────────────────
    while iterations < MAX_ITERATIONS:
        iterations += 1
        logger.info(f"[Agent] Iteration {iterations} | meeting_id={meeting_id}")

        # ── Call the LLM ─────────────────────────────────────────────────────
        # We pass tools= so Groq knows what functions the LLM can call.
        # tool_choice="auto" lets the LLM decide whether to call a tool
        # or give a final answer. (Other options: "required" to force a call,
        # "none" to disable tools entirely.)
        generation = trace.generation(
            name=f"agent_step_{iterations}",
            model=MODEL,
            input=messages,
        )

        try:
            response = _groq_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=1024,
            )
        except Exception as e:
            logger.error(f"[Agent] LLM call failed: {e}")
            generation.end(output=f"ERROR: {e}", metadata={"error": True})
            trace.update(output={"error": str(e)})
            return {
                "answer":     f"I encountered an error processing your question: {str(e)}",
                "tools_used": tools_used,
                "iterations": iterations,
            }

        message = response.choices[0].message

        # ── Check: did the LLM call a tool? ──────────────────────────────────
        # If message.tool_calls is non-empty, the LLM wants to call one or more tools.
        # If message.tool_calls is empty/None, the LLM is giving its final answer.
        if message.tool_calls:
            generation.end(
                output=f"tool_calls: {[tc.function.name for tc in message.tool_calls]}",
                metadata={"iteration": iterations},
            )

            # Append the assistant's "I want to call this tool" message to history.
            # This is required by the Groq API — you must include the assistant
            # message before the tool result messages.
            messages.append({
                "role":       "assistant",
                "content":    message.content,   # usually None when calling tools
                "tool_calls": [
                    {
                        "id":       tc.id,
                        "type":     "function",
                        "function": {
                            "name":      tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            # ── Execute each tool call ────────────────────────────────────────
            # The LLM can request multiple tools in one response.
            # We run all of them and append all results before looping back.
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tools_used.append(tool_name)

                # Parse the arguments JSON string the LLM provided
                # The LLM sends arguments as a JSON string, e.g.: '{"query": "decisions"}'
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}

                logger.info(f"[Agent] Calling tool: {tool_name}({tool_args})")

                # ── Run the tool ──────────────────────────────────────────────
                # execute_tool() dispatches to the correct function in tools.py
                # and returns a plain string result.
                tool_span = trace.span(
                    name=f"tool_{tool_name}",
                    input={"args": tool_args, "meeting_id": meeting_id},
                )
                tool_result = execute_tool(
                    tool_name=tool_name,
                    tool_args=tool_args,
                    meeting_id=meeting_id,
                )
                tool_span.end(output=tool_result[:500])  # truncate for Langfuse

                logger.info(f"[Agent] Tool result ({len(tool_result)} chars): {tool_result[:100]}...")

                # Append the tool result to the conversation.
                # role="tool" is the special role for tool results.
                # tool_call_id must match the id from the tool_call above —
                # this is how Groq pairs results with requests.
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tool_call.id,
                    "content":      tool_result,
                })

            # Loop continues — LLM will read the tool results and decide what to do next

        else:
            # ── No tool call = final answer ───────────────────────────────────
            # message.content is the LLM's final response to the user.
            final_answer = (message.content or "").strip()
            elapsed = time.time() - start_time

            generation.end(
                output=final_answer,
                usage={
                    "input":  response.usage.prompt_tokens,
                    "output": response.usage.completion_tokens,
                    "total":  response.usage.total_tokens,
                },
                metadata={"latency_seconds": round(elapsed, 3)},
            )
            trace.update(output={
                "answer":     final_answer,
                "tools_used": tools_used,
                "iterations": iterations,
            })

            logger.info(f"[Agent] Done in {iterations} iterations. Tools used: {tools_used}")

            return {
                "answer":     final_answer,
                "tools_used": tools_used,
                "iterations": iterations,
            }

    # ── Safety: exceeded MAX_ITERATIONS without a final answer ───────────────
    # This shouldn't happen with well-written prompts, but if it does,
    # we return a graceful message instead of crashing.
    logger.warning(f"[Agent] Exceeded MAX_ITERATIONS={MAX_ITERATIONS}")
    trace.update(output={"error": "max_iterations_exceeded"})

    return {
        "answer":     "I was unable to fully answer your question within the allowed steps. Please try rephrasing.",
        "tools_used": tools_used,
        "iterations": iterations,
    }