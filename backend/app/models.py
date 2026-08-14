"""SQLAlchemy models for all 15 core objects (FUNKSIONALLIK_LOGIKA.md, section 4)."""

import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    tutor = "tutor"
    staff = "staff"  # dean's office / registrar
    admin = "admin"


class DocumentType(str, enum.Enum):
    syllabus = "syllabus"
    order = "order"  # buyruq
    assignment = "assignment"  # topshiriq
    literature = "literature"  # adabiyot
    regulation = "regulation"  # ichki tartib nizomi
    other = "other"


class AccessLevel(str, enum.Enum):
    public = "public"  # all authenticated roles
    student = "student"
    teacher = "teacher"
    tutor = "tutor"
    staff = "staff"
    admin = "admin"


class PaymentStatus(str, enum.Enum):
    automatic = "automatic"  # arrived via payment system (synthetic Click/Payme)
    uploaded = "uploaded"  # receipt uploaded by student, awaiting confirmation
    confirmed = "confirmed"  # confirmed by tutor


class TurnstileDirection(str, enum.Enum):
    entry = "in"
    exit = "out"


class AttendanceStatus(str, enum.Enum):
    present = "present"
    absent = "absent"
    late = "late"


class ClassSessionStatus(str, enum.Enum):
    held = "held"  # o'tildi (confirmed)
    cancelled = "cancelled"  # qoldirildi
    needs_clarification = "needs_clarification"  # aniqlashtirish kerak


class FlowDocumentType(str, enum.Enum):
    application = "application"  # ariza
    report = "report"  # hisobot
    order = "order"  # buyruq
    letter = "letter"  # xat


class FlowStatus(str, enum.Enum):
    sent = "sent"
    seen = "seen"
    in_progress = "in_progress"
    approved = "approved"
    rejected = "rejected"


class ChatRole(str, enum.Enum):
    """Author of a stored chat message (S4 agent core)."""

    user = "user"
    assistant = "assistant"
    tool = "tool"  # tool result kept for audit: which tool, what it returned


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), index=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id"))
    faculty_id: Mapped[int | None] = mapped_column(Integer, index=True)
    language: Mapped[str] = mapped_column(String(8), default="uz")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    group: Mapped["Group | None"] = relationship(
        back_populates="students", foreign_keys=[group_id]
    )


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    tutor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    faculty_id: Mapped[int | None] = mapped_column(Integer, index=True)

    tutor: Mapped["User | None"] = relationship(foreign_keys=[tutor_id])
    students: Mapped[list["User"]] = relationship(
        back_populates="group", foreign_keys="User.group_id"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    doc_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), index=True)
    language: Mapped[str] = mapped_column(String(8), default="uz")
    access_level: Mapped[AccessLevel] = mapped_column(
        Enum(AccessLevel), default=AccessLevel.public, index=True
    )
    file_path: Mapped[str | None] = mapped_column(String(512))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chunks: Mapped[list["Chunk"]] = relationship(back_populates="document")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    # Vector itself lives in Chroma; this stores the Chroma record id (S3)
    embedding_id: Mapped[str | None] = mapped_column(String(64))
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    document: Mapped["Document"] = relationship(back_populates="chunks")


class Translation(Base):
    __tablename__ = "translations"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), index=True
    )
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("chunks.id"), index=True)
    language: Mapped[str] = mapped_column(String(8))
    translated_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(128))
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    deadline: Mapped[datetime] = mapped_column(DateTime)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    subject: Mapped[str] = mapped_column(String(128))
    room: Mapped[str] = mapped_column(String(32))
    weekday: Mapped[int] = mapped_column(Integer)  # 0 = Monday ... 6 = Sunday
    pair_number: Mapped[int] = mapped_column(Integer)  # juftlik: 1..6
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    total_amount: Mapped[float] = mapped_column(Numeric(14, 2))
    academic_year: Mapped[str] = mapped_column(String(16))  # e.g. "2025-2026"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(14, 2))
    paid_at: Mapped[datetime] = mapped_column(DateTime)
    receipt_number: Mapped[str | None] = mapped_column(String(64))
    receipt_file: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.automatic
    )
    academic_year: Mapped[str] = mapped_column(String(16))


class TurnstileLog(Base):
    __tablename__ = "turnstile_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    direction: Mapped[TurnstileDirection] = mapped_column(Enum(TurnstileDirection))


class Attendance(Base):
    __tablename__ = "attendances"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus))
    marked_by_teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class ClassSession(Base):
    __tablename__ = "class_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[ClassSessionStatus] = mapped_column(
        Enum(ClassSessionStatus), default=ClassSessionStatus.needs_clarification
    )
    teacher_arrived_at: Mapped[datetime | None] = mapped_column(DateTime)


class FlowDocument(Base):
    __tablename__ = "flow_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_type: Mapped[FlowDocumentType] = mapped_column(
        Enum(FlowDocumentType), index=True
    )
    template_id: Mapped[str | None] = mapped_column(String(64))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # Recipient is either a role (e.g. whole dean's office) or a concrete user
    recipient_role: Mapped[UserRole | None] = mapped_column(Enum(UserRole))
    recipient_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    body_text: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(512))
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[FlowStatus] = mapped_column(
        Enum(FlowStatus), default=FlowStatus.sent, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    history: Mapped[list["FlowHistory"]] = relationship(
        back_populates="flow_document", order_by="FlowHistory.timestamp"
    )


class FlowHistory(Base):
    __tablename__ = "flow_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    flow_document_id: Mapped[int] = mapped_column(
        ForeignKey("flow_documents.id"), index=True
    )
    status: Mapped[FlowStatus] = mapped_column(Enum(FlowStatus))
    comment: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    changed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    flow_document: Mapped["FlowDocument"] = relationship(back_populates="history")


class Conversation(Base):
    """One chat thread of one user (S4: `POST /chat` history)."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation", order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    """One message inside a conversation: user, assistant or tool result."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    role: Mapped[ChatRole] = mapped_column(Enum(ChatRole), index=True)
    content: Mapped[str] = mapped_column(Text)
    tool_name: Mapped[str | None] = mapped_column(String(64))
    # Citations collected for this message: [{"type", "label", "document_id", ...}]
    sources: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    notif_type: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    # Link to the related object: e.g. link_type="flow_document", link_id=12
    link_type: Mapped[str | None] = mapped_column(String(64))
    link_id: Mapped[int | None] = mapped_column(Integer)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
