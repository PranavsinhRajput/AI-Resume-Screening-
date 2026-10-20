"""Resume text → ResumeExtraction via the LLM gateway."""

from app.prompts.extraction import EXTRACTION_SYSTEM, extraction_user
from app.schemas.extraction import ResumeExtraction, ResumeExtractionGemini
from app.services.llm import LLMGateway


async def extract_resume(llm: LLMGateway, text: str) -> ResumeExtraction:
    """Raises LLMUnavailable or LLMInvalidOutput; callers map them to user-facing failures."""
    return await llm.generate_json(
        EXTRACTION_SYSTEM,
        extraction_user(text),
        ResumeExtraction,
        response_schema=ResumeExtractionGemini,
    )
