import pytest
from app.models.memory import MemoryItem
from app.services.memory_service import MemoryService
from app.utils.text_normalizer import (
    normalize_transcript_text,
    get_normalized_terms_found,
)


def test_normalize_transcript_text_quadrant_to_qdrant():
    raw = "Remember that my agent memory AI project uses Quadrant for persistent memory."
    normalized = normalize_transcript_text(raw)
    assert "Qdrant" in normalized
    assert "Quadrant" not in normalized
    assert normalized == "Remember that my agent memory AI project uses Qdrant for persistent memory."


def test_normalize_transcript_text_lyzer_to_lyzr():
    raw = "On Lyzer for agent orchestration, I need to finish React dashboard today."
    normalized = normalize_transcript_text(raw)
    assert "Lyzr" in normalized
    assert "Lyzer" not in normalized
    assert normalized == "On Lyzr for agent orchestration, I need to finish React dashboard today."


def test_normalize_transcript_text_combined_and_case_insensitive():
    raw = "Quadrant and lyzer are used together with LyZer and quadrant."
    normalized = normalize_transcript_text(raw)
    assert "Qdrant and Lyzr are used together with Lyzr and Qdrant." == normalized


def test_normalize_terms_found_extraction():
    raw = "We use Quadrant and Lyzer."
    found = get_normalized_terms_found(raw)
    assert found == {"Quadrant": "Qdrant", "Lyzer": "Lyzr"}


def test_preserves_unrelated_text_without_inferring():
    raw = "We had lunch at 12:30 and discussed normal quarterly numbers in the fourth quadrant of the building."
    # The word quadrant is normalized to Qdrant based on rule, but non-matching text is preserved exactly
    raw_clean = "We discussed the weather and coffee."
    normalized = normalize_transcript_text(raw_clean)
    assert normalized == raw_clean
    assert get_normalized_terms_found(raw_clean) == {}


def test_memory_item_preserves_original_content_and_sets_display_text():
    original_text = "SPEAKER_0: Remember that my agent memory AI project uses Quadrant for persistent memory."
    item = MemoryItem(
        id="test-1",
        uid="user-1",
        content=original_text,
    )

    # 1. Original content is strictly preserved exactly as received
    assert item.content == original_text
    assert "Quadrant" in item.content

    # 2. display_text is populated with normalized product name
    assert item.display_text is not None
    assert "Qdrant" in item.display_text
    assert item.display_text == "SPEAKER_0: Remember that my agent memory AI project uses Qdrant for persistent memory."


def test_memory_service_format_memories_distinguishes_original_from_normalized():
    service = MemoryService()
    memories = [
        MemoryItem(
            id="mem-1",
            uid="user-1",
            content="Alex said we use Quadrant and Lyzer.",
            metadata={"speaker": "Alex", "source": "omi_voice"},
        )
    ]

    context = service.format_memories_for_prompt(memories)
    # Must contain both original spoken transcript and normalized reference
    assert "Original Spoken Transcript: Alex said we use Quadrant and Lyzer." in context
    assert "Normalized Product Reference: Alex said we use Qdrant and Lyzr." in context
