"""S5 tests: the documents API behind the chat UI's source chips.

The access rule is the RAG one (`rag.search.allowed_access_levels`): the
confidential order "Buyruq 91-M" is `staff`-level, so a student must not see it
in the list and must get 404 — not 403 — when asking for it by id.
"""

DEMO_PASSWORD = "demo123"
SECRET_TITLE_PART = "91-M"
SECRET_PHRASE = "XIZMAT FOYDALANISHI UCHUN"


def headers(client, username):
    res = client.post(
        "/auth/login", json={"username": username, "password": DEMO_PASSWORD}
    )
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def listed(client, username):
    res = client.get("/documents", headers=headers(client, username))
    assert res.status_code == 200, res.text
    return res.json()


def secret_id(client):
    """Id of the confidential order, looked up as staff (who may see it)."""
    match = [d for d in listed(client, "rashidova") if SECRET_TITLE_PART in d["title"]]
    assert len(match) == 1, match
    return match[0]["id"]


# --- 1. list ----------------------------------------------------------------


def test_student_list_hides_the_confidential_order(client):
    documents = listed(client, "aliyev")
    assert documents, "talabaga birorta hujjat ko'rinmadi"
    assert all(SECRET_TITLE_PART not in d["title"] for d in documents), documents
    assert all(d["access_level"] == "public" for d in documents), documents

    first = documents[0]
    assert set(first) == {
        "id",
        "title",
        "doc_type",
        "language",
        "access_level",
        "uploaded_at",
    }, first  # file_path is internal and must not leak


def test_staff_list_includes_the_confidential_order(client):
    documents = listed(client, "rashidova")
    secret = [d for d in documents if SECRET_TITLE_PART in d["title"]]
    assert len(secret) == 1, documents
    assert secret[0]["access_level"] == "staff"
    # staff sees everything a student sees, plus the order
    assert len(documents) == len(listed(client, "aliyev")) + 1


def test_admin_sees_every_document(client):
    assert len(listed(client, "admin")) >= len(listed(client, "rashidova"))


# --- 2. detail --------------------------------------------------------------


def test_student_cannot_open_the_confidential_order(client):
    res = client.get(f"/documents/{secret_id(client)}", headers=headers(client, "aliyev"))
    # 404, not 403: existence itself must stay hidden
    assert res.status_code == 404, res.text
    assert SECRET_PHRASE not in res.text


def test_staff_opens_the_confidential_order_with_full_text(client):
    doc_id = secret_id(client)
    res = client.get(f"/documents/{doc_id}", headers=headers(client, "rashidova"))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["id"] == doc_id
    assert SECRET_TITLE_PART in body["title"]
    assert SECRET_PHRASE in body["text"]
    assert "file_path" not in body


def test_student_opens_a_public_document(client):
    documents = listed(client, "aliyev")
    doc_id = documents[0]["id"]
    res = client.get(f"/documents/{doc_id}", headers=headers(client, "aliyev"))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["id"] == doc_id
    assert body["title"] == documents[0]["title"]
    assert body["text"].strip(), "hujjat matni bo'sh"


def test_missing_document_is_404(client):
    res = client.get("/documents/999999", headers=headers(client, "admin"))
    assert res.status_code == 404, res.text


# --- 3. auth ----------------------------------------------------------------


def test_documents_require_authentication(client):
    assert client.get("/documents").status_code == 401
    assert client.get("/documents/1").status_code == 401


# --- 4. the chat UI also needs the disclaimer on replayed history -----------


def test_conversation_detail_carries_the_disclaimer(client, indexed_corpus):
    auth = headers(client, "aliyev")
    sent = client.post("/chat", json={"message": "Juftlik vaqtlari qanday?"}, headers=auth)
    assert sent.status_code == 200, sent.text
    conversation_id = sent.json()["conversation_id"]

    loaded = client.get(f"/chat/conversations/{conversation_id}", headers=auth)
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["disclaimer"] == sent.json()["disclaimer"]
    assert "rasmiy hujjat" in loaded.json()["disclaimer"]
