# UniAgent — NEXUS30 EdTech loyihasi

Universitet uchun rol-asosli AI agentlar ekotizimi (NEXUS30 hackathoni,
EdTech treki, hamkor: Yandex). Rol-asosli RAG + tool calling: talaba,
o'qituvchi, tyutor, dekanat va admin o'z doirasidagi ma'lumotlar bilan
AI agent orqali ishlaydi.

## Asosiy hujjatlar

- `FUNKSIONALLIK_LOGIKA.md` — nima qurilishi kerak (modullar, logika, ma'lumotlar
  modeli). Funksionallik bo'yicha yagona haqiqat manbasi.
- `ISH_REJA.md` — qanday qurilishi kerak (S0–S14 sessiyalar, har birining DoD
  va tekshiruvi).
- `PROGRESS.md` — hozir qayerdamiz (sessiyalar holati, qabul qilingan qarorlar).

## Sessiya protokoli (majburiy)

1. Ishni boshlashdan oldin `PROGRESS.md` ni o'qi — joriy sessiya va oldingi
   sessiyadan qolgan izohlar shu yerda.
2. `ISH_REJA.md` dan faqat joriy sessiya bo'limini, `FUNKSIONALLIK_LOGIKA.md`
   dan faqat tegishli modul bo'limini o'qi.
3. Faqat joriy sessiya doirasida ishla. Boshqa modul kodini import qilish
   mumkin, o'zgartirish mumkin emas. Doiradan tashqari muammo topilsa —
   tuzatmasdan `PROGRESS.md` ning "Keyinga qoldirilgan" bo'limiga yozib qo'y.
4. Sessiya oxirida: sessiyaning tekshirish buyruqlarini ishga tushir,
   `PROGRESS.md` ni yangila (qilingan ish, qarorlar, qolganlar).

## Gallyutsinatsiyaga qarshi qoidalar

- Funksiya/endpoint/model/maydon nomini taxmin qilma — avval Read/Grep bilan
  haqiqiy koddan tekshir, keyin ishlat.
- API sxemalari `backend/app/schemas.py` da — javob formatini o'ylab topma.
- Har yangi endpoint yozilgach darhol curl yoki pytest bilan tekshiriladi.
- Kutubxona APIsiga ishonch bo'lmasa — kichik sinov skripti bilan tekshir,
  taxmin bilan yozma.

## Til qoidalari

- Foydalanuvchi bilan muloqot: **o'zbek tilida**.
- Kod, identifikatorlar, commit xabarlari: **ingliz tilida**.
- UI matnlari: o'zbek tilida (i18n fayllar orqali, hardcode qilinmaydi).
- Kod izohlari: minimal, faqat noaniq joylarga, ingliz tilida.

## Texnologiyalar

- Backend: Python 3.11+, FastAPI, SQLAlchemy, SQLite (`backend/app.db`)
- Vektor baza: Chroma (lokal, `backend/chroma_data/`)
- Frontend: Next.js (App Router), TypeScript, Tailwind CSS
- LLM: provayderdan mustaqil klient (`backend/app/llm/client.py`) —
  provayder `.env` dagi `LLM_PROVIDER` bilan tanlanadi. LLM chaqiruvi FAQAT
  shu modul orqali; boshqa joydan to'g'ridan-to'g'ri provayder SDK chaqirilmaydi.
  **Tanlangan provayder: Google Gemini** (`LLM_PROVIDER=gemini`, kalit loyiha
  oxirida ulanadi). Ungacha ishlab chiqish va testlar `LLM_PROVIDER=mock`
  rejimida boradi — mock provayder deterministik javob qaytaradi.
- Embedding: ko'p tilli model, `backend/app/rag/embeddings.py` orqali (xuddi
  shunday — faqat shu modul orqali).

## Fayl arxitekturasi

```
Universitet/
├── CLAUDE.md                    # shu fayl
├── FUNKSIONALLIK_LOGIKA.md      # funksional spetsifikatsiya
├── ISH_REJA.md                  # sessiyalar rejasi
├── PROGRESS.md                  # joriy holat (har sessiyada yangilanadi)
├── NEXUS30_...docx              # hackathon rasmiy keyslar hujjati
├── backend/
│   ├── requirements.txt
│   ├── .env.example             # LLM_PROVIDER, API kalitlar, DB yo'li
│   ├── app/
│   │   ├── main.py              # FastAPI ilova, routerlar ulanishi
│   │   ├── config.py            # .env o'qish, sozlamalar
│   │   ├── db.py                # engine, session
│   │   ├── models.py            # BARCHA SQLAlchemy modellari (bitta fayl)
│   │   ├── schemas.py           # BARCHA Pydantic sxemalari (bitta fayl)
│   │   ├── auth/                # S2: login, JWT/sessiya, RBAC dependency
│   │   │   ├── router.py
│   │   │   └── rbac.py          # require_role + doira filtri — YAGONA joy
│   │   ├── llm/
│   │   │   └── client.py        # provayderdan mustaqil LLM interfeysi
│   │   ├── rag/                 # S3: ingest, chunking, qidiruv
│   │   │   ├── ingest.py
│   │   │   ├── embeddings.py
│   │   │   └── search.py
│   │   ├── agents/              # S4: agent yadrosi
│   │   │   ├── orchestrator.py  # chat oqimi, tool loop
│   │   │   ├── registry.py      # tool registri (nom+sxema+handler+ruxsat)
│   │   │   ├── tools/           # har tool alohida fayl
│   │   │   └── prompts/         # rol bo'yicha tizim promptlari (5 fayl)
│   │   ├── services/            # biznes logika (routerlardan ajratilgan)
│   │   │   ├── translation.py   # S7
│   │   │   ├── payments.py      # S8
│   │   │   ├── presence.py      # S9-S10 (talaba VA o'qituvchi — bitta servis)
│   │   │   ├── docflow.py       # S11
│   │   │   └── notifications.py # S12
│   │   └── api/                 # routerlar (yupqa qatlam, logika services da)
│   │       ├── chat.py
│   │       ├── documents.py
│   │       ├── payments.py
│   │       ├── attendance.py
│   │       ├── docflow.py
│   │       ├── notifications.py
│   │       └── admin.py
│   ├── seed/
│   │   ├── generate.py          # sintetik ma'lumot generatori (--reset)
│   │   └── documents/           # demo hujjatlar korpusi (uz/ru/en)
│   └── tests/                   # pytest (sessiya bo'yicha fayl: test_s2_auth.py ...)
└── frontend/
    ├── package.json
    └── src/
        ├── app/                 # sahifalar: login, chat, contract, group,
        │                        # attendance, docflow, admin
        ├── components/          # ChatWindow, DocViewer, DocTranslate,
        │                        # PaymentTable, PresenceList, NotifBell, ...
        ├── lib/api.ts           # backend klienti (fetch wrapper) — YAGONA joy
        └── i18n/                # UI matnlari (uz.json asosiy)
```

Arxitektura qoidalari:
- Routerlar yupqa — biznes logika `services/` da, test qilish oson bo'lsin.
- RBAC tekshiruvi faqat `auth/rbac.py` mexanizmi orqali — hech qayerda qo'lda
  rol tekshirilmaydi.
- Tool qo'shish = `agents/tools/` ga fayl + `registry.py` ga ro'yxatga olish
  (ruxsat ro'yxati bilan). Boshqa hech narsa o'zgarmaydi.
- Frontend backendga faqat `lib/api.ts` orqali murojaat qiladi.

## Buyruqlar

```bash
# Backend (backend/ ichida)
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
python -m seed.generate --reset                  # demo baza
python -m seed.ingest_documents --reset          # hujjatlarni indekslash (S3)
pytest                                           # testlar

# Frontend (frontend/ ichida)
npm install
npm run dev                                      # http://localhost:3000
```

## Domen qoidalari (buzilmaydi)

1. **Faqat sintetik ma'lumot** — real shaxs ma'lumoti hech qayerda ishlatilmaydi
   (hackathon keysining qat'iy talabi).
2. **RBAC backendda** — rol cheklovi hech qachon faqat promptda yoki frontendda
   qolmaydi; har endpoint va har tool handler ruxsatni serverda tekshiradi.
3. **AI javobi rasmiy hujjat emas** — har agent javobida disclaimer ko'rinadi.
4. **Tarjimada original saqlanadi** — original matn hech qachon almashtirilmaydi,
   tarjima alohida qatlam; muhim atamalar qavsda originalda qoladi.
5. **Manba ko'rsatiladi** — agent har faktik javobida manbani keltiradi
   (hujjat+bo'lim yoki ma'lumot manbasi: "turniket logi, 10:02").
6. **Mavjudlik = xulosa** — "qaysi xonada" ma'lumoti jadvalga asoslangan taxmin
   sifatida ko'rsatiladi ("jadval bo'yicha"), fakt sifatida emas.
