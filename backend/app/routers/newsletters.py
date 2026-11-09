from fastapi import APIRouter, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.deps import CurrentUser, DB
from app.models import (
    Group,
    NewsletterMessage,
    NewsletterThread,
    Role,
    User,
    group_members,
)
from app.schemas import (
    GroupBrief,
    NewsletterCreate,
    NewsletterRecipient,
    NewsletterReply,
    NewsletterThreadOut,
    UserBrief,
)
from app.timeutil import now_utc

router = APIRouter(prefix="/newsletters", tags=["newsletters"])


def accessible_threads(user: User):
    direct = or_(
        NewsletterThread.created_by == user.id,
        NewsletterThread.recipient_user_id == user.id,
    )
    if user.role == Role.admin:
        # Professors participate in all group newsletters but only their own direct conversations.
        return or_(direct, NewsletterThread.group_id.is_not(None))
    member_groups = select(group_members.c.group_id).where(group_members.c.user_id == user.id)
    return or_(direct, NewsletterThread.group_id.in_(member_groups))


def load_thread(db, thread_id: int, user: User) -> NewsletterThread:
    thread = db.scalar(
        select(NewsletterThread)
        .where(NewsletterThread.id == thread_id, accessible_threads(user))
        .options(
            selectinload(NewsletterThread.creator),
            selectinload(NewsletterThread.recipient),
            selectinload(NewsletterThread.group),
            selectinload(NewsletterThread.messages).selectinload(NewsletterMessage.author),
        )
    )
    if thread is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Newsletter not found")
    return thread


@router.get("/recipients", response_model=NewsletterRecipient)
def recipients(user: CurrentUser, db: DB):
    if user.role == Role.admin:
        people = db.scalars(
            select(User).where(User.is_active.is_(True), User.id != user.id).order_by(User.full_name)
        ).all()
        groups = db.scalars(select(Group).order_by(Group.name)).all()
    else:
        people = db.scalars(
            select(User).where(User.is_active.is_(True), User.role == Role.admin).order_by(User.full_name)
        ).all()
        groups = db.scalars(
            select(Group).join(group_members).where(group_members.c.user_id == user.id).order_by(Group.name)
        ).all()
    return NewsletterRecipient(
        users=[UserBrief.model_validate(person) for person in people],
        groups=[GroupBrief.model_validate(group) for group in groups],
    )


@router.get("", response_model=list[NewsletterThreadOut])
def list_newsletters(user: CurrentUser, db: DB):
    return db.scalars(
        select(NewsletterThread)
        .where(accessible_threads(user))
        .options(
            selectinload(NewsletterThread.creator),
            selectinload(NewsletterThread.recipient),
            selectinload(NewsletterThread.group),
            selectinload(NewsletterThread.messages).selectinload(NewsletterMessage.author),
        )
        .order_by(NewsletterThread.updated_at.desc(), NewsletterThread.id.desc())
    ).all()


@router.get("/{thread_id}", response_model=NewsletterThreadOut)
def get_newsletter(thread_id: int, user: CurrentUser, db: DB):
    return load_thread(db, thread_id, user)


@router.post("", response_model=NewsletterThreadOut, status_code=201)
def create_newsletter(body: NewsletterCreate, user: CurrentUser, db: DB):
    recipient = db.get(User, body.recipient_user_id) if body.recipient_user_id else None
    group = db.get(Group, body.group_id) if body.group_id else None
    if recipient is not None:
        if not recipient.is_active or recipient.id == user.id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid recipient")
        if user.role != Role.admin and recipient.role != Role.admin:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Students can start direct newsletters with professors")
    elif body.recipient_user_id is not None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown recipient")
    if group is not None and user.role != Role.admin:
        member = db.scalar(
            select(group_members.c.user_id).where(
                group_members.c.group_id == group.id, group_members.c.user_id == user.id
            )
        )
        if member is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not a member of this group")
    elif body.group_id is not None and group is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown group")

    thread = NewsletterThread(
        subject=body.subject.strip(), created_by=user.id,
        recipient_user_id=body.recipient_user_id, group_id=body.group_id,
    )
    db.add(thread)
    db.flush()
    db.add(NewsletterMessage(thread_id=thread.id, author_id=user.id, body=body.body.strip()))
    db.commit()
    return load_thread(db, thread.id, user)


@router.post("/{thread_id}/messages", response_model=NewsletterThreadOut, status_code=201)
def reply(thread_id: int, body: NewsletterReply, user: CurrentUser, db: DB):
    thread = load_thread(db, thread_id, user)
    thread.updated_at = now_utc()
    db.add(NewsletterMessage(thread_id=thread.id, author_id=user.id, body=body.body.strip()))
    db.commit()
    # The access check loaded the relationship before the new row existed; discard that cached collection.
    db.expire(thread, ["messages"])
    return load_thread(db, thread.id, user)
