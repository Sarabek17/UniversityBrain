# PROGRESS — joriy holat

> Har sessiya oxirida yangilanadi. Yangi sessiya SHU FAYLDAN boshlanadi.

## Joriy sessiya: S1 (navbatda)

S0 yakunlandi (DoD to'liq tekshirildi, commit: "S0: project skeleton").
Navbatdagi ish — S1: demo ma'lumot generatori (`backend/seed/generate.py` +
`backend/seed/documents/` korpusi). S1 uchun izohlar:

- Modellar va enumlar `backend/app/models.py` da tayyor — seed yozishdan oldin
  o'qib chiqilsin (maydon nomlari inglizcha: `full_name`, `paid_at`,
  `receipt_number`, `pair_number`, `weekday` 0=Dushanba, ...).
- `User` da `username` (unique) va `password_hash` maydonlari bor — seed
  foydalanuvchilarga username berilsin, parol xeshlash S2 da hal bo'ladi
  (hozircha `password_hash` ga oddiy belgi qo'yish mumkin, S2 almashtiradi).
- DB jadvallari `app.db.init_db()` (`Base.metadata.create_all`) bilan
  yaratiladi — uvicorn startupda avtomatik chaqiriladi; seed skript ham
  boshida `init_db()` ni chaqirsin.
- `Group.faculty_id` / `User.faculty_id` — oddiy int (alohida Faculty jadvali
  yo'q, 15 obyekt ro'yxatida bo'lmagani uchun). Seed 1 va 2 raqamlarini
  ishlatsin.
- Demo ssenariy qahramonlari shu sessiyada qat'iy belgilanib pastdagi
  "Qabul qilingan qarorlar"ga yozilsin.

## Sessiyalar holati

| № | Sessiya | Holat | Izoh |
|---|---|---|---|
| S0 | Loyiha skeleti + modellar | ✅ tugadi | DoD 4/4 o'tdi, commit "S0: project skeleton" |
| S1 | Demo ma'lumot generatori | ⬜ boshlanmagan | |
| S2 | Auth + RBAC | ⬜ boshlanmagan | |
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
- (S1 da to'ldiriladi) Demo ssenariy qahramonlari: ...

## Keyinga qoldirilganlar

- (bo'sh)

## Ochiq savollar

`FUNKSIONALLIK_LOGIKA.md` 9-bo'limga qarang — javoblar shu yerga ko'chiriladi.
