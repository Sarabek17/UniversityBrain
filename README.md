# UniAgent — universitet uchun rol-asosli AI agentlar ekotizimi

**NEXUS30 hackathoni · EdTech treki · hamkor: Yandex**

UniAgent — universitetning kundalik ishini bitta AI ish maydoniga yig'adigan
tizim. Talaba, o'qituvchi, tyutor, dekanat va admin **bitta agent** bilan
gaplashadi, lekin har biri **faqat o'z doirasidagi** ma'lumotni ko'radi:
cheklov promptda emas, **backendda** — har endpoint va har vosita (tool)
ruxsatni serverda tekshiradi.

Ikki ustun ustiga qurilgan:

- **Rol-asosli RAG** — hujjatlar korpusi ko'p tilli embedding bilan
  indekslanadi, qidiruv filtri esa vektor bazasining ichida ishlaydi:
  ko'rish huquqi yo'q hujjat qidiruvda ham, ro'yxatda ham, rezyumeda ham
  umuman ko'rinmaydi.
- **Tool calling** — agent javobni o'ylab topmaydi, balki vosita chaqiradi
  (`hujjat_qidir`, `tolov_holati`, `mavjudlik_tekshir`, …) va javobni
  **faqat vosita natijasidan** yig'adi, manbasini ko'rsatgan holda.

---

## Modullar

| Modul | Nima qiladi |
|---|---|
| Chat + RAG | Hujjatlardan javob, har javobda manba (hujjat + bo'lim) |
| Summarizatsiya | Uzun hujjatni rol rakursida qisqartirish (map-reduce) |
| Tarjima | Yonma-yon original/tarjima; original hech qachon almashtirilmaydi |
| To'lovlar | Kontrakt qoldig'i, chek yuklash, tyutor tasdig'i |
| Davomat + mavjudlik | Turniket (fakt) + jadval (xulosa) + jurnal; bir klikda belgilash |
| O'qituvchilar davomati | Dekanat uchun "dars xavf ostida" svodi va oylik foizlar |
| Hujjat aylanmasi | Ariza/buyruq: `yuborildi → ko'rildi → ijroda → tasdiqlandi/rad etildi` |
| Bildirishnomalar | Bitta qo'ng'iroqcha, 10 xil trigger, har biri obyektga havola |
| Admin panel | Foydalanuvchi/rol, hujjat yuklash + indekslash, **demo reset** |

Agent vositalari (10 ta): `hujjat_qidir`, `hujjat_rezyume`, `tarjima_qil`,
`jadval_kor`, `tolov_holati`, `mavjudlik_tekshir`, `davomat_kor`,
`oqituvchi_davomat`, `ariza_holati`, `bildirishnomalar`.

---

## Arxitektura

```
backend/  FastAPI + SQLAlchemy + SQLite          frontend/  Next.js 16 (App Router)
  app/api/        yupqa routerlar                  src/app/        sahifalar
  app/services/   biznes logika                    src/components/ komponentlar
  app/auth/rbac   RBAC — YAGONA joy                src/lib/api.ts  backend klienti (yagona joy)
  app/rag/        chunking, embedding, qidiruv     src/i18n/uz.json UI matnlari (hardcode yo'q)
  app/agents/     orkestrator + tool registri
  app/llm/client  provayderdan mustaqil LLM klienti
  seed/           sintetik demo ma'lumot
```

Qat'iy qoidalar:

- **LLM chaqiruvi faqat `app/llm/client.py` orqali.** Provayder `.env` dagi
  `LLM_PROVIDER` bilan tanlanadi: `mock` (default, tarmoqsiz, deterministik)
  yoki `gemini`.
- **Embedding faqat `app/rag/embeddings.py` orqali.** Model —
  `intfloat/multilingual-e5-small`, lokal ishlaydi, API kalit talab qilmaydi.
- **RBAC faqat `app/auth/rbac.py` mexanizmi orqali** (`require_role` + doira
  filtrlari). Vosita ruxsati esa `app/agents/registry.py` da: rol mos
  kelmasa handler **umuman chaqirilmaydi**.
- **Vektor baza** — Chroma (`backend/chroma_data/`, lokal fayl).

---

## O'rnatish va ishga tushirish

Talab: **Python 3.11+**, **Node 22+**.

### Backend (`backend/` ichida)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux / macOS

# torch — avval CPU g'ildiragidan (PyPI dagi oddiy g'ildirak CUDA bilan ~10x katta)
pip install --index-url https://download.pytorch.org/whl/cpu torch
pip install -r requirements.txt

cp .env.example .env              # Windows: copy .env.example .env

python -m seed.generate --reset            # demo baza (43 foydalanuvchi)
python -m seed.ingest_documents --reset    # hujjatlarni indekslash (10 hujjat / 28 bo'lak)

uvicorn app.main:app --reload --port 8000
```

Birinchi indekslashda embedding modeli yuklab olinadi (~450 MB, bir marta).

### Frontend (`frontend/` ichida)

```bash
npm install
npm run dev                        # http://localhost:3000
```

**Portlar qat'iy: backend 8000, frontend 3000.** CORS faqat
`http://localhost:3000` ga ochiq (`CORS_ORIGINS`), frontend esa backend
manzilini `NEXT_PUBLIC_API_URL` dan oladi (`frontend/.env.local`,
default `http://localhost:8000`).

---

## Demo loginlar

Barcha demo foydalanuvchilar paroli: **`demo123`**

| Login | Rol | Ism | Demo roli |
|---|---|---|---|
| `aliyev` | talaba | Aliyev Jasur (AT-24-01) | binoda (10:02 da kirgan), kontrakt to'liq to'langan |
| `karimov` | talaba | Karimov Diyor (AT-24-01) | **qarzdor** (0 so'm), bugun binoga kelmagan |
| `sodiqova` | talaba | Sodiqova Malika (AT-24-01) | qisman to'lagan (50%), 13:15 da chiqib ketgan |
| `mahmudov` | talaba | Mahmudov Aziz (AT-24-01) | binoda, lekin davomatda belgilanmagan |
| `sharipova` | talaba | Sharipova Gulnora (AT-24-02) | chek yuklagan, tyutor tasdig'i kutilmoqda |
| `umarov` | o'qituvchi | Umarov Sherzod | darsda (3-juftlik, AT-24-01, 214-xona) |
| `tursunov` | o'qituvchi | Tursunov Akmal | **binoga kirmagan** — "dars xavf ostida" |
| `nazarova` | tyutor | Nazarova Dilfuza | AT guruhlari |
| `qodirova` | tyutor | Qodirova Madina | IQ guruhlari |
| `rashidova` | dekanat | Rashidova Nilufar | 1-fakultet (AT) |
| `yusupov` | dekanat | Yusupov Bekzod | 2-fakultet (IQ) |
| `admin` | admin | Abdusattorov Botir | boshqaruv paneli |

Login sahifasida asosiy 6 ta rol uchun bir bosishli tugmalar bor.

---

## Demo ma'lumotni qayta yaratish (reset)

Ikki yo'l — ikkalasi ham aynan bir xil ishni bajaradi:

**1) CLI (`backend/` ichida):**

```bash
python -m seed.generate --reset            # barcha jadvallar qaytadan yoziladi
python -m seed.ingest_documents --reset    # Chroma kolleksiyasi qayta quriladi
```

**2) UI:** `admin` bilan kiring → **Admin** → *"Demo ma'lumotni qayta
yaratish"*. Reset fon vazifasida ketadi (~5-30 s), tugagach brauzer
avtomatik `/login` ga qaytaradi (sessiyalar bekor bo'ladi — bu normal holat).

Resetdan keyin barcha demo qahramonlar yuqoridagi jadvaldagi holatida bo'ladi.

> Eslatma: admin yuklagan hujjat fayli `backend/uploads/documents/` da qoladi,
> lekin bazadan va qidiruvdan o'chadi — kerak bo'lsa qayta yuklanadi.

---

## Gemini API kalitini ulash

Loyiha butun ishlab chiqish davomida `LLM_PROVIDER=mock` rejimida qurildi:
mock provayder tarmoqsiz, deterministik javob beradi va butun oqim (qidiruv →
manba → javob) kalitisiz ham jonli ishlaydi. Haqiqiy modelga o'tish uchun
**faqat `backend/.env` faylini** o'zgartirish kerak, boshqa hech narsa emas:

```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=<https://aistudio.google.com/apikey dan olingan kalit>
GEMINI_MODEL=gemini-2.5-flash     # ixtiyoriy, default shu
```

Keyin backendni qayta ishga tushiring:

```bash
uvicorn app.main:app --reload --port 8000
```

Shu bilan chat, rezyume va tarjima — uchalasi ham Gemini orqali ishlaydi
(`app/llm/client.py` dagi `GeminiLLMClient` yagona nuqta; `google-genai`
paketi `requirements.txt` da). Kalit repozitoriyga hech qachon yozilmaydi:
`.env` — gitignore'da, `.env.example` da esa faqat bo'sh kalit turadi.

Orqaga qaytish: `LLM_PROVIDER=mock`.

---

## Domen qoidalari (buzilmaydi)

1. **Faqat sintetik ma'lumot.** Barcha ism, guruh, to'lov, turniket logi va
   hujjat matnlari generator tomonidan o'ylab topilgan; real shaxs ma'lumoti
   hech qayerda ishlatilmaydi.
2. **RBAC backendda.** Rol cheklovi hech qachon faqat promptda yoki
   frontendda qolmaydi.
3. **AI javobi rasmiy hujjat emas.** Har javob ostida disclaimer turadi va u
   backenddan keladi (frontend hardcode qilmaydi).
4. **Tarjimada original saqlanadi.** Tarjima — alohida qatlam, original matn
   almashtirilmaydi; muhim atamalar qavsda originalda qoladi.
5. **Manba ko'rsatiladi.** Har faktik javobda manba bor: hujjat + bo'lim yoki
   ma'lumot manbasi ("turniket logi, 10:02").
6. **Mavjudlik = xulosa.** "Qaysi xonada" ma'lumoti jadvalga asoslangan taxmin
   sifatida ("jadval bo'yicha") ko'rsatiladi, fakt sifatida emas.

---

## Testlar

```bash
# backend/ ichida
pytest                       # 281 ta test (S2-S14)
pytest tests/test_s14_gemini.py -q    # faqat Gemini klienti (kalitsiz, SDK stub bilan)
```

```bash
# frontend/ ichida
npm run lint
npm run build
```

Testlar alohida bazada ishlaydi (`backend/test_app.db`, `test_chroma_data/`,
`test_uploads/`) — demo bazaga tegmaydi.

---

## Hujjatlar

- `FUNKSIONALLIK_LOGIKA.md` — funksional spetsifikatsiya (nima qurilgan).
- `ISH_REJA.md` — sessiyalar rejasi (qanday qurilgan, S0-S14).
- `PROGRESS.md` — joriy holat, qabul qilingan qarorlar, keyinga qoldirilganlar.
- `TAQDIMOT.md` — 6 daqiqalik demo ssenariysi va taqdimot tezislari.
- `CLAUDE.md` — ishlab chiquvchi/agent uchun qoidalar.
