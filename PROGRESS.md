# PROGRESS — joriy holat

> Har sessiya oxirida yangilanadi. Yangi sessiya SHU FAYLDAN boshlanadi.

## Joriy sessiya: S7 (navbatda)

S6 yakunlandi (DoD 3/3: `pytest` **54/54** — S2 12 + S3 9 + S4 9 + S5 9 +
S6 15; `npm run lint` va `npm run build` toza; jonli tekshiruv uvicorn+curl
bilan (bitta hujjat 3 rolda — promptdagi rakurs uchchalasida boshqacha;
ML hujjati → `parts: 2` map-reduce; talaba 91-M rezyumesini so'rasa **404**,
dekanat 200; chat orqali `use_tool:hujjat_rezyume:{...}` markeri manba +
disclaimer bilan ishlaydi) va **brauzerda** (headless Chrome/CDP): "Rezyume"
tugmasi → blok, manba + disclaimer + "Yopish", original matn joyida qoladi,
konsolda xato yo'q).
S7 (Tarjima moduli) uchun izohlar:

- **Hujjat matni qayerdan olinadi:** `app/services/documents.py` —
  `document_text(db, document)` (avval `Document.file_path` fayli, bo'sh
  bo'lsa `Chunk` lardan yig'iladi). Ruxsat: `get_visible_document(db, user,
  id)` → None bo'lsa **404**. Tarjima servisi ham SHU ikkitasidan foydalansin,
  o'z filtri/o'qishini yozmasin. Nomga qarab topish uchun tayyor helper ham
  bor: `find_visible_document_by_title(db, user, nom)` (S6 da qo'shildi).
- **Paragrafga bo'lish tayyor:** `app/services/summarization.py` dagi
  `split_parts(text, part_chars, max_parts) -> (parts, truncated)` —
  paragraf chegarasini buzmaydi. Tarjima paragraf-paragraf ketadi, shuning
  uchun uni import qilib ishlatish yoki shu naqshni takrorlash mumkin
  (yangi nusxa yasamasdan).
- **`Translation` jadvali (`models.py:157`, kesh uchun tayyor):**
  `id`, `document_id` (nullable, FK documents), `chunk_id` (nullable, FK
  chunks), `language` (String(8) — MAQSAD tili), `translated_text` (Text),
  `created_at`. Sxema `schemas.TranslationOut` da bor (hozircha
  ishlatilmaydi). Butun hujjat tarjimasi = `document_id` to'ldirilgan qator;
  bo'lak tarjimasi = `chunk_id`. Jadval `seed/generate.py` dagi `ALL_MODELS`
  ro'yxatida bor — demo reset keshni ham tozalaydi.
- **Endpoint naqshi (S6 dan nusxa oling):** `POST /documents/{id}/summary`
  — router yupqa (`app/api/documents.py`), ruxsat `get_visible_document`,
  logika `services/` da, javobda `source` (`schemas.ChatSource`) va
  `disclaimer` (`AGENT_DISCLAIMER`). Tarjima uchun ham xuddi shu naqsh:
  `POST /documents/{id}/translate?til=uz` yoki body bilan.
- **LLM klient interfeysi:** `app/llm/client.py` —
  `get_llm_client().chat(messages, tools=None, system=None) -> LLMResponse`.
  Tarjima chaqiruvi `tools` bermaydi (vosita kerak emas), faqat
  `messages=[{"role": "user", "content": prompt}]` + `system`.
- **Mock rejimda tarjimani qanday test qilish (S6 da ishlagan usul):**
  mock provayder `tools=None` bo'lganda `[mock:<digest>] Echo: <promptning
  ilk 600 belgisi>` qaytaradi — ya'ni tarjima MATNI haqiqiy tarjima emas.
  Shuning uchun testlar mexanikani tekshiradi: `monkeypatch.setattr(
  <servis moduli>, "get_llm_client", lambda: RecordingClient())` bilan
  promptlar va chaqiruvlar soni yoziladi (namuna:
  `tests/test_s6_summary.py` dagi `RecordingClient` + `recorder` fixture).
  Kesh testi: ikkinchi chaqiruvda LLM chaqiruvlari soni **0** bo'lishi kerak.
- **DocumentPanel tuzilishi (`frontend/src/components/DocumentPanel.tsx`):**
  `documentId` propi → `useEffect` da `documentsApi.get(id)`; holat id
  bo'yicha **derivatsiya** qilinadi (`loaded.id === documentId`), effektda
  sinxron `setState` YO'Q (Next 16 eslint qoidasi). Header'da amal tugmalari
  qatori bor (hozir: "Rezyume" + "Yopish") — "Tarjima" tugmasi shu qatorga
  qo'shiladi. Kontent maydonida avval rezyume bloki (`<section>`), keyin
  `<Markdown text={document.text} />`. Yonma-yon ko'rinish uchun shu
  kontent maydonini ikki ustunga bo'lish kerak (chapda `document.text`,
  o'ngda tarjima) — original hech qachon almashtirilmaydi (domen qoidasi 4).
- **`lib/api.ts`:** `documentsApi = { list, get, summary }` — tarjima metodi
  shu obyektga qo'shiladi, UI matnlari `src/i18n/uz.json` → `documents.*`.
- **Hujjatlar API (S5 da qo'shildi, `app/api/documents.py`):**
  ```
  GET  /documents              -> [{id, title, doc_type, language, access_level, uploaded_at}]
  GET  /documents/{id}         -> yuqoridagilar + text (to'liq matn)
  POST /documents/{id}/summary -> {document_id, title, summary, parts,
                                   truncated, source, disclaimer}   (S6)
  ```
  Sxemalar: `schemas.DocumentListItemOut` / `DocumentDetailOut` /
  `DocumentSummaryOut`.
  `file_path` ATAYLAB chiqarilmaydi (ichki yo'l). Rol filtri —
  `rag.search.allowed_access_levels(user)`, biznes logika
  `app/services/documents.py` da (`visible_documents`, `get_visible_document`,
  `find_visible_document_by_title`, `document_text`). Ko'rish huquqi yo'q yoki
  mavjud bo'lmagan hujjat → **404** (403 emas: mavjudligi ham oshkor
  bo'lmaydi). Matn `Document.file_path` dan o'qiladi, bo'sh bo'lsa `Chunk`
  lardan yig'iladi.
- **Frontend fayllari (S5):** sahifalar `src/app/(protected)/chat/page.tsx`
  (suhbat holati SHU YERDA: `messages`, `activeId`, `openDocumentId`) va
  `.../documents/page.tsx`; komponentlar `src/components/` da: `ChatWindow`
  (faqat ko'rinish), `ConversationList`, `SourceChips`, `DocumentPanel`,
  `DocumentList`, `RoleDashboard` (+ `hasDashboard(role)`), `Markdown`
  (o'z yozganimiz, kutubxonasiz). Yordamchilar: `src/lib/chat.ts`
  (`ViewMessage`, `toViewMessages`), `src/lib/labels.ts` (enum → o'zbekcha
  yorliq, sana formati).
- **Hujjat paneli qanday ochiladi:** chatdagi manba chipi (`SourceChips`,
  faqat `type === "document"` va `document_id != null` bo'lganda tugma) →
  `onOpenDocument(document_id)` → chat sahifasi `openDocumentId` ni
  o'rnatadi → o'ng panelda `DocumentPanel` chiqadi (o'sha panelning aynan
  o'zi `/documents` sahifasida ham ishlatiladi).
- **MUHIM (Next 16 + React eslint):** `react-hooks/set-state-in-effect`
  qoidasi `useEffect` ichida **sinxron** `setState` ni XATO deb hisoblaydi
  (`npm run lint` yiqiladi). Yechim: holatni hodisa ishlovchilarida (klik,
  submit) yangilash, effektda esa faqat `.then()/.catch()` ichida; "propdan
  kelgan id o'zgarganda tozalash" o'rniga holatni **derivatsiya** qilish
  (`DocumentPanel` da shunday). S6+ frontend ishlarida shu naqsh saqlansin.
- **Chat API (frontend shu bilan ishlaydi, `lib/api.ts` orqali):**
  ```
  POST /chat                     {message, conversation_id?}
    -> {conversation_id, text, sources[], disclaimer}
  GET  /chat/conversations       -> [{id, user_id, title, created_at}]  (faqat o'ziniki)
  GET  /chat/conversations/{id}  -> yuqoridagi + messages[] + disclaimer
  ```
  `sources[]` elementi (`schemas.ChatSource`): `type` ("document" | "schedule"),
  `label` (tayyor sitata matni — chipga shu yoziladi), `document_id`, `title`,
  `heading`, `order_index`, `chunk_id` (oxirgi 5 tasi ixtiyoriy/None).
  `messages[]` elementi: `role` ("user"/"assistant"/"tool"), `content`,
  `tool_name` (faqat tool xabarida), `sources`, `created_at` — "qaysi vosita
  ishlatildi" ko'rsatkichi shundan olinadi. Hamma endpoint `Bearer` token
  talab qiladi; begona suhbat → **404** (mavjudligini ham oshkor qilmaydi).
  `conversation_id` berilmasa yangi suhbat ochiladi, sarlavhasi — birinchi
  xabarning 80 belgisi.
- **Disclaimer matni backenddan keladi** (`orchestrator.DISCLAIMER`) —
  frontend uni hardcode qilmasin. `POST /chat` javobida ham,
  `GET /chat/conversations/{id}` javobida ham `disclaimer` maydoni bor
  (S5 da qo'shildi, tarixdan qayta yuklangan javoblar ostida ham ko'rinsin).
- Mock rejimda javob matni `[mock] '<vosita>' vositasi natijasi asosida: …`
  ko'rinishida bo'ladi (deterministik). UI buni "chiroyli javob" deb emas,
  oqim tirikligi belgisi deb qabul qilsin — Gemini ulangach matn o'zgaradi,
  format (manbalar, disclaimer) o'zgarmaydi.
- **Qidiruv imzosi (`hujjat_qidir` tooli shuni chaqiradi):**
  ```python
  from app.rag.search import search, SearchResult
  results: list[SearchResult] = search(query: str, user: User, top_k: int = 5)
  ```
  `SearchResult` — dataclass: `document_id`, `title`, `text` (bo'lak matni),
  `order_index` (bo'lak tartibi), `score` (0..1, katta = yaxshi), `heading`
  (hujjat bo'limi/bo'limlari), `language`, `doc_type`, `access_level`,
  `chunk_id`. `.as_dict()` bor — tool javobini JSON qilish uchun.
  `user` — SQLAlchemy `User` obyekti (rol shundan olinadi), DB sessiyasi
  KERAK EMAS. Bo'sh so'rov yoki bo'sh indeks → `[]`.
- **Ruxsat filtri qidiruv ICHIDA** (Chroma metadata filtri), natijadan keyin
  emas: ko'rish huquqi yo'q bo'lak umuman skorlanmaydi va LLM ga bormaydi.
  Qoida: `public` hammaga, rol-darajali hujjat faqat o'sha rolga, admin —
  hammasi (`search.allowed_access_levels(user)`).
- RBAC faqat `app/auth/rbac.py` da: `get_current_user`, `require_role(*rollar)`
  (admin DOIM ruxsatli), doira helperlari `visible_group_ids(db, user)`
  (None = cheklovsiz/admin) va `can_access_user` / `ensure_can_access_user`
  (403 ko'taradi). Keyingi sessiyalar FAQAT shularni ishlatadi.
- RBAC namunasi: `GET /auth/test-staff-only` (`auth/router.py`) — doimiy
  qoladi, S2 testlari unga tayanadi.
- Testlar uchun `tests/conftest.py`: alohida `backend/test_app.db`
  (`DATABASE_URL` env orqali) va alohida `backend/test_chroma_data/`
  (`CHROMA_PATH` env orqali) — ikkisi ham app importidan OLDIN o'rnatiladi.
  Fixturelar: `seeded_db` (to'liq seed, autouse), `client` (TestClient),
  `db_session` (DB sessiyasi) va `indexed_corpus` (korpusni bir marta
  indekslaydi — embedding modelini yuklaydi, ~10 s).
- **Demo/reset ketma-ketligi ikki buyruq:** `python -m seed.generate --reset`
  (Chunk jadvalini ham tozalaydi) → `python -m seed.ingest_documents --reset`
  (Chroma kolleksiyasini qayta quradi). S13 dagi "demo reset" tugmasi
  IKKALASINI ham chaqirishi kerak.

## Sessiyalar holati

| № | Sessiya | Holat | Izoh |
|---|---|---|---|
| S0 | Loyiha skeleti + modellar | ✅ tugadi | DoD 4/4 o'tdi, commit "S0: project skeleton" |
| S1 | Demo ma'lumot generatori | ✅ tugadi | DoD 3/3 o'tdi, commit "S1: demo data generator and document corpus" |
| S2 | Auth + RBAC | ✅ tugadi | DoD 4/4 o'tdi, commit "S2: auth and RBAC" |
| S3 | RAG quvuri | ✅ tugadi | DoD 3/3 o'tdi, commit "S3: RAG pipeline with role-filtered search" |
| S4 | Agent yadrosi + tools | ✅ tugadi | DoD 3/3 o'tdi, commit "S4: agent core with tool calling" |
| S5 | Chat UI | ✅ tugadi | DoD 3/3 o'tdi (pytest 39/39, lint+build toza, 4 rolda brauzer tekshiruvi), commit "S5: chat UI and document panel" |
| S6 | Summarizatsiya | ✅ tugadi | DoD 3/3 o'tdi (pytest 54/54, lint+build toza, curl 3 rolda + brauzerda "Rezyume" tugmasi), commit "S6: role-aware document summarization" |
| S7 | Tarjima moduli | ⬜ boshlanmagan | |
| S8 | To'lovlar moduli | ⬜ boshlanmagan | |
| S9 | Davomat + mavjudlik (talaba) | ⬜ boshlanmagan | |
| S10 | O'qituvchilar davomati | ⬜ boshlanmagan | |
| S11 | Hujjat almashinuvi | ⬜ boshlanmagan | |
| S12 | Bildirishnomalar | ⬜ boshlanmagan | |
| S13 | Admin panel + reset | ⬜ boshlanmagan | |
| S14 | Integratsiya + taqdimot | ⬜ boshlanmagan | |

Holatlar: ⬜ boshlanmagan · 🔄 jarayonda · ✅ tugadi (DoD tekshirilgan)

## Qabul qilingan qarorlar

- **Orkestratsiya:** S3 dan boshlab sessiya-subagentlar **Opus** modelida
  ochiladi (foydalanuvchi ko'rsatmasi, 2026-08-14).
- **LLM provayder: Google Gemini** — API kalit loyiha oxirida ulanadi.
  Ungacha `LLM_PROVIDER=mock` rejimida quriladi va test qilinadi.
  `llm/client.py` Gemini tool calling formatiga mo'ljallanadi.
- **S0 versiyalar (o'rnatilgan, `pip freeze` dan):** Python 3.13.7 (.venv),
  fastapi 0.141.1, uvicorn 0.52.3, sqlalchemy 2.0.52, pydantic 2.13.4,
  pydantic-settings 2.15.0; Node 22.19.0, next 16.3.1, react 19.2.8,
  tailwindcss 4 (create-next-app skeleti).
- **S0 model qarorlari:**
  - Rollar enumi: `student / teacher / tutor / staff / admin`
    (`staff` = dekanat/registrar).
  - `User` ga `username` + `password_hash` qo'shildi (3.1 login/parol talabi;
    S2 shundan foydalanadi).
  - Alohida `Faculty` jadvali YO'Q (4-bo'lim ro'yxatida yo'q) — `faculty_id`
    oddiy int maydon.
  - `Chunk.embedding` o'rniga `embedding_id` (String) — vektorning o'zi S3 da
    Chroma'da saqlanadi, SQLite'da faqat havola.
  - Status enumlari: Payment `automatic/uploaded/confirmed`; ClassSession
    `held/cancelled/needs_clarification`; Flow
    `sent/seen/in_progress/approved/rejected`; Attendance
    `present/absent/late`; Turnstile yo'nalishi `in/out`.
- **LLM interfeysi (S4 shu bilan quriladi):** `llm/client.py` —
  `BaseLLMClient.chat(messages, tools, system) -> LLMResponse(text, tool_calls)`.
  Neytral formatlar: message = `{"role", "content", "tool_name", "tool_result"}`,
  tool = `{"name", "description", "parameters"(JSON Schema)}`. Mock provayder
  deterministik: `use_tool:<nom>:{...}` markeri yoki matnda tool nomi kelsa
  tool call qaytaradi. Gemini — skelet, `chat()` NotImplementedError.
- **Frontend:** `frontend/AGENTS.md` va `frontend/CLAUDE.md` ni `next dev`
  o'zi generatsiya qiladi (Next 16) — o'chirilmaydi, commitda turadi. Next 16
  API'si o'zgargan — frontend ishlashdan oldin `frontend/AGENTS.md` dagi
  yo'riqnomaga qaralsin. API bazaviy URL: `NEXT_PUBLIC_API_URL`
  (`frontend/.env.local`, default `http://localhost:8000`).
- **S1 demo qahramonlar (O'ZGARMAS — keyingi sessiyalar shunga tayanadi):**
  - Fakultetlar: `1` = Axborot texnologiyalari (AT), `2` = Iqtisodiyot (IQ).
    Guruhlar va "uy xonalari": AT-24-01 → 214, AT-24-02 → 215,
    IQ-24-01 → 310, IQ-24-02 → 311.
  - **aliyev** (Aliyev Jasur, talaba, AT-24-01): binoda (bugun 10:02 da
    kirgan, chiqmagan), bugungi barcha darslarida `present`, kontrakt TO'LIQ
    to'langan (qarz yo'q), bitta arizasi (ma'lumotnoma) `approved`.
  - **karimov** (Karimov Diyor, talaba, AT-24-01): QARZDOR (0 so'm to'lagan),
    bugun binoga kelmagan, o'tgan kunlarda davomati past.
  - **sodiqova** (Sodiqova Malika, talaba, AT-24-01): QISMAN to'lagan (50%),
    bugun 08:12 da kirib 13:15 da chiqib ketgan.
  - **mahmudov** (Mahmudov Aziz, talaba, AT-24-01): binoda (08:07 da kirgan),
    lekin bugungi 3-4-juftlik davomatida `absent` — S9 dagi
    "binoda + davomatda belgilanmagan" holati.
  - **tursunov** (Tursunov Akmal, o'qituvchi, fakultet 1): bugun jadvalda
    darslari bor (jumladan 3-juftlik: AT-24-02, "Kompyuter tarmoqlari",
    103-lab), binoga UMUMAN kirmagan — S10 "dars xavf ostida" ssenariysi.
    Uning bugungi ClassSession lari `needs_clarification`; dekanat
    (rashidova, yusupov) uchun `teacher_absence` bildirishnomasi yozilgan.
  - **sharipova** (Sharipova Gulnora, talaba, AT-24-02): kecha chek yuklagan —
    `Payment.status = uploaded`, tyutor tasdig'i kutilmoqda (S8 demo);
    nazarova uchun bildirishnoma bor.
  - Bugungi pin: AT-24-01 3-juftlik = "Ma'lumotlar bazasi", 214-xona, umarov
    (FUNKSIONALLIK 3.7 misoli bilan mos: "10:02 da kirgan, 214-xonada,
    davomatda belgilangan").
  - Demo loginlar: talaba `aliyev`/`karimov`/`sodiqova`; o'qituvchi `umarov`
    (darsda) / `tursunov` (kelmagan); tyutor `nazarova` (AT) / `qodirova`
    (IQ); dekanat `rashidova` (AT) / `yusupov` (IQ); admin `admin`.
- **S2 qarorlar (auth + RBAC):**
  - JWT: **pyjwt** (2.13), HS256, secret `.env` dagi `JWT_SECRET` (≥32 belgi),
    muddat `JWT_EXPIRES_MINUTES` (default 720). Payload: `sub` (user id),
    `role`, `exp`. Logout stateless — klient tokenni o'chiradi.
  - Parol xeshlash: **stdlib PBKDF2** (`hashlib.pbkdf2_hmac`, sha256,
    100 000 iteratsiya) — `app/auth/passwords.py`, tashqi kutubxona yo'q.
    Format: `pbkdf2_sha256$iter$salt$digest`.
  - **Hamma demo foydalanuvchi paroli: `demo123`** (seed bitta xeshni
    hammaga qo'yadi — tezlik uchun).
  - `require_role(*roles)` ro'yxatdagi rollarga + **har doim admin** ga
    ruxsat beradi (admin superuser). Doira helperlari: talaba → o'zi,
    o'qituvchi → o'zi dars beradigan guruhlar (Schedule orqali), tyutor →
    `Group.tutor_id` guruhlari, staff → o'z fakulteti, admin → hammasi.
  - Frontend: token `localStorage` (`uniagent_token`), `lib/api.ts` har
    so'rovga `Authorization: Bearer` qo'shadi, 401 da tokenni o'chirib
    `/login` ga qaytaradi (login so'rovining o'zidan tashqari). Auth
    konteksti `src/lib/auth.tsx` (`AuthProvider`/`useAuth`), himoyalangan
    sahifalar `src/app/(protected)/` route-guruhida (client-side guard +
    header: ism, rol, chiqish). Login: `/login`, 5 ta demo tugma.
  - Backend testlarga `pytest`, `httpx` qo'shildi (`requirements.txt`).
- **S3 qarorlar (RAG quvuri):**
  - **Embedding modeli: `intfloat/multilingual-e5-small`** (lokal
    sentence-transformers, kalitsiz, 384 o'lchov, 512 tokenlik oyna, ~450 MB).
    Tanlov o'lchab qilingan (seed korpusi, 24 ta savol, top-1):
    `paraphrase-multilingual-MiniLM-L12-v2` RAD ETILDI — uning 50 tilli
    distillyatsiya ro'yxatida **o'zbek tili yo'q**; `multilingual-e5-base`
    (1.1 GB) sinovda e5-small dan **yaxshi chiqmadi** (ikkalasi ham 19/24),
    lekin 3 barobar sekin — shuning uchun small.
  - **Model FAQAT `app/rag/embeddings.py` orqali** (CLAUDE.md qoidasi).
    Sozlamalar `config.py` da: `EMBEDDING_MODEL`, `EMBEDDING_QUERY_PREFIX`
    (`"query: "`), `EMBEDDING_PASSAGE_PREFIX` (`"passage: "`) — e5 oilasi shu
    prefikslarni talab qiladi; boshqa model qo'yilsa ularni bo'sh qilish kerak.
  - **Markazlashtirish (mean centering), `EMBEDDING_CENTER=true`** — S3 ning
    eng muhim topilmasi. Ko'p tilli fazo anizotrop: hamma o'xshashlik
    0.79-0.87 oralig'ida siqilgan va qolgan farqni **til** belgilaydi, ma'no
    emas. Natijada "mashinaviy o'qitish nima?" savoli inglizcha ML hujjatini
    **12-o'ringa** tushirgan (oldida — mavzuga aloqasiz o'zbekcha hujjatlar).
    Korpus o'rtacha vektorini ayirish buni yo'qotadi: top-1 12/16 → 15/16.
    O'rtacha vektor to'liq qayta indekslashda hisoblanadi va
    `chroma_data/embedding_bias.json` da saqlanadi; savol ham shu vektor bilan
    markazlashtiriladi. Fayl bo'lmasa — oddiy (markazlashtirilmagan) rejim.
  - **Gibrid reyting:** vektor qidiruvi nomzodlar hovuzini beradi
    (`top_k*4`, kamida 20), keyin ular IDF-vaznli kalit so'z mosligi bilan
    qayta tartiblanadi: `0.7*kosinus + 0.3*leksik`
    (`SEARCH_LEXICAL_WEIGHT`). Kosinus **min-max normallashtirilmaydi** —
    aks holda eng yaxshi nomzod zaif bo'lsa ham 1.0 ga cho'ziladi va mavzuga
    aloqasiz hujjat yutib ketadi. O'lchov (talaba ko'rinishi, 23 savol,
    top-1): 15/23 oddiy → 18/23 markazlashtirilgan → **20/23 gibrid**.
  - **Bo'laklash:** paragraf chegaralarini buzmaydi, markdown sarlavhalarini
    kuzatadi; maqsad ~1600 belgi, qattiq chegara 2200 (`CHUNK_TARGET_CHARS`,
    `CHUNK_MAX_CHARS`) — bu ~260 median token, model oynasi 512 dan past,
    ya'ni **hech narsa kesilmaydi**. Embeddingga beriladigan matn oldiga
    hujjat nomi + bo'lim sarlavhasi qo'shiladi (qisqa bo'lak — masalan
    juftliklar jadvali — kontekstsiz ma'nosiz). Bo'lak bir nechta bo'limni
    qamrasa, `heading` ularning HAMMASINI " · " bilan ko'rsatadi (manba
    ko'rsatish qoidasi buzilmasin). Seed korpusi: 10 hujjat → 28 bo'lak.
  - **Chroma:** `chromadb` 1.5.9, `PersistentClient`,
    kolleksiya `uniagent_documents`, `metadata={"hnsw:space": "cosine"}`,
    `embedding_function=None` (vektorni doim o'zimiz beramiz). Papka
    `backend/chroma_data/` (`CHROMA_PATH`, gitignore da). Metadata:
    `document_id`, `chunk_id`, `title`, `doc_type`, `language`,
    `access_level`, `order_index`, `heading`. Chroma id formati
    `doc{document_id}_c{order_index}` — u `Chunk.embedding_id` ga yoziladi.
  - **Fayllar:** `app/rag/embeddings.py` (yagona embedding nuqtasi),
    `store.py` (yagona chromadb nuqtasi), `ingest.py` (matn → bo'lak →
    vektor → Chroma + `Chunk`), `search.py` (rol filtri + gibrid reyting),
    `seed/ingest_documents.py` (CLI). `seed/generate.py` O'ZGARMADI.
  - **Kutubxonalar:** torch **CPU g'ildiragi** (`--index-url
    https://download.pytorch.org/whl/cpu`, 122 MB; PyPI dagi oddiy g'ildirak
    CUDA bilan ~10 barobar katta), `sentence-transformers` 5.7,
    `chromadb` 1.5.9 — `requirements.txt` da izoh bilan.
- **S4 qarorlar (agent yadrosi + tool calling):**
  - **Tool registri (`app/agents/registry.py`):** `Tool(name, description,
    parameters(JSON Schema), handler, roles)` + `ToolResult(text, sources, ok)`.
    `execute_tool(name, args, db, user)` — **ruxsat shu yerda tekshiriladi**:
    rol mos kelmasa handler CHAQIRILMAYDI, `ToolResult(ok=False, "Ruxsat
    yo'q…")` qaytadi (exception EMAS — agent oqimi davom etadi va model rad
    javobini tushuntiradi). Noma'lum vosita va handler ichidagi xatolik ham
    shu tarzda `ok=False` natijaga aylanadi. `roles` ro'yxatiga qo'shimcha
    ravishda **admin har doim ruxsatli** (rbac dagi `require_role` bilan bir xil
    qoida). `tools_for_role(role)` — LLM ga beriladigan deklaratsiyalar.
    Yangi tool qo'shish: `agents/tools/` ga fayl + o'sha faylda `register(...)`;
    `agents/tools/__init__.py` ga bitta import qatori. Boshqa hech narsa.
  - **S4 dagi 3 vosita — uchalasi ham hamma rolga ochiq**, chunki cheklov
    ma'lumot qatlamida: `hujjat_qidir` (rol filtri `rag.search` ichida),
    `jadval_kor` (`rbac.visible_group_ids` doirasi; o'qituvchi — faqat
    `Schedule.teacher_id == user.id`; doiradan tashqari guruh so'ralsa
    "Ruxsat yo'q" natijasi), `hujjat_rezyume` (`access_level` tekshiruvi
    `rag.search.allowed_access_levels` bilan; **nom bo'yicha qidiruvda**
    ko'rinmaydigan hujjat umuman topilmaydi — mavjudligi ham oshkor bo'lmaydi,
    id bo'yicha so'ralsa ochiq "ruxsat yo'q"). Rol-cheklangan vositalar
    S8-S11 da qo'shiladi (`tolov_holati`, `mavjudlik_tekshir`, …).
  - **Tizim promptlari (`app/agents/prompts/`):** `umumiy.md` (6 ta buzilmas
    qoida: faqat tool natijasiga tayanish, manba ko'rsatish, ruxsat chegarasi,
    "rasmiy hujjat emas", "mavjudlik = xulosa", qisqalik) + rol fayli
    (`student.md`, `teacher.md`, `tutor.md`, `staff.md`, `admin.md`).
    `orchestrator.load_system_prompt(role)` ikkalasini birlashtiradi
    (`lru_cache`) — ya'ni majburiy qoidalar bitta joyda, rol fayli faqat ohang
    va rakursni belgilaydi.
  - **Orkestrator (`app/agents/orchestrator.py`):** tarix (oxirgi 20 ta
    user/assistant xabari) → rol prompti → `llm.chat(messages, tools, system)`
    → tool_calls bo'lsa `execute_tool` → natija xabarlar ro'yxatiga qo'shiladi
    va model qayta chaqiriladi → birinchi matnli javobda to'xtaydi,
    **max 5 iteratsiya** (tugasa oxirgi tool natijasidan fallback javob).
    Manbalar iteratsiyalar bo'ylab yig'iladi va dublikatlari olib tashlanadi.
  - **Yangi modellar (ataylab qilingan kengaytma, ISH_REJA S4 "suhbat DB da
    saqlanadi" talabi):** `Conversation` (id, user_id, title, created_at) va
    `ChatMessage` (id, conversation_id, role: user/assistant/**tool**, content,
    tool_name, sources JSON, created_at). Tool xabarlari **audit izi** sifatida
    saqlanadi (qaysi vosita, nima qaytardi), lekin modelga tarix sifatida
    QAYTA berilmaydi — faqat user/assistant almashinuvi beriladi (kontekst toza
    va deterministik qolsin). `seed/generate.py` dagi `ALL_MODELS` ro'yxatiga
    ikkala jadval qo'shildi, aks holda demo reset eski suhbatlarni qoldirardi.
  - **Chat API (`app/api/chat.py`):** router yupqa — butun oqim orkestratorda.
    Begona suhbat uchun **404** (403 emas): boshqa foydalanuvchi suhbatining
    mavjudligini ham bilib bo'lmasin.
  - **Mock provayder kengaytmasi (`llm/client.py`, deterministik qoldi):**
    tool tanlash tartibi — (1) `use_tool:<nom>:{...}` markeri, (2) xabarda
    tool nomi uchrasa o'sha, (3) aks holda `hujjat_qidir(query=<xabar>)`.
    **Transkriptda tool natijasi paydo bo'lgach mock BOSHQA tool chaqirmaydi**
    — shuning uchun sikl har doim tugaydi (bitta tool aylanmasi). Yakuniy matn
    FAQAT tool natijasidan yasaladi (foydalanuvchi savolini qaytarib aytmaydi —
    "javob" ichida o'ylab topilgan fakt bo'lmasligi kafolatlanadi).
    Shu bilan Gemini kalitisiz ham butun oqim (qidiruv → manba → javob) jonli
    ishlaydi; aniq vosita kerak bo'lsa marker ishlatiladi:
    `use_tool:hujjat_rezyume:{"nom": "91-M"}`.
- **S5 qarorlar (chat UI + hujjat paneli):**
  - **Hujjatlar API rol filtrini QAYTA yozmaydi** — `app/services/documents.py`
    `rag.search.allowed_access_levels(user)` ni chaqiradi. Ya'ni qidiruvda
    ko'rinmaydigan hujjat ro'yxatda ham, ko'ruvchida ham ko'rinmaydi (bitta
    qoida, bitta joy). Ko'rish huquqi yo'q hujjat → **404**, 403 emas
    (chat API dagi begona suhbat qoidasi bilan bir xil).
  - **`services/documents.py` qo'shildi** (CLAUDE.md dagi ro'yxatda yo'q edi):
    routerlar yupqa bo'lsin degan arxitektura qoidasiga amal qilingan; S6
    rezyume tugmasi ham shu servisdan foydalanadi.
  - **`ConversationDetailOut` ga `disclaimer` maydoni qo'shildi** (default —
    `orchestrator.DISCLAIMER`, `api/chat.py` O'ZGARMADI). Sabab: domen
    qoidasi 3 ga ko'ra tarixdan qayta yuklangan javob ostida ham ogohlantirish
    turishi kerak, frontend esa matnni hardcode qilmasligi kerak.
  - **Marshrutlar:** `/` → `/chat` ga yo'naltiradi (kirgandan keyin darhol
    chat); `(protected)/chat` — chat ish maydoni, `(protected)/documents` —
    hujjatlar sahifasi. `(protected)/layout.tsx` ga navigatsiya qo'shildi va
    balandlik `h-screen overflow-hidden` ga o'tkazildi (har sahifa o'z
    ustunini o'zi skroll qiladi).
  - **Layout rolga qarab:** chat markazda (hamma rol), o'ngdagi panel —
    ochilgan hujjat, hujjat ochilmagan bo'lsa `RoleDashboard` (bo'sh
    placeholder) faqat teacher/tutor/staff/admin uchun. Panel `lg:` dan
    kichik ekranda yashiriladi.
  - **Markdown renderer o'zimizniki** (`components/Markdown.tsx`, ~200 qator,
    sarlavha/jadval/ro'yxat/kod/bold): korpus kichik, tashqi markdown
    kutubxonasi bundle'dagi eng og'ir narsa bo'lib qolardi.
  - **Vosita badge'i** (`hujjat_qidir` va h.k.) `role="tool"` xabarlaridan
    olinadi: `POST /chat` javobida vosita nomi yo'q, shuning uchun javob
    kelgandan keyin `GET /chat/conversations/{id}` fonda qayta o'qiladi
    (muvaffaqiyatsiz bo'lsa javob baribir ekranda qoladi).
  - **UI matnlari faqat `src/i18n/uz.json` da** (`nav`, `chat`, `documents`,
    `dashboard`, `common` bo'limlari qo'shildi); enum yorliqlari
    `src/lib/labels.ts` orqali.
  - **Jonli tekshiruv retsepti (keyingi sessiyalar uchun):** CORS faqat
    `http://localhost:3000` ga ochiq va `NEXT_PUBLIC_API_URL` build paytida
    qotadi — shuning uchun brauzer tekshiruvi backend **8000**, frontend
    **3000** portida o'tkaziladi. Brauzer sinovi Chrome'ni
    `--headless=new --remote-debugging-port=9222` bilan ishga tushirib, Node
    22 ning ichki `WebSocket` i orqali CDP bilan qilindi (npm paketi
    o'rnatilmadi); viewport 1440x900 qilinmasa `lg:` paneli yashirin qoladi.
- **S6 qarorlar (summarizatsiya):**
  - **Yagona kod yo'li: `app/services/summarization.py`.** `hujjat_rezyume`
    tooli ham, `POST /documents/{id}/summary` ham AYNAN shu servisni
    chaqiradi (`summarize_document(db, document, user)`), dublikat yo'q.
    Tool endi faqat "qaysi hujjat" savolini hal qiladi va natijani
    `ToolResult` ga o'raydi; matn o'qish `services/documents.document_text`,
    nom bo'yicha qidiruv esa yangi `find_visible_document_by_title` orqali —
    ya'ni ruxsat qoidasi (`rag.search.allowed_access_levels`) hamon bitta
    joyda. Tooldagi eski nusxalar (`_visible_documents`, `_document_text`)
    olib tashlandi.
  - **Rol rakursi ikki qatlamda:** `ROLE_FOCUS` (qisqa ibora, S4 dan meros)
    + yangi `ROLE_POINTS` (har rol uchun 3 ta aniq savol: talaba — "mendan
    nima talab qilinadi / qachongacha / oqibati", dekanat — "raqam va sana /
    ijrochilar / muddatlar", o'qituvchi — "asosiy bandlar / o'quv jarayoniga
    ta'siri / undan talab qilinadigan ish" va h.k.). Ikkalasi HAM tizim
    promptiga (`system_prompt(role)`), HAM foydalanuvchi promptiga
    (`build_summary_prompt`/`build_part_prompt`/`build_reduce_prompt`) kiradi
    — provayder tizim promptini qanchalik hisobga olishidan qat'i nazar
    rakurs yo'qolmaydi. 5 rolning 5 ta har xil rakursi bor (test bilan
    qotirilgan).
  - **Map-reduce, `PART_CHARS = 4000` (`MAX_PARTS = 12`):** matn shu
    chegaradan uzun bo'lsa paragraf chegaralari bo'yicha bo'linadi
    (`split_parts`), har bo'lakka bitta "oraliq qayd" chaqiruvi (map), so'ng
    bitta birlashtiruvchi chaqiruv (reduce) — jami `parts + 1` chaqiruv;
    qisqa hujjatda bitta chaqiruv. 4000 model chegarasi emas, sifat/tezlik
    byudjeti: 6000 da demo korpusining BIRORTA hujjati map-reduce'ga
    tushmasdi (eng uzuni 4858 belgi — ruscha fayl 6793 BAYT, lekin kirill
    2 baytdan, ya'ni ~3.8k belgi). 4000 da syllabus/nizom/ML hujjatlari
    2 bo'lakka bo'linadi, 2 sahifalik buyruq esa bitta chaqiruvda qoladi —
    ikkala yo'l ham demoda jonli ko'rinadi. `MAX_PARTS` dan oshsa
    `truncated=True` va javobda ogohlantirish qatori chiqadi.
  - **Endpoint `POST /documents/{id}/summary`** (GET emas: LLM chaqiruvi —
    qimmat, keshlanmaydigan amal). Javob `schemas.DocumentSummaryOut`:
    `document_id, title, summary, parts, truncated, source (ChatSource),
    disclaimer`. Manba va disclaimer MAJBURIY maydon — rezyume ham faktik
    javob (domen qoidalari 3 va 5). Ruxsati yo'q hujjat → **404** (viewer
    bilan bir xil), matni bo'sh hujjat → 422.
  - **Mock provayder kengaytmasi (`llm/client.py`, ataylab minimal):**
    `tools` berilmagan chaqiruvda (rezyume shunday chaqiradi) javob endi
    `[mock:<digest>] Echo: <promptning ilk 600 belgisi> […]` — oldin butun
    prompt qaytarardi, ya'ni "rezyume" hujjatning o'zidan uzun bo'lardi.
    Digest hamon TO'LIQ matndan olinadi, shuning uchun deterministiklik va
    kirishga bog'liqlik saqlanadi; tool natijasidan javob yasash yo'li
    o'zgarmadi (endi u ham shu `_clip()` yordamchisini ishlatadi). Yoqimli
    yon ta'sir: mock rejimda ham rezyume matnining boshida rol rakursi
    ko'rinadi — 3 rolda farqni ko'z bilan tekshirish mumkin.
  - **Frontend:** "Rezyume" tugmasi `DocumentPanel` header'idagi amal
    tugmalari qatorida; natija hujjat matni TEPASIDA alohida `<section>`
    blokida (manba + disclaimer + "Yopish"), original matn hech qachon
    almashtirilmaydi. Holat S5 naqshi bilan — id bo'yicha derivatsiya
    (`summary.id === documentId`), `setState` faqat hodisa ishlovchisida va
    `.then()/.catch()` ichida (Next 16 `react-hooks/set-state-in-effect`).
- **S1 texnik qarorlar:**
  - Juftlik vaqtlari (`seed/generate.py` dagi `PAIR_TIMES`, ichki tartib
    nizomi 3.1-band bilan bir xil): 1) 08:30-09:50, 2) 10:00-11:20,
    3) 11:30-12:50, 4) 13:30-14:50, 5) 15:00-16:20, 6) 16:30-17:50.
    S9/S10 presence servisi shu vaqtlarni ishlatsin (umumiy konstantaga
    ko'chirish mumkin).
  - Jadval Dush-Shan (weekday 0-5), 1-4-juftlik (shanba 1-3), deterministik
    rotatsiya — o'qituvchi/xona to'qnashuvlari yo'q (SQL bilan tekshirilgan).
    Aliyev guruhining bugungi jadvali 2-juftlikdan boshlanadi (10:02 da
    kirgani bilan zid kelmasligi uchun).
  - Turniket loglari faqat "bugun" (skript ishga tushgan kun) uchun
    yaratiladi; bugungi davomat kunning HAMMA juftliklari uchun oldindan,
    turniket loglaridan hisoblab yoziladi — demo istalgan soatda ishlaydi.
    (Ertalab ishga tushirilsa ba'zi loglar/davomat "kelajakda" bo'ladi —
    demo uchun qabul qilingan soddalashtirish.)
  - Topshiriq deadlinelari nisbiy (bugun +4/+7/+11/+18 kun, 23:59) — hujjat
    matnlarida qat'iy sana YO'Q ("e'lon qilingan kundan N kun" deyilgan),
    shuning uchun DB va hujjat zid kelmaydi; S12 deadline triggerlari har
    resetdan keyin ham ishlayveradi.
  - Hujjat kirish darajalari: hammasi `public`, faqat "Buyruq 91-M
    (attestatsiya)" — `staff` (demo ssenariyda talabaga rad etiladi).
    `Document.file_path` — backend/ ga nisbatan yo'l (`seed/documents/...`).
  - Kontrakt summalari: fakultet 1 → 12 000 000, fakultet 2 → 10 500 000
    so'm; to'liq to'lov sxemasi 40/30/30 (nizom 5.1-band bilan mos).
  - Chek raqamlari: `CLK-...` (avtomatik, sintetik Click), `CHK-...`
    (qo'lda yuklangan). `Payment.receipt_file` — faqat yo'l-platzholder
    (`uploads/receipts/...`), haqiqiy fayl yo'q.

## Keyinga qoldirilganlar

- **Kichik ekran (mobil) layouti:** hujjat paneli va dashboard `lg:` dan
  kichik ekranda yashiringan — telefonda manba chipini bosish ko'zga
  ko'rinadigan natija bermaydi. S14 (sayqal) da modal/drawer qilinsin.
- **`type: "schedule"` manba chipi bosilmaydi** (ochadigan ko'rinish yo'q).
  S9/S10 jadval/davomat sahifasini qo'shganda shu chip ham havolaga
  aylantirilsin.
- Suhbatni o'chirish/nomini o'zgartirish YO'Q (faqat ro'yxat + yangi suhbat).
  Kerak bo'lsa S13 (admin) yoki S14 da qo'shiladi.
- `schemas.DocumentOut` va `ChunkOut` (S0 dan qolgan) hech qayerda
  ishlatilmaydi — S5 o'z sxemalarini qo'shdi (`DocumentListItemOut`,
  `DocumentDetailOut`). Kerak bo'lmasa S14 da tozalansin.
- **Juftlik vaqtlari ikki joyda:** `seed/generate.py` dagi `PAIR_TIMES` va
  `app/agents/tools/schedule_view.py` dagi `PAIR_TIMES` — bir xil jadval.
  S9 (mavjudlik servisi) uchinchi nusxa yasamasin: o'sha sessiyada umumiy
  konstantaga (masalan `app/services/presence.py` yoki `app/config.py`)
  ko'chirilsin.
- **Rezyume keshlanmaydi** — bitta hujjatga har bosishda LLM qayta
  chaqiriladi (rol bo'yicha farq qilgani uchun kesh kaliti
  `(document_id, role)` bo'lishi kerak). S7 da `Translation` keshi
  yozilgandan keyin xuddi shu naqshni rezyumega ham qo'llash mumkin
  (yoki S14 da) — hozircha demo tezligi yetarli.
- **Rezyume sifati Gemini bilan tekshirilmagan:** ISH_REJA S6 DoD dagi
  "2 sahifalik buyruq 5-6 qatorli aniq rezyumega tushadi" bandi mock
  rejimda o'lchab bo'lmaydi (matn — deterministik echo). S14 da kalit
  ulangach 3 rolda qayta ko'rilsin; kerak bo'lsa `SYSTEM_BASE` va
  `ROLE_POINTS` matnlari o'sha yerda sozlanadi.
- **`_document_text` mantiqi ikki joyda emas, lekin `extract_text` faqat
  `.md/.txt` ni biladi** — S13 da PDF/DOCX qo'shilsa rezyume ham avtomatik
  ishlaydi (u `services/documents.document_text` ga tayanadi).
- Gemini provayderi hali `NotImplementedError` — kalit ulangach
  `GeminiLLMClient.chat()` yozilishi kerak (neytral message/tool formatini
  google-genai formatiga o'girish). Butun tizim shu bitta metodga bog'liq.
- Chek rasm fayllari (`Payment.receipt_file` ko'rsatgan yo'llar) mavjud emas —
  S8 da chek ko'rish UI uchun demo rasm/placeholder hal qilinadi.
- Qidiruv sifati: 24 savollik o'lchovda 4-5 tasi hali ham xato hujjatni
  birinchi qo'yadi (masalan "birlamchi kalit va tashqi kalit" → ruscha hujjat
  o'rniga inglizcha ML hujjati; savolda ruscha atama bilan hech qanday
  leksik moslik yo'q). Sabab — 118M parametrli kichik modelning chegarasi.
  Agar S14 da vaqt bo'lsa: kattaroq model (`bge-m3`, `LaBSE`) yoki
  savolni LLM bilan inglizcha/ruschaga kengaytirish (query expansion)
  sinab ko'rilsin. MVP uchun hozirgi sifat yetarli (talaba ko'rinishida
  top-1 20/23, top-3 21/23).
- `Document.language` maydoni ingest da metadata sifatida yoziladi, lekin
  til bo'yicha FILTR hali qo'llanilmaydi (tillar aro qidiruv shart) — S7
  tarjima moduli kerak bo'lsa shu metadatadan foydalanadi.
- Faqat `.md`/`.txt` fayllar indekslanadi (`app/rag/ingest.py`
  `SUPPORTED_SUFFIXES`) — S13 da PDF/DOCX yuklash kerak bo'lsa,
  `extract_text()` kengaytiriladi.

## Ochiq savollar

`FUNKSIONALLIK_LOGIKA.md` 9-bo'limga qarang — javoblar shu yerga ko'chiriladi.
