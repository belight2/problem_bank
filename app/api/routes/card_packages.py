from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentProfile, DatabaseSession
from app.models.card import Card
from app.models.concept import (
    CardConcept,
    Concept,
    ConceptRelation,
    ConceptRelationType,
    NoteConcept,
    ProblemConcept,
    ProblemConceptRole,
)
from app.models.note import Note
from app.models.problem import Problem
from app.models.topic import Topic
from app.schemas.card import CardRead
from app.schemas.card_package import (
    CardPackage,
    CardPackageCard,
    CardPackageConcept,
    CardPackageConceptRelation,
    CardPackageImportRead,
    CardPackageNote,
    CardPackagePreview,
    CardPackageProblem,
    CardPackageSummary,
    CardPackageTopic,
)
from app.services.concepts import concept_name_key
from app.services.graph_outbox import (
    enqueue_card_event,
    enqueue_concept_event,
    enqueue_note_event,
    enqueue_problem_event,
    enqueue_topic_event,
)

router = APIRouter(tags=["card-packages"])

SYMMETRIC_RELATIONS = {
    ConceptRelationType.RELATED.value,
    ConceptRelationType.CONTRASTS.value,
    ConceptRelationType.CONFUSED_WITH.value,
}


def package_summary(package: CardPackage) -> CardPackageSummary:
    return CardPackageSummary(
        topic_count=len(package.topics),
        concept_count=len(package.concepts),
        concept_relation_count=len(package.concept_relations),
        note_count=len(package.notes),
        problem_count=len(package.problems),
    )


def existing_concepts_by_key(
    package: CardPackage,
    profile_id: int,
    db: DatabaseSession,
) -> dict[str, Concept]:
    name_keys = {concept_name_key(concept.name) for concept in package.concepts}
    if not name_keys:
        return {}
    concepts = db.scalars(
        select(Concept).where(
            Concept.profile_id == profile_id,
            Concept.name_key.in_(name_keys),
        )
    ).all()
    return {concept.name_key: concept for concept in concepts}


def preview_package(
    package: CardPackage,
    profile_id: int,
    db: DatabaseSession,
) -> CardPackagePreview:
    existing = existing_concepts_by_key(package, profile_id, db)
    reused_count = sum(concept_name_key(concept.name) in existing for concept in package.concepts)
    return CardPackagePreview(
        format_version=package.format_version,
        title=package.card.title,
        summary=package_summary(package),
        reused_concept_count=reused_count,
        new_concept_count=len(package.concepts) - reused_count,
    )


@router.get("/cards/{card_id}/package", response_model=CardPackage)
def export_card_package(
    card_id: int,
    profile: CurrentProfile,
    db: DatabaseSession,
) -> CardPackage:
    card = db.scalar(
        select(Card)
        .options(
            selectinload(Card.topics),
            selectinload(Card.concept_links).selectinload(CardConcept.concept),
            selectinload(Card.notes).selectinload(Note.concept_links),
            selectinload(Card.problems).selectinload(Problem.concept_links),
        )
        .where(Card.id == card_id, Card.profile_id == profile.id)
    )
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")

    topics = sorted(card.topics, key=lambda topic: topic.id)
    concepts = sorted(
        (link.concept for link in card.concept_links),
        key=lambda concept: concept.id,
    )
    notes = sorted(card.notes, key=lambda note: note.id)
    problems = sorted(card.problems, key=lambda problem: problem.id)
    topic_refs = {topic.id: f"topic:{topic.id}" for topic in topics}
    concept_refs = {concept.id: f"concept:{concept.id}" for concept in concepts}
    note_refs = {note.id: f"note:{note.id}" for note in notes}
    concept_ids = set(concept_refs)
    relations = (
        db.scalars(
            select(ConceptRelation)
            .where(
                ConceptRelation.source_concept_id.in_(concept_ids),
                ConceptRelation.target_concept_id.in_(concept_ids),
            )
            .order_by(ConceptRelation.id)
        ).all()
        if concept_ids
        else []
    )

    return CardPackage(
        exported_at=datetime.now(UTC),
        card=CardPackageCard(title=card.title, description=card.description),
        topics=[CardPackageTopic(ref=topic_refs[topic.id], name=topic.name) for topic in topics],
        concepts=[
            CardPackageConcept(
                ref=concept_refs[concept.id],
                name=concept.name,
                description=concept.description,
            )
            for concept in concepts
        ],
        concept_relations=[
            CardPackageConceptRelation(
                source_concept_ref=concept_refs[relation.source_concept_id],
                target_concept_ref=concept_refs[relation.target_concept_id],
                relation_type=relation.relation_type,
            )
            for relation in relations
        ],
        notes=[
            CardPackageNote(
                ref=note_refs[note.id],
                topic_ref=topic_refs.get(note.topic_id),
                title=note.title,
                content_markdown=note.content_markdown,
                concept_refs=[
                    concept_refs[link.concept_id]
                    for link in sorted(note.concept_links, key=lambda link: link.concept_id)
                ],
            )
            for note in notes
        ],
        problems=[
            CardPackageProblem(
                topic_ref=topic_refs[problem.topic_id],
                question=problem.question,
                problem_type=problem.problem_type,
                choices=problem.choices,
                answer=problem.answer,
                source_note_ref=note_refs.get(problem.source_note_id),
                primary_concept_ref=concept_refs.get(problem.primary_concept_id),
                supporting_concept_refs=[
                    concept_refs[concept_id]
                    for concept_id in sorted(problem.supporting_concept_ids)
                ],
            )
            for problem in problems
        ],
    )


@router.post("/card-packages/preview", response_model=CardPackagePreview)
def preview_card_package(
    package: CardPackage,
    profile: CurrentProfile,
    db: DatabaseSession,
) -> CardPackagePreview:
    return preview_package(package, profile.id, db)


@router.post(
    "/card-packages/import",
    response_model=CardPackageImportRead,
    status_code=status.HTTP_201_CREATED,
)
def import_card_package(
    package: CardPackage,
    profile: CurrentProfile,
    db: DatabaseSession,
) -> CardPackageImportRead:
    preview = preview_package(package, profile.id, db)
    existing_concepts = existing_concepts_by_key(package, profile.id, db)

    try:
        card = Card(
            profile=profile,
            title=package.card.title,
            description=package.card.description,
        )
        db.add(card)
        db.flush()

        topics_by_ref: dict[str, Topic] = {}
        for package_topic in package.topics:
            topic = Topic(card=card, name=package_topic.name)
            db.add(topic)
            topics_by_ref[package_topic.ref] = topic
        db.flush()

        concepts_by_ref: dict[str, Concept] = {}
        for package_concept in package.concepts:
            name_key = concept_name_key(package_concept.name)
            concept = existing_concepts.get(name_key)
            if concept is None:
                concept = Concept(
                    profile=profile,
                    name=package_concept.name,
                    name_key=name_key,
                    description=package_concept.description,
                )
                db.add(concept)
                existing_concepts[name_key] = concept
            card.concept_links.append(CardConcept(concept=concept))
            concepts_by_ref[package_concept.ref] = concept
        db.flush()

        existing_relation_keys = (
            set(
                db.execute(
                    select(
                        ConceptRelation.source_concept_id,
                        ConceptRelation.target_concept_id,
                        ConceptRelation.relation_type,
                    ).where(
                        ConceptRelation.source_concept_id.in_(
                            [concept.id for concept in concepts_by_ref.values()]
                        ),
                        ConceptRelation.target_concept_id.in_(
                            [concept.id for concept in concepts_by_ref.values()]
                        ),
                    )
                ).all()
            )
            if concepts_by_ref
            else set()
        )
        for package_relation in package.concept_relations:
            source = concepts_by_ref[package_relation.source_concept_ref]
            target = concepts_by_ref[package_relation.target_concept_ref]
            relation_type = package_relation.relation_type.value
            if relation_type in SYMMETRIC_RELATIONS and source.id > target.id:
                source, target = target, source
            relation_key = (source.id, target.id, relation_type)
            if relation_key in existing_relation_keys:
                continue
            db.add(
                ConceptRelation(
                    source_concept=source,
                    target_concept=target,
                    relation_type=relation_type,
                )
            )
            existing_relation_keys.add(relation_key)
        db.flush()

        notes_by_ref: dict[str, Note] = {}
        for package_note in package.notes:
            note = Note(
                card=card,
                topic=(
                    topics_by_ref[package_note.topic_ref]
                    if package_note.topic_ref is not None
                    else None
                ),
                title=package_note.title,
                content_markdown=package_note.content_markdown,
            )
            note.concept_links = [
                NoteConcept(concept_id=concepts_by_ref[concept_ref].id)
                for concept_ref in package_note.concept_refs
            ]
            db.add(note)
            notes_by_ref[package_note.ref] = note
        db.flush()

        imported_problems: list[Problem] = []
        for package_problem in package.problems:
            problem = Problem(
                card=card,
                topic=topics_by_ref[package_problem.topic_ref],
                question=package_problem.question,
                problem_type=package_problem.problem_type.value,
                choices=package_problem.choices,
                answer=package_problem.answer,
                source_note=(
                    notes_by_ref[package_problem.source_note_ref]
                    if package_problem.source_note_ref is not None
                    else None
                ),
            )
            if package_problem.primary_concept_ref is not None:
                problem.concept_links.append(
                    ProblemConcept(
                        concept_id=concepts_by_ref[package_problem.primary_concept_ref].id,
                        role=ProblemConceptRole.PRIMARY.value,
                    )
                )
            problem.concept_links.extend(
                ProblemConcept(
                    concept_id=concepts_by_ref[concept_ref].id,
                    role=ProblemConceptRole.SUPPORTING.value,
                )
                for concept_ref in package_problem.supporting_concept_refs
            )
            db.add(problem)
            imported_problems.append(problem)
        db.flush()

        enqueue_card_event(db, card)
        for topic in topics_by_ref.values():
            enqueue_topic_event(db, topic)
        for concept in set(concepts_by_ref.values()):
            enqueue_concept_event(db, concept)
        for note in notes_by_ref.values():
            enqueue_note_event(db, note)
        for problem in imported_problems:
            enqueue_problem_event(db, problem)
        db.commit()
        db.refresh(card)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="카드 내용을 가져오는 중 중복 데이터가 발견되었습니다.",
        ) from error

    return CardPackageImportRead(
        card=CardRead.model_validate(card),
        summary=preview.summary,
        reused_concept_count=preview.reused_concept_count,
        new_concept_count=preview.new_concept_count,
    )
