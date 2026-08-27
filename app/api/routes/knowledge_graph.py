from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CurrentProfile, DatabaseSession, FusekiConnection
from app.api.routes.cards import get_card_or_404
from app.schemas.knowledge_graph import KnowledgeGraphRead
from app.services.fuseki import FusekiQueryError
from app.services.knowledge_graph import (
    KnowledgeGraphResultError,
    load_card_knowledge_graph,
)

router = APIRouter(tags=["knowledge-graph"])


@router.get(
    "/cards/{card_id}/knowledge-graph",
    response_model=KnowledgeGraphRead,
)
def read_card_knowledge_graph(
    card_id: int,
    db: DatabaseSession,
    profile: CurrentProfile,
    fuseki: FusekiConnection,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> KnowledgeGraphRead:
    card = get_card_or_404(card_id, db, profile.id)
    try:
        return load_card_knowledge_graph(
            fuseki,
            card_id=card.id,
            card_title=card.title,
            limit=limit,
        )
    except FusekiQueryError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="지식 그래프 저장소에 연결할 수 없습니다.",
        ) from error
    except KnowledgeGraphResultError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="지식 그래프 조회 결과를 해석할 수 없습니다.",
        ) from error
