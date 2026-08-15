"""S14: publishing a document announces itself (FUNKSIONALLIK 3.10).

The last un-triggered row of the notification table — "Yangi buyruq e'lon
qilindi -> tegishli rollar" — is wired here: `services/admin.upload_document`
calls `services/notifications.notify_new_document` once the file is stored and
indexed. Who counts as a "relevant role" is not a new rule: it is
`rag.search.allowed_access_levels` read backwards.
"""

import pytest

from app.models import AccessLevel, Document, Notification, User, UserRole
from app.rag import ingest as rag_ingest
from app.rag.search import allowed_access_levels
from app.services import notifications as notifications_service

DEMO_PASSWORD = "demo123"

PUBLIC_TITLE = "Talabalar turar joyi qoidalari (S14 sinov)"
PUBLIC_FILENAME = "yotoqxona_s14.md"
PUBLIC_BODY = """# Talabalar turar joyi qoidalari

Turar joyga kirish talabalik guvohnomasi bilan amalga oshiriladi.
Mehmonlarni qabul qilish soat 21:00 gacha ruxsat etiladi.
"""

STAFF_TITLE = "Ichki xizmat yozishmasi (S14 sinov)"
STAFF_FILENAME = "xizmat_s14.md"
STAFF_BODY = """# Ichki xizmat yozishmasi

Dekanat xodimlari uchun oylik hisobot shakli yangilandi.
"""


def headers(client, username):
    res = client.post(
        "/auth/login", json={"username": username, "password": DEMO_PASSWORD}
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture(scope="module")
def admin_headers(client):
    return headers(client, "admin")


@pytest.fixture
def temp_document(db_session):
    """Removes the uploaded document *and* the notifications it produced."""
    created: list[int] = []
    yield created
    db_session.rollback()
    for document_id in created:
        db_session.query(Notification).filter(
            Notification.link_type == notifications_service.LINK_DOCUMENT,
            Notification.link_id == document_id,
        ).delete(synchronize_session=False)
        db_session.commit()
        document = db_session.get(Document, document_id)
        if document is None:
            continue
        path = rag_ingest.document_path(document)
        rag_ingest.delete_document_index(db_session, document)
        db_session.delete(document)
        db_session.commit()
        if path.exists():
            path.unlink()


def upload(client, admin_headers, *, title, filename, body, access_level, doc_type):
    res = client.post(
        "/admin/documents",
        headers=admin_headers,
        data={
            "title": title,
            "doc_type": doc_type,
            "language": "uz",
            "access_level": access_level,
        },
        files={"file": (filename, body.encode("utf-8"), "text/markdown")},
    )
    assert res.status_code == 201, res.text
    return res.json()["document"]["id"]


def rows_for(db_session, document_id, username):
    db_session.rollback()
    user = db_session.query(User).filter_by(username=username).one()
    return (
        db_session.query(Notification)
        .filter(
            Notification.user_id == user.id,
            Notification.notif_type == notifications_service.NEW_ORDER,
            Notification.link_id == document_id,
        )
        .all()
    )


# --- who is a "relevant role" -----------------------------------------------


def test_roles_for_access_mirrors_the_search_filter(db_session):
    db_session.rollback()
    public = notifications_service.roles_for_access(AccessLevel.public)
    assert set(public) == set(UserRole)

    staff_only = notifications_service.roles_for_access(AccessLevel.staff)
    assert set(staff_only) == {UserRole.staff, UserRole.admin}

    # The same answer the search filter gives, from the other direction.
    for username, role in (
        ("aliyev", UserRole.student),
        ("rashidova", UserRole.staff),
    ):
        user = db_session.query(User).filter_by(username=username).one()
        levels = allowed_access_levels(user)
        assert (AccessLevel.staff.value in levels) == (role in staff_only)


# --- the trigger -------------------------------------------------------------


def test_public_upload_notifies_every_role_but_the_uploader(
    client, admin_headers, db_session, temp_document
):
    document_id = upload(
        client,
        admin_headers,
        title=PUBLIC_TITLE,
        filename=PUBLIC_FILENAME,
        body=PUBLIC_BODY,
        access_level="public",
        doc_type="regulation",
    )
    temp_document.append(document_id)

    for username in ("aliyev", "umarov", "nazarova", "rashidova"):
        rows = rows_for(db_session, document_id, username)
        assert len(rows) == 1, username
        row = rows[0]
        assert PUBLIC_TITLE in row.text
        assert row.link_type == notifications_service.LINK_DOCUMENT
        assert row.is_read is False

    # The admin who published it does not notify themselves.
    assert rows_for(db_session, document_id, "admin") == []


def test_staff_only_upload_reaches_the_dean_office_alone(
    client, admin_headers, db_session, temp_document
):
    document_id = upload(
        client,
        admin_headers,
        title=STAFF_TITLE,
        filename=STAFF_FILENAME,
        body=STAFF_BODY,
        access_level="staff",
        doc_type="order",
    )
    temp_document.append(document_id)

    assert len(rows_for(db_session, document_id, "rashidova")) == 1
    assert rows_for(db_session, document_id, "aliyev") == []
    assert rows_for(db_session, document_id, "umarov") == []
    # doc_type=order -> the wording of the 3.10 table row.
    assert "Yangi buyruq e'lon qilindi" in rows_for(
        db_session, document_id, "rashidova"
    )[0].text


def test_announcing_the_same_document_twice_writes_nothing_new(
    client, admin_headers, db_session, temp_document
):
    document_id = upload(
        client,
        admin_headers,
        title=PUBLIC_TITLE,
        filename=PUBLIC_FILENAME,
        body=PUBLIC_BODY,
        access_level="public",
        doc_type="other",
    )
    temp_document.append(document_id)

    db_session.rollback()
    document = db_session.get(Document, document_id)
    admin = db_session.query(User).filter_by(username="admin").one()
    before = db_session.query(Notification).count()
    assert (
        notifications_service.notify_new_document(
            db_session, document, exclude_user_id=admin.id
        )
        == 0
    )
    assert db_session.query(Notification).count() == before


def test_the_bell_shows_the_announcement_with_a_document_link(
    client, admin_headers, temp_document
):
    document_id = upload(
        client,
        admin_headers,
        title=PUBLIC_TITLE,
        filename=PUBLIC_FILENAME,
        body=PUBLIC_BODY,
        access_level="public",
        doc_type="order",
    )
    temp_document.append(document_id)

    feed = client.get("/notifications", headers=headers(client, "aliyev")).json()
    row = next(
        r
        for r in feed["rows"]
        if r["notif_type"] == notifications_service.NEW_ORDER
        and r["link_id"] == document_id
    )
    assert row["link_type"] == notifications_service.LINK_DOCUMENT
    assert PUBLIC_TITLE in row["text"]
    assert feed["unread_count"] >= 1
