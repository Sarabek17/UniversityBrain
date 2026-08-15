# TAQDIMOT — UniAgent (NEXUS30, EdTech)

Bu fayl uch qismdan iborat: **6 daqiqalik demo oqimi** (qadam-baqadam),
**slaydlar tezislari** va **savol-javobga tayyor javoblar**.

---

## 0. Taqdimotdan oldin (5 daqiqa tayyorgarlik)

1. Backend va frontend ishga tushirilgan bo'lsin:
   `uvicorn app.main:app --port 8000` va `npm run dev` (3000-port).
2. `admin` bilan kiring → **Admin** → **"Demo ma'lumotni qayta yaratish"** —
   demo shu bilan toza holatdan boshlanadi (~5-30 s, keyin `/login`).
3. Gemini kaliti ulangan bo'lsin (`backend/.env`: `LLM_PROVIDER=gemini`,
   `GEMINI_API_KEY=…` — README ga qarang). Kalitsiz (mock) rejimda ham
   butun oqim ishlaydi, lekin agent javobi `[mock] …` deb boshlanadi:
   u holda chatda aniq vositani ko'rsatish uchun savol oldiga marker
   qo'yiladi, masalan `use_tool:tolov_holati:{}`.
4. Brauzer to'liq ekranda, kengligi ≥ 1440 px (o'ng paneli shunda ko'rinadi).
5. Login sahifasida 6 ta rol tugmasi bor — parol yozish shart emas.

**O'lchangan tizim vaqti:** butun ssenariy oxirigacha (mock rejimda, brauzer
avtomatikasi bilan) **~25 soniya** sof tizim javobi. Ya'ni 6 daqiqaning
qolgan qismi — gapirish uchun; hech bir qadam kutish sababli cho'zilmaydi.

---

## 1. Demo oqimi — 6 daqiqa

| Vaqt | Kim | Nima qilinadi | Ekranda kutilgan natija |
|---|---|---|---|
| 0:00–0:20 | — | Kirish gapi (muammo bir jumlada) | Login sahifasi, 6 ta rol tugmasi |
| 0:20–1:20 | **talaba** `aliyev` | 1-blok (pastda) | Manba chiplari, yonma-yon tarjima |
| 1:20–2:20 | **talaba** `aliyev` | 2-blok | Kontrakt raqamlari, yuborilgan ariza |
| 2:20–3:20 | **tyutor** `nazarova` | 3-blok | Qarzdorlar, chek tasdig'i, mavjudlik |
| 3:20–5:00 | **dekanat** `rashidova` | 4-blok | Qizil "dars xavf ostida", ariza tasdig'i |
| 5:00–5:40 | **talaba** `aliyev` | 5-blok (rol farqi) | "Topilmadi" — hujjat mavjudligi ham oshkor bo'lmaydi |
| 5:40–6:00 | **admin** | 6-blok | Statistika + "Demo ma'lumotni qayta yaratish" |

### 1-blok — talaba: savol → manba → tarjima (0:20–1:20)

1. `aliyev` tugmasi bilan kiring → darhol **Suhbat** sahifasi ochiladi.
2. Savol: **"Ma'lumotlar bazasidan topshiriq nima edi va muddati qachon?"**
   - *Kutilgan:* javob ustida `hujjat_qidir` yorlig'i, javob ostida
     **manba chiplari** ("Topshiriq 1: SQL so'rovlar … 1-bo'lak") va
     disclaimer.
   - *Aytiladigan gap:* "Agent javobni o'ylab topmaydi — vosita chaqiradi va
     javobni faqat topilgan bo'lakdan yig'adi. Manbani bosish mumkin."
3. **Hujjatlar** → *"Introduction to Machine Learning (Chapter 1)"* (inglizcha)
   → til tanlagichda **O'zbekcha** → **Tarjima**.
   - *Kutilgan:* "Inglizcha → O'zbekcha · 23 paragraf", chapda original,
     o'ngda tarjima; paragraf soni ikkala ustunda teng.
   - *Aytiladigan gap:* "Original hech qachon almashtirilmaydi — tarjima
     alohida qatlam, atamalar qavsda originalda qoladi."
4. Xuddi shu hujjatda **Rezyume** tugmasi.
   - *Kutilgan:* qisqa mazmun + "Manba: … (to'liq hujjat)" + disclaimer.
   - *Aytiladigan gap:* "Rezyume rolga qarab boshqacha bo'ladi: talabaga
     'mendan nima talab qilinadi', dekanatga 'raqam, sana, ijrochilar'."

### 2-blok — talaba: kontrakt va ariza (1:20–2:20)

1. **Kontrakt** sahifasi.
   - *Kutilgan:* Jami 12 000 000 / To'langan 12 000 000 / **Qoldiq 0 so'm**,
     100% progress, to'lovlar tarixi va "Chekni ochish" tugmalari, manba
     qatori ("To'lov jadvali — kontrakt 2025-2026, oxirgi chek CLK-…").
2. **Arizalar** → **Yangi ariza** → shablon *"O'qish joyidan ma'lumotnoma"*
   (matn avtomatik to'ldiriladi; `[qavs]` ichini to'ldiring) → **Yuborish**.
   - *Kutilgan:* "Hujjat yuborildi — status kuzatuvda", yangi ariza
     **Yuborildi** holatida, status tarixi bitta qator bilan ochiladi.
   - *Aytiladigan gap:* "Talaba dekanatga borib so'ramaydi — statusni real
     vaqtda ko'radi. Har qadam bildirishnoma yaratadi."

### 3-blok — tyutor: pul va odam (2:20–3:20)

1. `nazarova` bilan kiring → **Guruh**.
   - *Kutilgan:* "To'langan: 12 · Qisman: 2 · Qarzdor: 2 · Umumiy qarz
     34 800 000 so'm", ro'yxat qoldiq bo'yicha saralangan (qarzdorlar tepada).
2. **Sharipova Gulnora** qatorini bosing → o'ng panelda kontrakti ochiladi →
   **Tasdiqlash** (u kecha chek yuklagan).
   - *Kutilgan:* to'langan 6 000 000 → **7 200 000**, qoldiq 6 000 000 →
     **4 800 000**.
   - *Aytiladigan gap:* "'Chekni yukladim' bilan 'to'ladim' bir narsa emas:
     yuklangan chek qoldiqni kamaytirmaydi, tyutor tasdig'idan keyin
     kamayadi."
3. **Suhbat** → savol: **"Aliyev hozir universitetdami?"**
   *(mock rejimda: `mavjudlik_tekshir: Aliyev hozir universitetdami?`)*
   - *Kutilgan:* "binoda — turniket logi, 10:02", "**jadval bo'yicha**
     214-xonada", "davomatda belgilangan".
   - *Aytiladigan gap:* "Turniket — fakt, xona — jadvalga asoslangan
     **xulosa**, va tizim bu ikkisini hech qachon aralashtirmaydi."

### 4-blok — dekanat: nazorat va qaror (3:20–5:00)

1. `rashidova` bilan kiring → **qo'ng'iroqcha** (o'ng yuqorida, qizil sanoq).
   - *Kutilgan:* "**Dars xavf ostida:** Tursunov Akmal bugun 3-juftlikdagi
     darsiga …", "Yangi ariza keldi: Aliyev Jasur — …".
2. Bildirishnomani bosing (yoki **Davomat** → **O'qituvchilar**).
   - *Kutilgan:* birinchi qator **qizil** — Tursunov Akmal, "Bugun kelmagan",
     har dars uchun holat chipi (*xavf ostida / aniqlashtirish kerak*);
     yuqorida svod: "Binoda: 4 · Kelmagan: 1 · Xavf ostida: 1".
   - *Aytiladigan gap:* "Bu holat DB da saqlanmaydi — turniket + jadval +
     davomat jurnalidan **hisoblanadi**, shuning uchun soatiga qarab
     'xavf ostida' dan 'aniqlashtirish kerak' ga o'tadi."
3. **Oylik jadval** tabi.
   - *Kutilgan:* eng past foiz birinchi qatorda — Tursunov 8/10 = **80%**.
4. **Arizalar** → **Kelgan hujjatlar** → talabaning yangi arizasi →
   **Tasdiqlash** → izoh → **Yuborish**.
   - *Kutilgan:* holat **Tasdiqlandi**, status tarixiga yangi qator,
     talabaga bildirishnoma ketadi.
5. **Suhbat** → **"Buyruq 91-M ni qisqartirib ber"**
   *(mock rejimda: `use_tool:hujjat_rezyume:{"nom": "91-M"}`)*
   - *Kutilgan:* attestatsiya buyrug'ining qisqa mazmuni + manba.

### 5-blok — rol farqi jonli (5:00–5:40)

1. **Chiqish** → `aliyev` bilan kiring → **xuddi shu savolni** bering.
   - *Kutilgan:* "topilmadi" javobi — hujjat 91-M `staff` darajasida, ya'ni
     talaba uchun u **umuman mavjud emas**.
2. **Hujjatlar** sahifasi: ro'yxatda 91-M yo'q.
   - *Aytiladigan gap:* "Bu cheklov promptda emas: qidiruv filtri vektor
     bazasining ichida, endpoint esa 404 qaytaradi — 403 emas, chunki
     hujjatning **mavjudligi ham** oshkor bo'lmasligi kerak."

### 6-blok — admin: panel va reset (5:40–6:00)

1. `admin` → **Admin**.
   - *Kutilgan:* 6 ta statistika kartasi (43 foydalanuvchi, 10 hujjat /
     28 bo'lak, to'lovlar, bugungi davomat 86%, o'qituvchilar, hujjat
     aylanmasi), foydalanuvchilar jadvali (rolni bevosita jadvalda
     o'zgartirish mumkin), hujjat yuklash formasi.
2. Ixtiyoriy (vaqt bo'lsa): `.md` fayl yuklang → "… yuklandi va N bo'lakda
   indekslandi" → talaba chatida darhol topiladi va unga **"Yangi hujjat
   e'loni"** bildirishnomasi boradi.
3. Yakun: **"Demo ma'lumotni qayta yaratish"** — bir bosishda hamma narsa
   boshlang'ich holatga qaytadi.

---

## 2. Slaydlar tezislari

### Slayd 1 — Muammo
- Talaba javobni to'rt joydan qidiradi: e'lonlar guruhi, dekanat koridori,
  qog'oz nizom, kurator telefoni.
- Xodim vaqtining katta qismi **takroriy savollarga** ketadi: "kontraktdan
  qancha qoldi", "arizam qayerda", "o'qituvchi keldimi".
- Ma'lumot bor, lekin **tarqoq va rolga bo'linmagan** — shuning uchun
  "hammaga hamma narsa" yoki "hech kimga hech narsa".

### Slayd 2 — Yechim
- **Bitta agent, besh rakurs.** Talaba, o'qituvchi, tyutor, dekanat, admin —
  bitta interfeys, lekin har biri o'z doirasi bilan.
- **Rol-asosli RAG + tool calling.** Agent javobni o'ylab topmaydi: vosita
  chaqiradi, natijadan javob yig'adi va manbani ko'rsatadi.
- **Cheklov backendda.** Prompt "iltimos" qiladi, backend esa **rad etadi**:
  rol mos kelmasa vosita handleri umuman chaqirilmaydi.

### Slayd 3 — Demo (yuqoridagi 6 blok)
- Talaba: savol → manba → tarjima → kontrakt → ariza.
- Tyutor: qarzdorlar, chek tasdig'i, "hozir universitetdami?".
- Dekanat: "dars xavf ostida", oylik foizlar, ariza tasdig'i.
- Rol farqi jonli: bitta savol, ikki xil javob.

### Slayd 4 — Arxitektura
- **Backend:** FastAPI + SQLAlchemy + SQLite; routerlar yupqa, biznes logika
  `services/` da.
- **RAG:** ko'p tilli embedding (`multilingual-e5-small`) + Chroma;
  markazlashtirish (mean centering) + gibrid reyting (0.7 kosinus +
  0.3 leksik) — o'zbekcha savol inglizcha hujjatni ham topadi
  (o'lchov: top-1 15/23 → **20/23**).
- **Agent:** tool registri (nom + JSON Schema + handler + **ruxsat ro'yxati**),
  orkestrator tool loopi, 10 ta vosita, 5 ta rol prompti + umumiy qoidalar.
- **LLM provayderdan mustaqil:** `llm/client.py` — bitta interfeys, ikki
  implementatsiya (mock / Gemini). Provayder almashtirish = `.env` dagi bitta
  qator.
- **Frontend:** Next.js 16 (App Router) + TypeScript + Tailwind; backendga
  faqat `lib/api.ts` orqali; UI matnlari `i18n/uz.json` da.
- **Sifat:** 281 ta avtomatlashtirilgan test, lint + build toza.

### Slayd 5 — Real joriy etish yo'li
| Hozir (hackathon) | Ishlab chiqarishda |
|---|---|
| Sintetik to'lovlar, chek — strukturali yozuv | **Click / Payme API** (webhook + rekonsiliatsiya), chek fayli obyekt-storage'da |
| Turniket loglari generatordan | **Real turniket / kartochka tizimi** (SDK yoki oraliq broker), oflayn buferi bilan |
| "Tasdiqlash" tugmasi = shartli imzo | **ERI (elektron raqamli imzo)** — E-IMZO integratsiyasi, hujjat xeshi bilan |
| SQLite + lokal Chroma | PostgreSQL + boshqariladigan vektor baza, migratsiyalar |
| Foydalanuvchilar seed'dan | **HEMIS / universitet ma'lumot tizimi** bilan sinxronizatsiya, SSO |
| Bildirishnoma — in-app polling | Push / Telegram-bot / SMS kanali, navbat (queue) orqali |
| Mock yoki bitta LLM provayder | Provayder almashtiriladigan (`llm/client.py`), lokal model ham mumkin |

Bosqichlar: **pilot bitta fakultet (1 oy) → to'lov va turniket integratsiyasi
(2 oy) → ERI va butun universitet (3-6 oy)**.

### Slayd 6 — Nima allaqachon tayyor
- 9 modul, 10 agent vositasi, 5 rol, 43 demo foydalanuvchi, 10 hujjatli
  ko'p tilli korpus (uz/ru/en).
- Bir bosishli **demo reset** — taqdimotni istalgan payt qaytadan boshlash
  mumkin.
- Admin hujjat yuklasa — u **keyingi savoldayoq** qidiruvda topiladi va
  tegishli rollarga e'lon bildirishnomasi ketadi.

---

## 3. Savol-javobga tayyor javoblar

### "Maxfiylik qanday ta'minlanadi? Agent hamma ma'lumotni ko'rmaydimi?"
Yo'q. Cheklov **uch qatlamda** va uchalasi ham serverda:
1. **Endpoint** — `require_role()` va doira filtrlari (`auth/rbac.py`,
   yagona joy). Talaba boshqa talabaning kontraktini so'rasa — **403**.
2. **Vosita** — registr rolni handlerdan **oldin** tekshiradi: `tolov_holati`
   o'qituvchiga ochiq emas, `oqituvchi_davomat` faqat dekanatga. Rol mos
   kelmasa handler umuman ishlamaydi, model esa "ruxsat yo'q" natijasini
   oladi va shuni tushuntiradi.
3. **Ma'lumot qatlami** — qidiruv filtri Chroma metadata darajasida:
   ko'rinmaydigan hujjat natijalar ro'yxatiga **umuman kirmaydi**, keyin
   filtrlanmaydi.
Bundan tashqari shaxsiy hujjatda **404** ishlatiladi (403 emas), ya'ni
hujjatning mavjudligi ham oshkor bo'lmaydi. Buni demoning 5-blokida jonli
ko'rsatamiz.

### "AI xato qilsa-chi? Noto'g'ri javobga kim javob beradi?"
Uchta mexanizm bir vaqtda ishlaydi:
1. **Disclaimer** — har javob ostida "AI javobi universitetning rasmiy hujjati
   hisoblanmaydi" yozuvi turadi va u backenddan keladi (frontend uni
   o'chira olmaydi).
2. **Manba majburiy** — agent har faktik javobda manbani keltiradi: hujjat +
   bo'lim yoki ma'lumot manbasi ("turniket logi, 10:02"). Foydalanuvchi
   javobni bir bosishda asl matn bilan solishtira oladi.
3. **Xulosa fakt sifatida ko'rsatilmaydi** — "qaysi xonada" savoli
   **"jadval bo'yicha"** izohi bilan qaytadi; turniket vaqti fakt, xona esa
   taxmin. O'qituvchining "dars xavf ostida" holati ham hisoblangan xulosa,
   DB dagi status emas — ikkisi javobda yonma-yon turadi.
Va eng muhimi: agent **faqat vosita natijasidan** javob yasaydi. Vosita hech
narsa topmasa, javob "topilmadi" bo'ladi — bo'sh joyni to'qib to'ldirmaydi.
Qaror (ariza tasdig'i, davomat belgisi, chek tasdig'i) esa har doim **odam**
tomonidan bosiladi va status tarixiga kim/qachon yozib qo'yiladi.

### "Real ma'lumot qani? Nega hamma narsa o'ylab topilgan?"
Bu **keysning qat'iy talabi**: real shaxs ma'lumoti ishlatilmaydi. Shuning
uchun butun demo bazasi generator bilan yaratilgan — 43 foydalanuvchi,
jadval, turniket loglari, to'lovlar, hujjatlar korpusi. Ammo **struktura
haqiqiy**: juftlik vaqtlari ichki tartib nizomi bilan mos, to'lov sxemasi
40/30/30, chek raqamlari Click formatida. Ya'ni real manbaga ulanish =
`seed/generate.py` o'rniga integratsiya adapterini qo'yish; modellar,
endpointlar va RBAC o'zgarmaydi.

### "Nega Gemini? Yandex resursi bo'lsa-chi?"
LLM chaqiruvi butun loyihada **bitta modul** orqali ketadi
(`app/llm/client.py`, `chat(messages, tools, system) -> LLMResponse`).
Provayder `.env` dagi bitta qator bilan tanlanadi; hozir mock va Gemini
implementatsiyasi bor, uchinchisini qo'shish = bitta klass. Shuning uchun
Yandex modeli (yoki lokal model) berilsa, qolgan kod umuman o'zgarmaydi.

### "Bu ChatGPT'ga hujjat tashlashdan nimasi bilan farq qiladi?"
Uch narsa bilan: (a) **rol** — bir savol besh xil odamga besh xil javob
beradi va cheklov serverda; (b) **jonli ma'lumot** — kontrakt qoldig'i,
turniket, davomat, ariza statusi hujjatda emas, bazada, agent ularga
vosita orqali boradi; (c) **amal** — agent nafaqat gapiradi, balki tizimda
ish bajaradi (ariza yuborish, chek tasdig'i, davomat belgilash) va har amal
audit izini qoldiradi.

### "Nechta odam ishlatadi? Yuklamaga chidaydimi?"
Demo bitta jarayonda SQLite bilan ishlaydi — hackathon uchun yetarli.
Arxitektura esa gorizontal: routerlar holatsiz, biznes logika `services/` da,
vektor baza alohida. Ishlab chiqarishga chiqishda SQLite → PostgreSQL,
lokal Chroma → boshqariladigan vektor baza, reset bayrog'i → Redis.
Bu almashtirishlar kod strukturasini o'zgartirmaydi.

### "Hozir nima ishlamaydi?" (halol javob)
- Mobil layout: o'ng panellar kichik ekranda yashiringan (planshet/desktop
  uchun optimallashtirilgan).
- Eksport (CSV/XLSX), PDF/DOCX hujjat yuklash — hozircha `.md`/`.txt`.
- Real-time yo'q: bildirishnoma 60 soniyalik polling bilan yangilanadi.
- Topshiriq deadline'i bo'yicha bildirishnoma triggeri — `Assignment` modeli
  bor, lekin unga endpoint hali yozilmagan.
To'liq ro'yxat `PROGRESS.md` ning "Keyinga qoldirilganlar" bo'limida —
har biri sababi bilan yozilgan.
