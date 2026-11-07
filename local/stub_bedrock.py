"""A scripted stand-in for the Bedrock client, so the planner works offline and free.

It follows the same three steps as a real model: read the open tasks, create a plan, then
summarize. Its plan is deliberately generic. It proves the loop works, not that it plans well.
"""

from datetime import timedelta

from shared.timeutil import today_ist


def _prompt_text(messages: list[dict]) -> str:
    return messages[0]["content"][0]["text"]


def _tool_rounds(messages: list[dict]) -> int:
    return sum(1 for m in messages if m["role"] == "user" and "toolResult" in m["content"][0])


def _tool_use(tool_id: str, name: str, tool_input: dict) -> dict:
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"toolUse": {"toolUseId": tool_id, "name": name, "input": tool_input}}],
            }
        },
        "stopReason": "tool_use",
    }


class StubBedrock:
    def converse(self, **kwargs) -> dict:
        messages = kwargs["messages"]
        rounds = _tool_rounds(messages)
        if rounds == 0:
            return _tool_use("stub-1", "get_open_tasks", {})
        if rounds == 1:
            return _tool_use("stub-2", "create_tasks", {"tasks": self._plan(_prompt_text(messages))})
        text = (
            "Stub planner: I split your request into three sessions over the next three days. "
            "Set PLANNER_MODE=bedrock to use a real model."
        )
        return {"output": {"message": {"role": "assistant", "content": [{"text": text}]}}, "stopReason": "end_turn"}

    @staticmethod
    def _plan(prompt: str) -> list[dict]:
        topic = " ".join(prompt.split())[:90]
        today = today_ist()
        steps = [("Start", "high", 60), ("Practice", "medium", 45), ("Review", "low", 30)]
        return [
            {
                "title": f"{label}: {topic}",
                "dueDate": (today + timedelta(days=offset)).isoformat(),
                "priority": priority,
                "estMinutes": minutes,
            }
            for offset, (label, priority, minutes) in enumerate(steps, start=1)
        ]
