"""Minimal agent example: one LLM + one tool + a loop.

Install: pip install openai
Set:    OPENAI_API_KEY=...
Run:    python agent_minimal.py
"""

import json

from openai import OpenAI


client = OpenAI()


# 1. A real tool and the JSON schema the LLM can see.
def add(a: int, b: int) -> int:
    return a + b


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two integers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
        },
    }
]

TOOL_IMPLS = {"add": add}


def run_tool(name: str, args: dict):
    if name not in TOOL_IMPLS:
        raise ValueError(f"unknown tool: {name}")
    return TOOL_IMPLS[name](**args)


# 2. The agent loop: ask LLM, execute tool calls, send results back.
def agent(question: str, max_steps: int = 5) -> str:
    messages = [
        {
            "role": "system",
            "content": "You are a helpful agent. Use tools when needed, then answer concisely.",
        },
        {"role": "user", "content": question},
    ]

    for _ in range(max_steps):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOL_SCHEMAS,
        )
        message = response.choices[0].message
        messages.append(message)  # keep the assistant reply in history

        if not message.tool_calls:  # plain text: the final answer
            return message.content

        for call in message.tool_calls:  # tool result goes back into history
            args = json.loads(call.function.arguments)
            result = run_tool(call.function.name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    raise RuntimeError(f"reached max_steps={max_steps}")


if __name__ == "__main__":
    print(agent("What is 12345 + 67890?"))
