from app.db.session import SessionLocal
from app.services.graph_backfill import enqueue_graph_backfill


def main() -> None:
    with SessionLocal() as db:
        result = enqueue_graph_backfill(db)
        db.commit()

    print(
        "그래프 소급 적재 이벤트 생성 완료: "
        f"개념 {result.concepts}, 카드 {result.cards}, 주제 {result.topics}, "
        f"노트 {result.notes}, "
        f"문제 {result.problems}, 전체 {result.total}"
    )


if __name__ == "__main__":
    main()
