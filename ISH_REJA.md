# ISH REJA — sessiyalarga bo'lingan 100% reja

> Har bir sessiya — **alohida Claude sessiyasi** (yangi kontekst).
> Maqsad: kontekst toza va kichik bo'lsin, model faqat bitta modulga
> fokuslansin — gallyutsinatsiya xavfi minimal bo'lsin.

## Sessiya protokoli (har sessiyada majburiy)

**Boshlanishda:**
1. `CLAUDE.md` avtomatik o'qiladi (loyiha qoidalari shu yerda).
2. `PROGRESS.md` o'qiladi — qaysi sessiyada turibmiz, oldingi sessiya nima
   qoldirgan.
3. `FUNKSIONALLIK_LOGIKA.md` dan **faqat shu sessiyaga tegishli bo'lim** o'qiladi.
4. Sessiya doirasidan tashqari modulga **tegilmaydi** (import qilish mumkin,
   o'zgartirish mumkin emas).

**Yakunida:**
1. Tekshirish buyruqlari ishga tushiriladi (har sessiyada ko'rsatilgan).
2. `PROGRESS.md` yangilanadi: nima qilindi, qanday muhim qaror qabul qilindi,
   keyingi sessiyaga nima qoldi.
3. Hech narsa "keyin tuzataman" holatida qoldirilmaydi — DoD bajarilmasa,
   sessiya yakunlanmagan hisoblanadi.

**Gallyutsinatsiyaga qarshi qoidalar:**
- Mavjud funksiya/endpoint/model nomini **taxmin qilmaslik** — avval faylni
  o'qish (Read/Grep), keyin ishlatish.
- API javob formatini o'ylab topmaslik — `schemas.py` dagi haqiqiy sxemaga qarash.
- Bir sessiyada 8-10 tadan ortiq fayl yaratmaslik/o'zgartirmaslik — undan katta
  ish rejada bo'linishi kerak edi, to'xtab bo'lish kerak.
- Har yozilgan endpoint darhol test yoki curl bilan tekshiriladi.

---

## Sessiyalar xaritasi

| № | Sessiya | Ustuvorlik | Bog'liq |
|---|---|---|---|
| S0 | Loyiha skeleti + ma'lumotlar modeli | MVP | — |
| S1 | Demo ma'lumot generatori (seed) | MVP | S0 |
| S2 | Auth + RBAC | MVP | S0, S1 |
| S3 | RAG quvuri | MVP | S0, S1 |
| S4 | Agent yadrosi + tool calling | MVP | S2, S3 |
| S5 | Chat UI + hujjat paneli | MVP | S4 |
| S6 | Summarizatsiya | MVP | S4, S5 |
| S7 | Tarjima moduli | P1 | S3, S5 |
| S8 | To'lovlar moduli | P1 | S2, S4 |
| S9 | Davomat + mavjudlik (talaba) | P1 | S2, S4 |
| S10 | O'qituvchilar davomati | P1 | S9 |
| S11 | Hujjat almashinuvi | P1 | S2, S4 |
| S12 | Bildirishnomalar markazi | P1 | S8–S11 |
| S13 | Admin panel + demo reset | P1 | hammasi |
| S14 | Yakuniy integratsiya + demo + taqdimot | MVP | hammasi |

> Vaqt siqilsa, qisqartirish tartibi (oxiridan emas, qiymatiga qarab):
> S13 admin panelni minimal qilish → S10 ni S9 ichiga kontsept sifatida
> kiritish → S7 tarjimani bitta hujjatlik demoga qisqartirish.
> S8 (to'lov) va S11 (hujjat almashinuvi) — bizning kuchli farqlovchi
> g'oyalarimiz, ularni qisqartirmaymiz.

---

## S0 — Loyiha skeleti + ma'lumotlar modeli

**Maqsad:** ishga tushadigan bo'sh karkas: backend, frontend, DB, config.
**Ishlar:**
- Papka tuzilishini yaratish (`CLAUDE.md` dagi arxitektura bo'yicha).
- FastAPI ilova: `main.py`, `config.py` (.env dan o'qiydi), health endpoint.
- SQLAlchemy modellari — `FUNKSIONALLIK_LOGIKA.md` 4-bo'limdagi **barcha**
  obyektlar (User, Group, Document, Chunk, Translation, Assignment, Schedule,
  Contract, Payment, TurnstileLog, Attendance, ClassSession, FlowDocument,
  FlowHistory, Notification).
- Pydantic sxemalar fayli (`schemas.py`) — asosiy obyektlar uchun.
- Next.js/React ilova skeleti: bo'sh layout, routing, API klient moduli.
- `requirements.txt` / `package.json`, `.env.example`, `.gitignore`, git init.
**DoD:** `uvicorn` ko'tariladi, `/health` 200 qaytaradi; frontend `npm run dev`
bilan ochiladi; DB jadvallari yaratiladi (alembic yoki create_all).
**Tekshirish:** `curl /health`; `python -c "from app.models import *"`;
frontend sahifasi ochilishi.

## S1 — Demo ma'lumot generatori (seed)

**Maqsad:** butun tizim uchun realistik sintetik ma'lumotlar — bitta buyruq
bilan.
**Ishlar:**
- `seed/generate.py`: 2 fakultet, 4 guruh, ~30 talaba, ~8 o'qituvchi, 2 tyutor,
  2 xodim, 1 admin; dars jadvali (hafta bo'yicha, xonalar bilan); kontraktlar +
  to'lovlar (to'liq/qisman/qarzdor holatlar aralash); turniket loglari (bugungi
  kun uchun realistik: kimdir binoda, kimdir chiqib ketgan, bitta o'qituvchi
  darsiga kelmagan ssenariy!); davomat yozuvlari; 3-4 ta ariza turli statuslarda.
- Demo hujjatlar korpusi `seed/documents/`: syllabus, 3-4 topshiriq, ichki
  tartib nizomi, 2 buyruq, 1 inglizcha maqola/darslik bo'limi, 1 ruscha —
  matnlarini shu sessiyada yozamiz (har biri 1-2 sahifa, realistik).
- `python -m seed.generate --reset` — hammasini o'chirib qayta yaratadi
  (bu keyin admin paneldagi "demo reset" ham ishlatadi).
**DoD:** bitta buyruq bilan to'liq demo baza; qayta ishga tushirsa ham ishlaydi
(idempotent).
**Tekshirish:** seed skript xatosiz o'tadi; DB da kutilgan sonlar bor (SQL
count tekshiruvlari skript oxirida chiqadi).
**Muhim:** demo ssenariy "qahramonlari"ni shu yerda qat'iy belgilaymiz
(masalan talaba Aliyev — binoda, qarzdor emas; o'qituvchi X — darsiga
kelmagan) va `PROGRESS.md` ga yozib qo'yamiz — demo skript shularga tayanadi.

## S2 — Auth + RBAC

**Maqsad:** login va rol asosidagi kirishning yagona mexanizmi.
**Ishlar:**
- Login endpoint (JWT yoki server sessiya — soddasi tanlanadi), logout, `me`.
- RBAC dekorator/dependency: `require_role(...)` + doira filtri
  (tyutor → o'z guruhi, dekanat → o'z fakulteti) — **bitta joyda**, hamma
  keyingi modullar shuni ishlatadi.
- Frontend: login sahifasi + tez "demo rol tanlash" tugmalari (taqdimotda rol
  almashish 2 soniya bo'lsin), auth konteksti, himoyalangan routelar.
**DoD:** 5 rolda kirish ishlaydi; ruxsatsiz so'rov 403 oladi; rol almashish tez.
**Tekshirish:** har rol uchun curl bilan kirish + taqiqlangan endpointga 403
testi (pytest da 5-6 ta test).

## S3 — RAG quvuri

**Maqsad:** hujjatlarni indekslash va rol filtri bilan semantik qidiruv.
**Ishlar:**
- Ingest: fayl → matn → til aniqlash → bo'laklash (500–1000 token) →
  embedding → vektor baza (Chroma, lokal) + Chunk yozuvlari.
- Qidiruv funksiyasi: `search(query, user)` — avval `kirish_darajasi` bo'yicha
  metadata filtr, keyin semantik qidiruv, natijada bo'lak + hujjat nomi + o'rin.
- Seed hujjatlarini indekslash (S1 korpusi) — seed jarayoniga ulanadi.
- Embedding moduli provayderdan mustaqil (CLAUDE.md dagi LLM qoidasi kabi).
**DoD:** o'zbekcha savol inglizcha hujjatdan ham topadi (ko'p tilli embedding);
talaba roli bilan qidirsak "faqat xodim" hujjati chiqmaydi.
**Tekshirish:** 5-6 ta qidiruv testi (pytest): topilishi kerak bo'lgan /
chiqmasligi kerak bo'lgan holatlar.

## S4 — Agent yadrosi + tool calling

**Maqsad:** loyihaning yuragi — rolga mos agent, vositalar orqali ishlaydi.
**Ishlar:**
- LLM klient moduli: provayderdan mustaqil interfeys (bitta klass), tool
  calling qo'llaydi; provayder .env dan tanlanadi.
- Tool registri: har tool = nom + tavsif + sxema + handler + **ruxsat ro'yxati**.
  Ruxsat backendda tekshiriladi (agent so'rasa ham, roli mos kelmasa handler
  ishlamaydi va "ruxsat yo'q" qaytadi).
- Shu sessiyada 3 ta tool: `hujjat_qidir` (S3 ga ulanadi), `jadval_kor`,
  `hujjat_rezyume` (oddiy variant — hujjat matnini qisqartirish).
  Qolgan toollar o'z sessiyalarida qo'shiladi — registr shunga tayyor bo'lsin.
- Rol bo'yicha tizim promptlari (5 rol) — alohida fayllar `agents/prompts/`.
- Javob formati: matn + manbalar ro'yxati + "rasmiy hujjat emas" belgisi.
- Chat endpoint: `POST /chat` (tarix bilan), suhbat DB da saqlanadi.
**DoD:** curl orqali talaba sifatida "topshiriq nima edi?" desak — agent
`hujjat_qidir` ni chaqirib, manba bilan javob qaytaradi.
**Tekshirish:** har rol uchun 1 ta jonli so'rov; ruxsatsiz tool chaqiruvi
bloklanish testi.

## S5 — Chat UI + hujjat paneli

**Maqsad:** foydalanuvchi ko'radigan asosiy interfeys.
**Ishlar:**
- Chat oynasi: xabarlar, yozish, kutish holati, manbalar chiplari (bosilsa
  hujjat ochiladi), "rasmiy hujjat emas" ogohlantirishi.
- Hujjatlar ro'yxati (rol filtri bilan, backenddan) + hujjat ko'rish paneli.
- Rolga qarab layout: talaba (chat markazda), tyutor/xodim (chat + dashboard
  o'rni — hozircha bo'sh joy, keyingi sessiyalar to'ldiradi).
**DoD:** brauzerda login → chat → savol → manbali javob → manba bosilsa hujjat
ochiladi.
**Tekshirish:** 4 rolda qo'lda o'tish (checklist bilan); console'da xato yo'q.

## S6 — Summarizatsiya

**Maqsad:** rezyume funksiyasini rolga mos rakurs bilan yakunlash.
**Ishlar:**
- `hujjat_rezyume` toolini rolga mos promptlar bilan kuchaytirish (talaba:
  "nima qilishim kerak/qachon"; xodim: "sana, raqam, ijrochi").
- Hujjat panelida "Rezyume" tugmasi (chatga murojaatsiz ishlaydi).
- Uzun hujjat uchun bo'lib-bo'lib rezyume (map-reduce) — oddiy varianti.
**DoD:** 2 sahifalik buyruq 5-6 qatorli aniq rezyumega tushadi, rol rakursi
seziladi.
**Tekshirish:** bitta hujjatni 3 rolda rezyume qilib farqni ko'rish.

## S7 — Tarjima moduli

**Maqsad:** original + yonma-yon tarjima, atamalar himoyasi.
**Ishlar:**
- `tarjima_qil` tool + tarjima servisi: paragraf-paragraf, atamalar qavsda
  originalda ("machine learning" naqshi), Translation jadvaliga kesh.
- UI: hujjat panelida "Tarjima" rejimi — chapda original, o'ngda tarjima,
  paragraflar sinxron skroll.
- Chatda tillar aro javob: o'zbekcha savol → inglizcha manba → o'zbekcha javob
  + originalda sitata (S3 allaqachon topadi, bu yerda javob formatlanadi).
**DoD:** inglizcha maqola yonma-yon o'zbekchada o'qiladi; ikkinchi ochilishda
keshdan (tez) keladi; original doim ko'rinadi.
**Tekshirish:** bitta hujjatni ikki marta ochib vaqt farqi; atama naqshi
tarjimada borligini ko'rish.

## S8 — To'lovlar moduli

**Maqsad:** chek muammosini yopish — talaba ko'radi, tyutor tekshirmaydi,
so'ramaydi.
**Ishlar:**
- Endpointlar: talaba o'z kontrakt/to'lovlari; tyutor guruh svodi; chek fayl
  ko'rish; chek yuklash + tyutor tasdiqlashi (ochiq savol hal bo'lganicha —
  ikkalasi ham).
- UI talaba: "Kontrakt" sahifa — jami/to'langan/qoldiq, to'lovlar jadvali,
  chek ochish.
- UI tyutor: guruh dashboardi — status ranglari (to'langan/qisman/qarzdor),
  saralash, chekka o'tish.
- `tolov_holati` toolini registrga qo'shish (talaba o'ziniki, tyutor guruhi —
  RBAC S2 mexanizmi bilan).
**DoD:** talaba "kontraktimdan qancha qoldi?" desa agent aniq raqam + oxirgi
chek bilan javob beradi; tyutor dashboardda qarzdorlarni ko'radi.
**Tekshirish:** talaba boshqa talabaning to'lovini so'rasa rad etilishi (test);
tyutor faqat o'z guruhini ko'rishi (test).

## S9 — Davomat + mavjudlik (talaba)

**Maqsad:** turniket + jadval + davomat uchligidan mavjudlik xulosasi.
**Ishlar:**
- Mavjudlik servisi: `presence(user_id)` → turniket logidan binoda/emas +
  jadval kesishmasidan "qaysi xonada bo'lishi kerak" + davomat tasdig'i.
  **Bitta funksiya — talaba ham, keyin S10 da o'qituvchi ham shu orqali.**
- O'qituvchi UI: dars boshida guruh ro'yxati → bir klik davomat belgilash
  (Attendance + ClassSession yoziladi).
- Tyutor UI: guruh mavjudlik ro'yxati (binoda/darsda-tasdiqlangan/yo'q) +
  kunlik davomat foizi.
- `mavjudlik_tekshir` va `davomat_kor` toollari registrga.
**DoD:** "Aliyev hozir universitetdami?" → "binoda, 10:02 da kirgan, jadval
bo'yicha 214-xonada, davomatda belgilangan" — manbalar bilan.
**Tekshirish:** seed'dagi 3 xil holat (binoda+darsda / binoda+belgilanmagan /
chiqib ketgan) to'g'ri qaytishi (pytest).

## S10 — O'qituvchilar davomati

**Maqsad:** dekanat uchun o'qituvchi nazorati — S9 mexanizmi ustiga.
**Ishlar:**
- ClassSession holat mantig'i: jadvaldagi dars vaqti + o'qituvchi turniket
  logi + davomat belgilanganligi → o'tildi / xavf ostida / aniqlashtirish /
  kechikkan.
- Dekanat UI: bugungi svod (o'qituvchilar ro'yxati, holat ranglari) + oylik
  jadval (foizlar).
- "Dars xavf ostida" hodisasi Notification yozuvini yaratadi (S12 ga tayyor —
  jadval hozircha DB ga yozadi, UI S12 da).
- `oqituvchi_davomat` tool (faqat dekanat/admin).
**DoD:** seed'dagi "kelmagan o'qituvchi" ssenariysi dashboardda qizil ko'rinadi;
agent "bugun kim darsga kelmadi?" ga to'g'ri javob beradi.
**Tekshirish:** 3 holat testi (keldi-o'tdi / kelmadi / kechikdi); o'qituvchi
roli boshqa o'qituvchini ko'ra olmasligi.

## S11 — Hujjat almashinuvi

**Maqsad:** ariza/hujjat aylanmasi — status zanjiri bilan.
**Ishlar:**
- Shablonlar (seed'ga 4-5 ta: ma'lumotnoma, akademik ta'til, qayta topshirish,
  hisobot, buyruq-topshiriq).
- Endpointlar: yaratish (shablondan), kelganlar/yuborilganlar ro'yxati, status
  o'zgartirish (ko'rildi/ijroda/tasdiqlandi/rad+sabab), tarix.
- Har status o'zgarishi FlowHistory + Notification yozadi.
- UI: talaba — "Arizalarim" (yangi ariza + status kuzatuv); xodim — kelgan
  hujjatlar kutubxonasi (saralash: yangi/muddati o'tayotgan), ko'rish +
  qaror tugmalari; o'qituvchi — hujjat topshirish.
- `ariza_holati` tool; kelgan hujjatni rezyume qilish S6 tooli bilan ishlaydi.
**DoD:** talaba ariza yuboradi → xodim ko'rib tasdiqlaydi → talaba statusda
ko'radi; "arizam qayerda?" ga agent javob beradi.
**Tekshirish:** to'liq zanjir testi (yuborildi→tasdiqlandi, tarix 3 yozuv);
begona ariza ko'rinmasligi testi.

## S12 — Bildirishnomalar markazi

**Maqsad:** hamma modul hodisalarini bitta qo'ng'iroqchaga yig'ish.
**Ishlar:**
- Notification servisi allaqachon yozilayotgan yozuvlarni (S10, S11) + yangi
  triggerlarni (deadline yaqin, qarzdorlik, yangi topshiriq) qamrab oladi —
  triggerlar ro'yxati `FUNKSIONALLIK_LOGIKA.md` 3.10 jadvalidan.
- Deadline/qarzdorlik tekshiruvi: sodda yo'l — login/sahifa ochilganda hisoblash
  (hackathon uchun cron shart emas).
- UI: qo'ng'iroqcha + sanoq, ro'yxat panel, bosilsa tegishli obyektga o'tadi,
  o'qildi belgisi.
- Agent: "menda yangi nima bor?" → o'qilmaganlar svodi.
**DoD:** S8–S11 hodisalari bildirishnoma yaratadi va bosilsa to'g'ri sahifa
ochiladi.
**Tekshirish:** har trigger turi uchun bitta hodisa yasab ko'rish (checklist).

## S13 — Admin panel + demo reset

**Maqsad:** boshqaruv va taqdimot xavfsizligi.
**Ishlar:**
- Foydalanuvchi/rol boshqaruvi (ro'yxat, yaratish, rol o'zgartirish).
- Hujjat yuklash + teglash UI (ingest S3 quvuriga ulanadi).
- **Demo reset tugmasi** — S1 seed skriptini chaqiradi (taqdimotdan oldin
  bir bosishda toza holat).
**DoD:** admin yangi hujjat yuklasa, u qidiruvda topiladi; reset ishlaydi.
**Tekshirish:** yukla→qidir→top zanjiri; reset'dan keyin demo qahramonlar
joyida.

## S14 — Yakuniy integratsiya + demo + taqdimot

**Maqsad:** 6 daqiqalik demo oqimini silliq qilish.
**Ishlar:**
- `FUNKSIONALLIK_LOGIKA.md` 8-bo'limdagi demo ssenariyni boshdan-oxir 3 marta
  o'tkazish, har qoqilgan joyni tuzatish (faqat shu ssenariy yo'lidagi bugfix —
  yangi funksiya QO'SHILMAYDI).
- UI pardozi: nomlar, bo'sh holatlar, yuklanish indikatorlari.
- Taqdimot materiallari: slaydlar tezislari (muammo → yechim → demo → arxitektura
  → real joriy etish yo'li: Click API, real turniket, ERI) + savol-javobga
  tayyor javoblar (maxfiylik savoli, "AI xato qilsa-chi" savoli).
- README: o'rnatish + ishga tushirish yo'riqnomasi.
**DoD:** toza reset'dan keyin demo ssenariy to'liq, qoqilmasdan o'tadi.
**Tekshirish:** vaqt o'lchab yakuniy repetitsiya (≤ 6 daqiqa).
