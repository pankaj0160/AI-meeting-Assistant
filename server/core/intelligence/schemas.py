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



class SpeakerSentiment(BaseModel):
    """
    Sentiment analysis for ONE speaker in the meeting.
 
    speaker        : the label from diarization e.g. "SPEAKER_00"
                     OR a name if the transcript uses real names
    sentiment      : overall tone — "positive", "neutral", or "negative"
    confidence     : how certain the model is, 0.0 to 1.0
    dominant_emotion: the strongest single emotion detected
                     e.g. "enthusiastic", "concerned", "frustrated", "calm"
    key_phrases    : up to 3 short quotes that best represent this speaker's tone
    """
    speaker:          str            = Field(description="Speaker label, e.g. SPEAKER_00")
    sentiment:        str            = Field(description="positive / neutral / negative")
    confidence:       float          = Field(description="Confidence score 0.0 to 1.0", ge=0.0, le=1.0)
    dominant_emotion: str            = Field(description="The strongest emotion: enthusiastic, concerned, frustrated, calm, etc.")
    key_phrases:      list[str]      = Field(default_factory=list, description="Up to 3 short quotes showing this sentiment")
 
 
class SpeakerSentimentList(BaseModel):
    """
    Instructor wrapper — lets us extract a list of SpeakerSentiment objects.
    Same pattern as ActionItemList, DecisionList, TopicList.
    """
    speakers: list[SpeakerSentiment] = Field(
        default_factory=list,
        description="Sentiment analysis for each speaker in the meeting"
    )
 
 
class MeetingSentimentSummary(BaseModel):
    """
    The full sentiment report for a meeting — stored in the database.
 
    overall_sentiment  : the meeting's overall tone
    meeting_energy     : how engaged/energetic the meeting felt overall
    tension_detected   : True if conflict or frustration was detected
    sentiment_shift    : did the mood change during the meeting?
                         e.g. "Started tense, ended positively after the budget decision"
    speakers           : per-speaker breakdown (list of SpeakerSentiment)
    """
    overall_sentiment : str                   = Field(description="positive / neutral / negative")
    meeting_energy    : str                   = Field(description="high / medium / low")
    tension_detected  : bool                  = Field(description="True if any conflict or frustration was detected")
    sentiment_shift   : Optional[str]         = Field(default=None, description="Description of mood change if any")
    speakers          : list[SpeakerSentiment] = Field(default_factory=list)
 