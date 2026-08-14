"""Pydantic schemas for the core objects. Response format source of truth."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models import (
    AccessLevel,
    AttendanceStatus,
    ClassSessionStatus,
    DocumentType,
    FlowDocumentType,
    FlowStatus,
    PaymentStatus,
    TurnstileDirection,
    UserRole,
)


class ORMSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthOut(BaseModel):
    status: str
    app: str


class UserOut(ORMSchema):
    id: int
    username: str
    full_name: str
    role: UserRole
    group_id: int | None
    faculty_id: int | None
    language: str


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class OkOut(BaseModel):
    status: str = "ok"


class GroupOut(ORMSchema):
    id: int
    name: str
    tutor_id: int | None
    faculty_id: int | None


class DocumentOut(ORMSchema):
    id: int
    title: str
    doc_type: DocumentType
    language: str
    access_level: AccessLevel
    file_path: str | None
    uploaded_at: datetime


class ChunkOut(ORMSchema):
    id: int
    document_id: int
    text: str
    order_index: int


class TranslationOut(ORMSchema):
    id: int
    document_id: int | None
    chunk_id: int | None
    language: str
    translated_text: str
    created_at: datetime


class AssignmentOut(ORMSchema):
    id: int
    subject: str
    group_id: int
    description: str
    deadline: datetime
    teacher_id: int
    created_at: datetime


class ScheduleOut(ORMSchema):
    id: int
    group_id: int
    subject: str
    room: str
    weekday: int
    pair_number: int
    teacher_id: int


class ContractOut(ORMSchema):
    id: int
    student_id: int
    total_amount: float
    academic_year: str


class PaymentOut(ORMSchema):
    id: int
    student_id: int
    amount: float
    paid_at: datetime
    receipt_number: str | None
    receipt_file: str | None
    status: PaymentStatus
    academic_year: str


class TurnstileLogOut(ORMSchema):
    id: int
    user_id: int
    timestamp: datetime
    direction: TurnstileDirection


class AttendanceOut(ORMSchema):
    id: int
    student_id: int
    schedule_id: int
    date: date
    status: AttendanceStatus
    marked_by_teacher_id: int


class ClassSessionOut(ORMSchema):
    id: int
    schedule_id: int
    date: date
    status: ClassSessionStatus
    teacher_arrived_at: datetime | None


class FlowDocumentOut(ORMSchema):
    id: int
    doc_type: FlowDocumentType
    template_id: str | None
    sender_id: int
    recipient_role: UserRole | None
    recipient_user_id: int | None
    body_text: str
    file_path: str | None
    due_date: date | None
    status: FlowStatus
    created_at: datetime


class FlowHistoryOut(ORMSchema):
    id: int
    flow_document_id: int
    status: FlowStatus
    comment: str | None
    timestamp: datetime
    changed_by_id: int


class NotificationOut(ORMSchema):
    id: int
    user_id: int
    notif_type: str
    text: str
    link_type: str | None
    link_id: int | None
    is_read: bool
    created_at: datetime
