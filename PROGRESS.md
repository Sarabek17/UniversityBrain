# PROGRESS — joriy holat

> Har sessiya oxirida yangilanadi. Yangi sessiya SHU FAYLDAN boshlanadi.

## Joriy sessiya: S3 (navbatda)

S2 yakunlandi (DoD 4/4: pytest 12/12 o'tdi; 5 rol curl bilan login +
`/auth/me` jonli tekshirildi; brauzerda login → header'da ism/rol → chiqish
ishladi (headless Chrome smoke, konsolda xato yo'q); talaba tokeni bilan
`/auth/test-staff-only` curl'da 403 qaytardi). S3 uchun izohlar:

- RBAC faqat `app/auth/rbac.py` da: `get_current_user`, `require_role(*rollar)`
  (admin DOIM ruxsatli), doira helperlari `visible_group_ids(db, user)`
  (None = cheklovsiz/admin) va `can_access_user` / `ensure_can_access_user`
  (403 ko'taradi). Keyingi sessiyalar FAQAT shularni ishlatadi.
- RBAC namunasi: `GET /auth/test-staff-only` (`auth/router.py`) — doimiy
  qoladi, S2 testlari unga tayanadi.
- S3 qidiruv filtri: `Document.access_level` bo'yicha — `public` hammaga,
  rol-darajali hujjat faqat o'sha rolga (admin hammasini ko'radi). Seedda
  yagona maxfiy hujjat: "Buyruq 91-M" (`staff`).
- Testlar uchun `tests/conftest.py` bor: alohida `backend/test_app.db`
  (`DATABASE_URL` env orqali, app importidan OLDIN o'rnatiladi), session-scoped
  `seeded_db` (to'liq seed) va `client` (TestClient) fixturelari — S3 testlari
  shu fixturelarni qayta ishlatsin.
- Seed hujjatlari hali indekslanmagan (Chunk=0) — S3 ingest seed jarayoniga
  ulanadi (`seed/generate.py` dan chaqirish yoki alohida buyruq).

## Sessiyalar holati

| № | Sessiya | Holat | Izoh |
|---|---|---|---|
| S0 | Loyiha skeleti + modellar | ✅ tugadi | DoD 4/4 o'tdi, commit "S0: project skeleton" |
| S1 | Demo ma'lumot generatori | ✅ tugadi | DoD 3/3 o'tdi, commit "S1: demo data generator and document corpus" |
| S2 | Auth + RBAC | ✅ tugadi | DoD 4/4 o'tdi, commit "S2: auth and RBAC" |
| S3 | RAG quvuri | ⬜ boshlanmagan | |
| S4 | Agent yadrosi + tools | ⬜ boshlanmagan | |
| S5 | Chat UI | ⬜ boshlanmagan | |
| S6 | Summarizatsiya | ⬜ boshlanmagan | |
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

- Chek rasm fayllari (`Payment.receipt_file` ko'rsatgan yo'llar) mavjud emas —
  S8 da chek ko'rish UI uchun demo rasm/placeholder hal qilinadi.
- Seed hujjatlari hali indekslanmagan (Chunk=0) — S3 ingest seed jarayoniga
  ulanadi.

## Ochiq savollar

`FUNKSIONALLIK_LOGIKA.md` 9-bo'limga qarang — javoblar shu yerga ko'chiriladi.
