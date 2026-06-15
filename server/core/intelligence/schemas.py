from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ActionItem(BaseModel):
    task: str = Field(description="The specific task to be completed")
    owner: Optional[str] = Field(default=None, description="Person responsible")
    deadline: Optional[str] = Field(default=None, description="Due date or timeframe")
    priority: Optional[str] = Field(default="medium", description="high / medium / low")


class Decision(BaseModel):
    decision: str = Field(description="The decision that was made")
    rationale: Optional[str] = Field(default=None, description="Why this decision was made")


class Topic(BaseModel):
    title: str = Field(description="Short topic title, 3-5 words")
    description: Optional[str] = Field(default=None, description="One sentence explanation")


class MeetingIntelligence(BaseModel):
    summary: str = Field(description="Executive summary of the meeting")
    action_items: list[ActionItem] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    topics: list[Topic] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())



# ── Instructor list wrappers ──────────────────────────────────────────────────
# Instructor needs a top-level model to extract into.
# These wrap list fields so we can extract multiple items at once.

class ActionItemList(BaseModel):
    items: list[ActionItem] = Field(
        default_factory=list,
        description="All action items extracted from the transcript"
    )

class DecisionList(BaseModel):
    items: list[Decision] = Field(
        default_factory=list,
        description="All decisions extracted from the transcript"
    )

class TopicList(BaseModel):
    items: list[Topic] = Field(
        default_factory=list,
        description="All topics discussed in the transcript"
    )