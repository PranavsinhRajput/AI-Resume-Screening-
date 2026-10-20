from fastapi import APIRouter, Depends
from supabase import Client

from app.config import Settings, get_settings
from app.deps import get_access, get_embedder, get_llm, get_supabase
from app.errors import AppError
from app.schemas.search import SearchRequest, SearchResponse
from app.services.access import AccessContext
from app.services.embeddings import Embedder
from app.services.llm import LLMGateway
from app.services.rate_limit import get_search_limiter
from app.services.search import run_search

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    access: AccessContext = Depends(get_access),
    client: Client = Depends(get_supabase),
    settings: Settings = Depends(get_settings),
    llm: LLMGateway = Depends(get_llm),
    embedder: Embedder = Depends(get_embedder),
) -> SearchResponse:
    # Rate limit counts against the person searching (an admin viewing a user spends their own quota).
    get_search_limiter(settings.SEARCH_RATE_LIMIT_PER_MIN).check(access.actor.id)
    top_k = body.top_k or settings.SEARCH_DEFAULT_TOP_K
    if top_k > settings.SEARCH_MAX_TOP_K:
        raise AppError(422, "validation_error", f"top_k must be at most {settings.SEARCH_MAX_TOP_K}.")
    return await run_search(
        owner_id=access.owner_id,
        query=body.query,
        top_k=top_k,
        client=client,
        settings=settings,
        llm=llm,
        embedder=embedder,
    )
