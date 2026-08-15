"""S13 tests: the admin panel — users, uploads, stats and the demo reset.

Three things are proven here:

* **the guard** — every `/admin/*` endpoint answers 403 for a student and for
  the dean's office; only the admin passes (the single `require_role()`
  mechanism, no manual role checks anywhere);
* **the chain that is the S13 DoD** — an uploaded document is written to
  `uploads/documents/`, gets a `Document` + `Chunk` rows and is found by
  `rag.search.search` in the very next query;
* **the reset flag** — a second reset request while one runs is refused (409).
  The reset itself is not executed here (it re-seeds and re-indexes, ~15-30 s):
  the background task is replaced by a spy, so the endpoint contract is tested
  without paying for the work. The two real steps are covered by
  `seed.generate` (conftest runs it for every session) and by
  `tests/test_s3_rag.py` (`ingest_all(reset=True)` via `indexed_corpus`).

Everything this file creates (a user, a document, its file) is removed again:
pytest shares one demo database between the session files.
"""

import pytest

from app.models import Chunk, Document, Group, Notification, User, UserRole
from app.rag import ingest as rag_ingest
from app.rag.search import search
from app.services import admin as admin_service

DEMO_PASSWORD = "demo123"

# A term that appears nowhere in the seed corpus — so a hit can only come from
# the freshly uploaded file.
UPLOAD_TITLE = "Kvant laboratoriyasi ish tartibi (S13 sinov)"
UPLOAD_FILENAME = "kvant_lab_s13.md"
UPLOAD_BODY = """# Kvant laboratoriyasi ish tartibi

## 1. Umumiy qoidalar

Kvant laboratoriyasi 401-xonada joylashgan va faqat kriostat operatori
ruxsati bilan ochiladi. Kubit stendida ishlash uchun oldindan ro'yxatdan
o'tish talab qilinadi.

## 2. Xavfsizlik

Kriostat ishlayotgan paytda laboratoriyaga yolg'iz kirish taqiqlanadi.
Suyuq geliy bilan ishlashda himoya ko'zoynagi majburiy.
"""


# --- helpers ----------------------------------------------------------------


def headers(client, username):
    res = client.post(
        "/auth/login", json={"username": username, "password": DEMO_PASSWORD}
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture(scope="module")
def admin_headers(client):
    return headers(client, "admin")


@pytest.fixture(scope="module")
def admin_user(db_session):
    db_session.rollback()
    return db_session.query(User).filter_by(username="admin").one()


@pytest.fixture
def temp_user(db_session):
    """Removes whatever account a test created, whatever the test did."""
    created: list[str] = []
    yield created
    db_session.rollback()
    for username in created:
        row = db_session.query(User).filter_by(username=username).one_or_none()
        if row is not None:
            db_session.delete(row)
    db_session.commit()


@pytest.fixture
def temp_document(db_session):
    """Removes an uploaded document: Chroma entries, Chunk rows, row, file."""
    created: list[int] = []
    yield created
    db_session.rollback()
    for document_id in created:
        document = db_session.get(Document, document_id)
        if document is None:
            continue
        path = rag_ingest.document_path(document)
        rag_ingest.delete_document_index(db_session, document)
        db_session.delete(document)
        db_session.commit()
        if path.exists():
            path.unlink()


# --- the guard --------------------------------------------------------------

GUARDED = [
    ("get", "/admin/users", None),
    ("get", "/admin/groups", None),
    ("get", "/admin/documents", None),
    ("get", "/admin/stats", None),
    ("get", "/admin/reset/status", None),
    ("post", "/admin/reset", None),
    (
        "post",
        "/admin/users",
        {
            "username": "ruxsatsiz",
            "full_name": "Ruxsatsiz Foydalanuvchi",
            "role": "student",
            "password": "demo123",
        },
    ),
    ("patch", "/admin/users/1", {"role": "student"}),
]


@pytest.mark.parametrize("username", ["aliyev", "umarov", "nazarova", "rashidova"])
@pytest.mark.parametrize("method,path,body", GUARDED)
def test_admin_endpoints_reject_other_roles(client, username, method, path, body):
    """Student, teacher, tutor and the dean's office all get 403 — every route."""
    call = getattr(client, method)
    res = (
        call(path, headers=headers(client, username))
        if body is None
        else call(path, json=body, headers=headers(client, username))
    )
    assert res.status_code == 403, f"{method} {path} -> {res.status_code}"


def test_upload_rejects_other_roles(client):
    res = client.post(
        "/admin/documents",
        headers=headers(client, "rashidova"),
        data={"title": "Ruxsatsiz", "doc_type": "other"},
        files={"file": ("a.md", b"# salom", "text/markdown")},
    )
    assert res.status_code == 403


def test_admin_endpoints_require_a_token(client):
    assert client.get("/admin/users").status_code == 401
    assert client.get("/admin/stats").status_code == 401


# --- users ------------------------------------------------------------------


def test_list_users_filters_and_search(client, admin_headers):
    everyone = client.get("/admin/users", headers=admin_headers)
    assert everyone.status_code == 200
    rows = everyone.json()
    logins = {row["username"] for row in rows}
    assert {"aliyev", "umarov", "nazarova", "rashidova", "admin"} <= logins
    assert all(row["role_label"] for row in rows)

    students = client.get("/admin/users?role=student", headers=admin_headers).json()
    assert students and all(row["role"] == "student" for row in students)
    assert len(students) < len(rows)
    # A student always carries their group name — the table shows it as is.
    assert all(row["group_name"] for row in students)

    found = client.get("/admin/users?q=aliyev", headers=admin_headers).json()
    assert [row["username"] for row in found] == ["aliyev"]


def test_create_user_then_change_role(client, admin_headers, db_session, temp_user):
    db_session.rollback()
    group = db_session.query(Group).order_by(Group.id).first()

    payload = {
        "username": "demo_talaba_s13",
        "full_name": "Demo Talaba (sintetik)",
        "role": "student",
        "password": "demo123",
        "group_id": group.id,
        "faculty_id": group.faculty_id,
    }
    created = client.post("/admin/users", json=payload, headers=admin_headers)
    assert created.status_code == 201, created.text
    temp_user.append(payload["username"])
    body = created.json()
    assert body["role"] == "student"
    assert body["group_name"] == group.name
    assert body["role_label"] == "talaba"

    # The account really works: the hashed password is a login password.
    login = client.post(
        "/auth/login",
        json={"username": payload["username"], "password": "demo123"},
    )
    assert login.status_code == 200

    changed = client.patch(
        f"/admin/users/{body['id']}",
        json={"role": "teacher", "group_id": 0},
        headers=admin_headers,
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["role"] == "teacher"
    assert changed.json()["role_label"] == "o'qituvchi"
    assert changed.json()["group_id"] is None

    # ... and the change is persisted, not just echoed back.
    db_session.rollback()
    stored = db_session.query(User).filter_by(username=payload["username"]).one()
    assert stored.role == UserRole.teacher


def test_create_user_validation(client, admin_headers, temp_user):
    duplicate = client.post(
        "/admin/users",
        json={
            "username": "aliyev",
            "full_name": "Ikkinchi Aliyev",
            "role": "student",
            "password": "demo123",
        },
        headers=admin_headers,
    )
    assert duplicate.status_code == 409

    weak = client.post(
        "/admin/users",
        json={
            "username": "demo_zaif_s13",
            "full_name": "Demo Zaif",
            "role": "student",
            "password": "123",
        },
        headers=admin_headers,
    )
    assert weak.status_code == 422

    unknown_group = client.post(
        "/admin/users",
        json={
            "username": "demo_guruhsiz_s13",
            "full_name": "Demo Guruhsiz",
            "role": "student",
            "password": "demo123",
            "group_id": 9999,
        },
        headers=admin_headers,
    )
    assert unknown_group.status_code == 422


def test_admin_cannot_demote_themselves(client, admin_headers, admin_user):
    res = client.patch(
        f"/admin/users/{admin_user.id}",
        json={"role": "student"},
        headers=admin_headers,
    )
    assert res.status_code == 409
    # ...and nothing changed.
    assert admin_user.role == UserRole.admin


def test_update_unknown_user_is_404(client, admin_headers):
    res = client.patch(
        "/admin/users/999999", json={"role": "student"}, headers=admin_headers
    )
    assert res.status_code == 404


# --- document upload (the S13 DoD) ------------------------------------------


def test_upload_document_is_indexed_and_searchable(
    client, admin_headers, db_session, admin_user, indexed_corpus, temp_document
):
    """upload -> Document + Chunk rows -> found by the search the agent uses."""
    res = client.post(
        "/admin/documents",
        headers=admin_headers,
        data={
            "title": UPLOAD_TITLE,
            "doc_type": "regulation",
            "language": "uz",
            "access_level": "public",
        },
        files={"file": (UPLOAD_FILENAME, UPLOAD_BODY.encode("utf-8"), "text/markdown")},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    temp_document.append(body["document"]["id"])

    assert body["chunks"] >= 1
    assert body["document"]["title"] == UPLOAD_TITLE
    assert body["document"]["doc_type"] == "regulation"
    assert body["document"]["access_level"] == "public"
    assert body["document"]["indexed"] is True
    assert body["document"]["uploaded"] is True
    # Never in seed/documents/: a demo reset must not be able to delete it.
    assert not body["document"]["file_path"].startswith("seed/")

    db_session.rollback()
    document = db_session.get(Document, body["document"]["id"])
    assert document is not None
    stored = rag_ingest.document_path(document)
    assert stored.exists()
    assert stored.parent == admin_service.uploads_dir()
    chunks = db_session.query(Chunk).filter_by(document_id=document.id).all()
    assert len(chunks) == body["chunks"]
    assert all(chunk.embedding_id for chunk in chunks)

    # The DoD: the very next search finds it (same function `hujjat_qidir` calls).
    hits = search("kriostat va kubit stendi qoidalari", admin_user, top_k=5)
    assert document.id in {hit.document_id for hit in hits}

    # It also shows up in the admin list, with its chunk count.
    listed = client.get("/admin/documents", headers=admin_headers).json()
    row = next(r for r in listed if r["id"] == document.id)
    assert row["chunk_count"] == body["chunks"] and row["indexed"] is True


def test_upload_rejects_unsupported_and_empty_files(client, admin_headers):
    unsupported = client.post(
        "/admin/documents",
        headers=admin_headers,
        data={"title": "PDF hujjat", "doc_type": "other"},
        files={"file": ("hujjat.pdf", b"%PDF-1.4 binary", "application/pdf")},
    )
    assert unsupported.status_code == 422

    empty = client.post(
        "/admin/documents",
        headers=admin_headers,
        data={"title": "Bo'sh hujjat", "doc_type": "other"},
        files={"file": ("bosh.md", b"   \n\n  ", "text/markdown")},
    )
    assert empty.status_code == 422


def test_safe_filename_keeps_the_suffix():
    assert admin_service.safe_filename("Buyruq 91-M.md") == "Buyruq_91-M.md"
    assert admin_service.safe_filename("../../etc/passwd.txt") == "passwd.txt"


# --- stats ------------------------------------------------------------------


def test_stats_are_collected_from_the_existing_services(
    client, admin_headers, indexed_corpus
):
    res = client.get("/admin/stats", headers=admin_headers)
    assert res.status_code == 200, res.text
    data = res.json()

    roles = {row["role"]: row["count"] for row in data["users"]["by_role"]}
    assert set(roles) == {"student", "teacher", "tutor", "staff", "admin"}
    assert data["users"]["total"] == sum(roles.values())
    assert roles["admin"] >= 1 and roles["student"] > 0
    assert data["users"]["group_count"] == 4
    assert data["users"]["faculty_count"] == 2

    assert data["corpus"]["document_count"] >= 10
    assert data["corpus"]["chunk_count"] > 0
    assert data["corpus"]["indexed_count"] == data["corpus"]["document_count"]

    # Admin scope = the whole university, so these are the seed's own numbers.
    assert data["payments"]["student_count"] == roles["student"]
    assert data["payments"]["debtor_count"] >= 1
    assert data["payments"]["total_amount"] > 0
    assert data["payments"]["pending_count"] >= 1  # sharipova's uploaded receipt

    assert data["presence"]["student_count"] == roles["student"]
    assert (
        data["presence"]["inside_count"]
        + data["presence"]["left_count"]
        + data["presence"]["absent_count"]
        == roles["student"]
    )

    assert data["teachers"]["teacher_count"] == roles["teacher"]
    assert data["docflow"]["total"] >= 1
    assert data["notifications"]["total"] >= 1

    assert data["source"]["label"].startswith("Boshqaruv paneli statistikasi")
    assert data["disclaimer"]


def test_stats_do_not_write_teacher_absence_notifications(
    client, admin_headers, db_session
):
    """Opening the dashboard is read-only (`teacher_day_overview(notify=False)`)."""
    db_session.rollback()
    before = db_session.query(Notification).filter_by(notif_type="teacher_absence").count()
    assert client.get("/admin/stats", headers=admin_headers).status_code == 200
    db_session.rollback()
    after = db_session.query(Notification).filter_by(notif_type="teacher_absence").count()
    assert after == before


# --- demo reset -------------------------------------------------------------


def test_reset_starts_in_the_background(client, admin_headers, monkeypatch):
    """The endpoint claims the slot and hands the work to a background task."""
    calls: list[str] = []

    def fake_run_reset():
        calls.append("run")
        return admin_service.finish_reset(True, "sinov reset", documents=3, chunks=7)

    monkeypatch.setattr(admin_service, "run_reset", fake_run_reset)

    res = client.post("/admin/reset", headers=admin_headers)
    assert res.status_code == 202, res.text
    assert res.json()["running"] is True  # the answer is sent before the work

    assert calls == ["run"]  # TestClient runs background tasks before returning
    state = client.get("/admin/reset/status", headers=admin_headers).json()
    assert state["running"] is False
    assert state["ok"] is True
    assert state["message"] == "sinov reset"
    assert (state["documents"], state["chunks"]) == (3, 7)
    assert state["started_at"] and state["finished_at"]


def test_second_reset_is_refused_while_one_runs(client, admin_headers):
    assert admin_service.begin_reset() is True
    try:
        assert admin_service.begin_reset() is False  # the flag itself
        res = client.post("/admin/reset", headers=admin_headers)
        assert res.status_code == 409
        running = client.get("/admin/reset/status", headers=admin_headers).json()
        assert running["running"] is True
        assert running["message"] == admin_service.RESET_RUNNING_MESSAGE
    finally:
        admin_service.finish_reset(True, "tozalash")
