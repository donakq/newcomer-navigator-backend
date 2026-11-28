"""Postgres store (SQLAlchemy 2). Tables follow the OPT MVP v1 Data Spec §3 (U1, U3, U4, U5, U7).

Tables are created on first use (create_all). Once the schema needs to change on a live database,
add Alembic migrations instead.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, create_engine, delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.pool import StaticPool

from app.mock.opt_demo import policy_version
from app.opt.content import get_content
from app.schemas.opt import (AssistantFeedbackRequest, HistoryEntry, Offer, OptSelection, ProcessingChoice, Profile,
                             School, StageDates, TaskStatus)
from app.store.base import SESSION_DAYS, UserState, apply_restore, clear_for_reset, hash_token, new_token


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserRow(Base):  # U1
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    timezone: Mapped[str] = mapped_column(String(64))
    plan_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SessionRow(Base):  # U3: only the token hash is stored
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProfileRow(Base):  # U4
    __tablename__ = "user_profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    school_id: Mapped[str] = mapped_column(String(64))
    degree_level: Mapped[str] = mapped_column(String(16))
    program_end_date: Mapped[date] = mapped_column(Date)
    opt_intent: Mapped[str | None] = mapped_column(String(32))
    first_time_at_level: Mapped[bool | None] = mapped_column(Boolean)
    opt_type: Mapped[str | None] = mapped_column(String(32))
    stage: Mapped[str | None] = mapped_column(String(32))
    i20_request_date: Mapped[date | None] = mapped_column(Date)
    dso_rec_date: Mapped[date | None] = mapped_column(Date)
    i20_issue_date: Mapped[date | None] = mapped_column(Date)
    uscis_receipt_date: Mapped[date | None] = mapped_column(Date)
    requested_start_date: Mapped[date | None] = mapped_column(Date)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class OfferRow(Base):  # U5
    __tablename__ = "offer_info"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    has_offer: Mapped[bool] = mapped_column(Boolean)
    offer_start_date: Mapped[date | None] = mapped_column(Date)
    start_flexible: Mapped[str | None] = mapped_column(String(16))
    start_preference: Mapped[str | None] = mapped_column(String(16))
    preferred_start_date: Mapped[date | None] = mapped_column(Date)
    premium_intent: Mapped[str] = mapped_column(String(16))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class ProcessingRow(Base):  # student-picked processing times; its own table so create_all adds it to live DBs
    __tablename__ = "processing_choices"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    school_business_days: Mapped[int | None] = mapped_column(Integer)
    uscis_standard_days: Mapped[int | None] = mapped_column(Integer)
    uscis_premium_business_days: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class TaskRow(Base):  # U7: only the statuses the student set; dates are recomputed from the profile
    __tablename__ = "user_tasks"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    template_id: Mapped[str] = mapped_column(String(8), primary_key=True)
    status: Mapped[str] = mapped_column(String(32))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class HistoryRow(Base):  # a plan the student archived by starting over; snapshot = profile + task statuses
    __tablename__ = "user_history"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    plan_version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)


class FeedbackRow(Base):  # thumbs up / down on an assistant answer; no question or answer text is stored
    __tablename__ = "assistant_feedback"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64))
    rating: Mapped[str] = mapped_column(String(8))
    reasons: Mapped[list] = mapped_column(JSON)
    comment: Mapped[str | None] = mapped_column(String(500))
    intent: Mapped[str | None] = mapped_column(String(32))
    scope: Mapped[str | None] = mapped_column(String(32))
    current_page: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


PROFILE_DATE_FIELDS = tuple(StageDates.model_fields)
PROCESSING_FIELDS = tuple(ProcessingChoice.model_fields)
OFFER_FIELDS = ("has_offer", "offer_start_date", "start_flexible", "start_preference", "preferred_start_date",
                "premium_intent")


def make_engine(url: str) -> Engine:
    """Accepts Neon / Vercel style URLs (postgres://...) and uses the psycopg 3 driver."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("sqlite") and ":memory:" in url:
        return create_engine(url, poolclass=StaticPool, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True, pool_size=2, max_overflow=3)


class SqlStore:
    def __init__(self, url: str) -> None:
        self.engine = make_engine(url)
        Base.metadata.create_all(self.engine)

    # --- sessions ---

    def login(self, email: str, timezone: str) -> tuple[str, bool]:
        email = email.strip().lower()
        token = new_token()
        with Session(self.engine) as db, db.begin():
            user = db.scalar(select(UserRow).where(UserRow.email == email))
            is_new = user is None
            if user is None:
                user = UserRow(id=str(uuid.uuid4()), email=email, timezone=timezone, plan_version=1)
                db.add(user)
                db.flush()
            db.add(SessionRow(token_hash=hash_token(token), user_id=user.id,
                              expires_at=_now() + timedelta(days=SESSION_DAYS)))
        return token, is_new

    def _user_id(self, db: Session, token: str) -> str | None:
        row = db.get(SessionRow, hash_token(token))
        if row is None:
            return None
        expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)
        return row.user_id if expires > _now() else None

    def logout(self, token: str) -> None:
        with Session(self.engine) as db, db.begin():
            db.execute(delete(SessionRow).where(SessionRow.token_hash == hash_token(token)))

    def delete_user(self, token: str) -> None:
        with Session(self.engine) as db, db.begin():
            user_id = self._user_id(db, token)
            if user_id:
                for table in (FeedbackRow, HistoryRow, TaskRow, ProcessingRow, OfferRow, ProfileRow, SessionRow):
                    db.execute(delete(table).where(table.user_id == user_id))
                db.execute(delete(UserRow).where(UserRow.id == user_id))

    # --- user state ---

    def state_for(self, token: str) -> UserState | None:
        with Session(self.engine) as db:
            user_id = self._user_id(db, token)
            user = db.get(UserRow, user_id) if user_id else None
            if user is None:
                return None
            profile_row = db.get(ProfileRow, user.id)
            offer_row = db.get(OfferRow, user.id)
            processing_row = db.get(ProcessingRow, user.id)
            tasks = db.scalars(select(TaskRow).where(TaskRow.user_id == user.id)).all()
            return UserState(
                user_id=user.id,
                email=user.email,
                timezone=user.timezone,
                profile=_to_profile(user, profile_row, offer_row, processing_row) if profile_row else None,
                task_statuses={t.template_id: TaskStatus(t.status) for t in tasks},
                plan_version=user.plan_version,
            )

    def save(self, state: UserState) -> None:
        with Session(self.engine) as db, db.begin():
            self._save(db, state)

    def _save(self, db: Session, state: UserState) -> None:
        user = db.get(UserRow, state.user_id)
        if user is None:
            return  # deleted meanwhile
        user.timezone = state.timezone
        user.plan_version = state.plan_version
        db.execute(delete(TaskRow).where(TaskRow.user_id == state.user_id))
        db.add_all(TaskRow(user_id=state.user_id, template_id=t, status=s.value)
                   for t, s in state.task_statuses.items())
        p = state.profile
        if p is None:
            db.execute(delete(ProcessingRow).where(ProcessingRow.user_id == state.user_id))
            db.execute(delete(OfferRow).where(OfferRow.user_id == state.user_id))
            db.execute(delete(ProfileRow).where(ProfileRow.user_id == state.user_id))
            return
        sel = p.opt_selection
        db.merge(ProfileRow(
            user_id=state.user_id, school_id=p.school.id, degree_level=p.degree_level.value,
            program_end_date=p.program_end_date,
            opt_intent=sel.opt_intent.value if sel else None,
            first_time_at_level=sel.first_time_at_level if sel else None,
            opt_type=sel.opt_type.value if sel and sel.opt_type else None,
            stage=p.stage.value if p.stage else None,
            **{f: getattr(p.stage_dates, f) for f in PROFILE_DATE_FIELDS},
        ))
        db.merge(ProcessingRow(user_id=state.user_id, **p.processing.model_dump()))
        if p.offer is None:
            db.execute(delete(OfferRow).where(OfferRow.user_id == state.user_id))
        else:
            values = p.offer.model_dump(mode="json")
            db.merge(OfferRow(user_id=state.user_id, **{
                f: getattr(p.offer, f) if f.endswith("_date") or f == "has_offer" else values[f]
                for f in OFFER_FIELDS
            }))

    # --- start over / history ---

    @staticmethod
    def _archive(db: Session, state: UserState) -> None:
        if state.profile is not None:
            db.add(HistoryRow(id=str(uuid.uuid4()), user_id=state.user_id, plan_version=state.plan_version,
                              snapshot={"profile": state.profile.model_dump(mode="json"),
                                        "task_statuses": {k: v.value for k, v in state.task_statuses.items()}}))

    def reset(self, state: UserState) -> None:
        with Session(self.engine) as db, db.begin():
            if db.get(UserRow, state.user_id) is None:
                return
            self._archive(db, state)
            clear_for_reset(state)
            self._save(db, state)

    def restore(self, state: UserState, entry_id: str) -> bool:
        with Session(self.engine) as db, db.begin():
            row = db.get(HistoryRow, entry_id)
            if row is None or row.user_id != state.user_id:
                return False
            entry = _to_history_entry(row)
            db.delete(row)
            self._archive(db, state)
            apply_restore(state, entry)
            self._save(db, state)
        return True

    def history(self, user_id: str) -> list[HistoryEntry]:
        with Session(self.engine) as db:
            rows = db.scalars(select(HistoryRow).where(HistoryRow.user_id == user_id)
                              .order_by(HistoryRow.archived_at.desc(), HistoryRow.plan_version.desc())).all()
            return [_to_history_entry(r) for r in rows]

    # --- assistant feedback ---

    def add_feedback(self, user_id: str, feedback: AssistantFeedbackRequest) -> str:
        row_id = str(uuid.uuid4())
        with Session(self.engine) as db, db.begin():
            db.add(FeedbackRow(
                id=row_id, user_id=user_id, conversation_id=feedback.conversation_id, rating=feedback.rating.value,
                reasons=[r.value for r in feedback.reasons], comment=feedback.comment,
                intent=feedback.intent.value if feedback.intent else None,
                scope=feedback.scope.value if feedback.scope else None, current_page=feedback.current_page))
        return row_id


def _to_history_entry(row: HistoryRow) -> HistoryEntry:
    return HistoryEntry(id=row.id, archived_at=row.archived_at, plan_version=row.plan_version,
                        profile=Profile.model_validate(row.snapshot["profile"]),
                        task_statuses=row.snapshot["task_statuses"])


def _to_profile(user: UserRow, row: ProfileRow, offer: OfferRow | None,
                processing: ProcessingRow | None) -> Profile:
    content = get_content()
    school = next(s for s in content.schools if s.id == row.school_id)
    selection = None
    if row.opt_intent is not None:
        selection = OptSelection(opt_intent=row.opt_intent, first_time_at_level=bool(row.first_time_at_level),
                                 opt_type=row.opt_type)
    return Profile(
        email=user.email,
        school=School(**school.model_dump()),
        degree_level=row.degree_level,
        program_end_date=row.program_end_date,
        timezone=user.timezone,
        opt_selection=selection,
        stage=row.stage,
        stage_dates=StageDates(**{f: getattr(row, f) for f in PROFILE_DATE_FIELDS}),
        offer=Offer(**{f: getattr(offer, f) for f in OFFER_FIELDS}) if offer else None,
        processing=ProcessingChoice(**{f: getattr(processing, f) for f in PROCESSING_FIELDS}) if processing
        else ProcessingChoice(),
        # Policy info always reflects the current catalog, not what it was when saved.
        policy_version=policy_version(content),
        policy_last_reviewed=content.policy.reviewed_at,
    )
