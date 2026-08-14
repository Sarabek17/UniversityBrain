# UniAgent — Universitet uchun AI agentlar ekotizimi
## Funksionallik va logika hujjati (loyiha pishitish uchun ishchi hujjat)

> NEXUS30 hackathoni, EdTech treki (hamkor: Yandex).
> Bu hujjat — ishchi hujjat. Har bir bo'limga izoh/qo'shimcha yozib boring.
> Holat belgilari: **[MVP]** — birinchi navbatda, **[P1]** — MVP dan keyin,
> **[P2]** — vaqt qolsa / kontsept, **[?]** — muhokama talab.
> Ish tartibi: `ISH_REJA.md` (sessiyalarga bo'lingan reja), qoidalar: `CLAUDE.md`.

---

## 1. Loyiha konsepsiyasi (bitta gap)

Foydalanuvchi tizimga kiradi → tizim uning rolini biladi → AI agent shu rol
huquqlari doirasidagi universitet ma'lumotlaridan (hujjatlar, jadval, to'lovlar,
davomat, arizalar) foydalanib, foydalanuvchi tilida javob beradi, manbani
originalda ko'rsatadi.

Asosiy g'oya: barcha modullar AI agent chaqira oladigan **vositalar (tools)**
sifatida quriladi. Loyiha alohida sahifalar to'plami emas, yaxlit
"agentlar ekotizimi" bo'ladi — keys nomining o'zi shuni talab qiladi.

---

## 2. Rollar

| Rol | Kim | Nimalarni ko'radi |
|---|---|---|
| **Talaba** | Universitet talabasi | O'z topshiriqlari, jadvali, to'lov holati, arizalari, ochiq hujjatlar, adabiyotlar |
| **O'qituvchi** | Fan o'qituvchisi | O'z fanlari materiallari, guruh topshiriqlari, davomat belgilash, hujjat topshirish |
| **Tyutor** | Guruh kuratori | O'z guruhi talabalari: to'lov holati, davomat, kampusda mavjudlik, arizalar |
| **Ma'muriy xodim** | Dekanat / registrar | Ichki hujjatlar, buyruqlar, hujjat aylanmasi, o'qituvchilar davomati, fakultet statistikasi |
| **Admin** | Tizim boshqaruvchisi | Foydalanuvchilar, hujjatlar, rollar, demo ma'lumotlar boshqaruvi |

Qoidalar:
- Har bir hujjat/ma'lumotda `kirish_darajasi` tegi bor; qidiruv va agent javobi
  faqat ruxsat etilgan doirada ishlaydi.
- Talaba boshqa talabaning ma'lumotini (to'lov, joylashuv) hech qachon ko'rmaydi.
- Tyutor faqat o'z guruhini, dekanat faqat o'z fakultetini ko'radi.
- O'qituvchining davomat ma'lumotini faqat dekanat/admin ko'radi (o'qituvchilar
  bir-birini ko'rmaydi).

---

## 3. Modullar va funksiyalar

### 3.1. Autentifikatsiya va rol boshqaruvi **[MVP]**
**Nima qiladi:** login/parol bilan kirish, sessiya, rol asosidagi kirish (RBAC).
**Logika:**
- Demo uchun oldindan yaratilgan foydalanuvchilar (har rol uchun 1-2 ta).
- Har so'rovda backend foydalanuvchi rolini va doirasini (guruh/fakultet) tekshiradi.
- Rol almashtirib demo qilish oson bo'lishi uchun tez "rol tanlash" ekrani.

### 3.2. AI agent yadrosi (chat) **[MVP]** — keysning markazi
**Nima qiladi:** har rol uchun moslashgan suhbat interfeysi. Agent savolga javob
berish uchun quyidagi vositalarni o'zi tanlab chaqiradi (tool calling):

| Vosita | Nima qiladi | Kimga ochiq |
|---|---|---|
| `hujjat_qidir` | RAG: hujjatlar bazasidan rol filtri bilan qidiradi | hamma (o'z doirasida) |
| `hujjat_rezyume` | Tanlangan hujjatni qisqartirib beradi | hamma |
| `tarjima_qil` | Matn/bo'lakni foydalanuvchi tiliga o'giradi | hamma |
| `jadval_kor` | Dars jadvalini o'qiydi (guruh/o'qituvchi/xona kesimida) | hamma |
| `tolov_holati` | Kontrakt to'lov holatini qaytaradi | talaba (o'ziniki), tyutor (guruhi) |
| `mavjudlik_tekshir` | Turniket logi + jadval asosida kampusdagi holat | tyutor, dekanat |
| `davomat_kor` | Talaba davomat yozuvlarini qaytaradi | o'qituvchi, tyutor, dekanat |
| `oqituvchi_davomat` | O'qituvchilarning kelish/dars o'tish holati | dekanat, admin |
| `ariza_holati` | Hujjat/ariza aylanmasidagi statusni qaytaradi | yuboruvchi + qabul qiluvchi |

**Logika:**
- Rolga qarab tizim prompti almashadi (talaba — oddiy til, tushuntirish;
  o'qituvchi — umumlashtirish; tyutor — guruh monitoring; xodim — hujjat aylanmasi).
- Agent ruxsati yo'q vositani chaqira olmaydi (**backend darajasida bloklanadi**,
  faqat promptda emas!).
- Har javobda manba ko'rsatiladi: hujjat nomi + bo'lim, yoki ma'lumot manbasi
  (masalan: "Manba: turniket logi, 10:02").
- Har javob ostida ogohlantirish: "AI javobi universitetning rasmiy hujjati
  hisoblanmaydi" (keys cheklovi talabi).

### 3.3. Hujjatlar bazasi + RAG qidiruv **[MVP]**
**Nima qiladi:** universitet hujjatlarini saqlaydi va ular ustidan semantik qidiruv.
**Logika:**
- Hujjat yuklanadi → til aniqlanadi → `kirish_darajasi` va `turi` teglanadi →
  500–1000 tokenli bo'laklarga bo'linadi → embedding → vektor bazaga yoziladi.
- Qidiruvda avval rol filtri, keyin semantik o'xshashlik.
- Demo korpus (o'zimiz tayyorlaymiz, ~15–20 hujjat): syllabus, topshiriqlar,
  ichki tartib nizomi, buyruqlar, dars jadvali, 2–3 ta inglizcha/ruscha maqola
  yoki darslik bo'limi.

### 3.4. Summarizatsiya **[MVP]**
**Nima qiladi:** uzun hujjat/topshiriq/buyruqning asosiy mazmunini qisqartirib beradi.
**Logika:**
- Rolga mos rakurs: talabaga — "nima qilishim kerak, qachongacha";
  o'qituvchiga — "asosiy bandlar"; xodimga — "sana, raqam, ijrochilar".
- Chatdan ham ("shu hujjatni qisqartir"), hujjat ko'rish oynasidan ham
  ("Rezyume" tugmasi) chaqiriladi.

### 3.5. Ko'p tilli adabiyot moduli **[P1]**
**Nima qiladi:** chet tilidagi adabiyotni foydalanuvchi tiliga o'girib beradi,
**originalni har doim saqlab va ko'rsatib**.
**Logika:**
- Yonma-yon ko'rinish: chapda original, o'ngda tarjima, paragraflar bog'langan.
- Atamalar himoyasi: muhim terminlar tarjimada qavs ichida originalda qoladi —
  "mashinaviy o'qitish (machine learning)". Fan bo'yicha lug'at yuritish mumkin **[?]**.
- Tarjima keshda saqlanadi (bir hujjat qayta-qayta tarjima qilinmaydi).
- Tillar aro qidiruv: o'zbekcha savol → inglizcha manbadan ham topadi
  (ko'p tilli embedding), javob o'zbekcha + sitata originalda.
- Original hech qachon o'zgartirilmaydi/almashtirilmaydi — tarjima alohida qatlam.

### 3.6. Kontrakt to'lovlari moduli **[P1]** — (chek muammosi)
**Muammo:** talaba kontraktni to'lagan bo'lsa ham tyutor chek so'raydi —
talaba har safar bank ilovasiga/qog'oz chekka qaytadi.
**Nima qiladi:**
- **Talaba:** o'z to'lov holatini ko'radi — jami kontrakt, to'langan, qoldiq,
  to'lovlar tarixi (sana, summa, chek raqami). Chekni PDF/rasm ko'rinishida
  ochib ko'rsatishi mumkin.
- **Tyutor:** guruh bo'yicha dashboard — kim to'lagan / qisman / qarzdor,
  oxirgi to'lov sanasi. Endi chek so'rash o'rniga tizimga qaraydi.
- **Chek yuklash:** to'lov avtomatik tushmagan holatda talaba chekni o'zi
  yuklaydi, tyutor "tasdiqlash" tugmasi bilan qabul qiladi **[?]**.
- **Agent integratsiyasi:** talaba: "kontraktimdan qancha qoldi?";
  tyutor: "guruhimda kimlar qarzdor?" — `tolov_holati` vositasi orqali.
**Logika:**
- Hackathonda: sintetik to'lov yozuvlari (demo Click/Payme tranzaksiyalari).
- Taqdimotda: "real hayotda Click API bilan integratsiya" (hackathon hamkori
  Click bo'lgani uchun kuchli argument).
- Maxfiylik: talaba faqat o'zini, tyutor faqat o'z guruhini ko'radi.

### 3.7. Talaba davomati va kampusda mavjudlik **[P1]**
**Muammo:** tyutor/dekanat talabaning universitetda bor-yo'qligini bilmaydi;
davomat qog'ozda yoki tarqoq.
**Nima qiladi:**
- **Binoda/binoda emas:** turniket (kirish-chiqish) loglari asosida joriy holat:
  "Binoda (10:02 da kirgan)" yoki "Binoda emas (13:40 da chiqqan)".
- **Qaysi xonada (xulosa sifatida):** joriy vaqt + dars jadvali kesishmasi:
  "Hozir 3-juftlik, 214-guruh 214-xonada 'Ma'lumotlar bazasi' darsida — talaba
  o'sha yerda bo'lishi kerak". Davomat belgilangan bo'lsa — "tasdiqlangan".
- **Davomat belgilash:** o'qituvchi dars boshida ro'yxatni ochib bir klik bilan
  belgilaydi — mavjudlik xulosasini tasdiqlovchi manba.
- **Tyutor ko'rinishi:** guruh ro'yxati: kim binoda, kim darsda (tasdiqlangan),
  kim yo'q. Fakultet kesimida agregat: "bugun davomat 87%".
- **Agent integratsiyasi:** "Aliyev hozir universitetdami?" → "Ha, 10:02 da
  kirgan, jadval bo'yicha 214-xonada, davomatda belgilangan".
**Logika va chegaralar:**
- Hammasi **sintetik** loglar bilan (demo turniket yozuvlari generatsiya qilinadi).
- Real indoor-pozitsiyalash (Wi-Fi/beacon) qurilmaydi — kontseptual kengaytma **[P2]**.
- **Ramka:** bu "kuzatuv" emas, "davomat va xavfsizlik vositasi". Faqat vakolatli
  rollar ko'radi; ochiq interfeysda individual joylashuv ko'rsatilmaydi.
- Xona darajasi — qat'iy fakt emas, jadvalga asoslangan **xulosa**; interfeysda
  "jadval bo'yicha" deb belgilanadi.

### 3.8. O'qituvchilar davomati **[P1]** — (yangi)
**Muammo:** dekanat o'qituvchining darsga kelgan-kelmaganini, dars o'tilgan-
o'tilmaganini tezkor bilmaydi; hisobot qo'lda yig'iladi.
**Nima qiladi:**
- **Kelish nazorati:** o'qituvchi ham turniketdan o'tadi — binoga kirgan vaqti
  qayd etiladi (talabalar bilan bir xil mexanizm, `TurnstileLog` umumiy).
- **Dars o'tilishi nazorati:** jadval bo'yicha o'qituvchining darsi bor paytda:
  - binoga kirmagan bo'lsa → **"dars xavf ostida"** ogohlantirishi dekanatga
    (bildirishnoma sifatida ham boradi);
  - davomat belgilagan bo'lsa → "dars o'tilmoqda (tasdiqlangan)";
  - binoda, lekin davomat belgilanmagan → "aniqlashtirish kerak".
- **Kechikish:** dars boshlanishidan keyin kirgan bo'lsa — "kechikkan" belgisi.
- **Dekanat dashboardi:** bugungi kesim (kim keldi/kelmadi/kechikdi, qaysi
  darslar o'tildi) + oylik svod (o'qituvchi bo'yicha davomat foizi, o'tilgan/
  qoldirilgan darslar) — hisobot uchun eksport **[P2]**.
- **Agent integratsiyasi:** dekanat: "bugun qaysi o'qituvchilar darsga
  kelmagan?" → `oqituvchi_davomat` vositasi javob beradi.
**Logika:**
- Talaba mavjudligi bilan bitta mexanizm (turniket + jadval kesishmasi) —
  alohida infratuzilma kerak emas, faqat rol boshqacha.
- Maxfiylik: o'qituvchi davomatini faqat dekanat/admin ko'radi; o'qituvchi
  o'zining ma'lumotini ko'ra oladi.

### 3.9. Hujjat almashinuvi (ariza va hujjat aylanmasi) **[P1]** — (yangi)
**Muammo:** talaba ma'lumotnoma/ariza uchun dekanatga boradi, o'qituvchi hisobotni
qog'ozda topshiradi, xodim hujjatning kimda turganini bilmaydi.
**Nima qiladi:**
- **Ariza yuborish (talaba):** tayyor shablonlar asosida — ma'lumotnoma so'rovi,
  akademik ta'til, qayta topshirish, turar joy va h.k. Ariza dekanatga tushadi.
- **Hujjat topshirish (o'qituvchi):** hisobot, ish reja, baholash qaydnomasi
  kabi hujjatlarni dekanatga elektron topshirish.
- **Hujjat yo'naltirish (xodim):** buyruq/xat/topshiriqni tegishli rol yoki
  shaxsga yuborish, ijro muddati bilan.
- **Status zanjiri:** `yuborildi → ko'rildi → ijroda → tasdiqlandi / rad etildi
  (sabab bilan)` — har o'zgarish tarixda saqlanadi, ikkala tomon ham ko'radi.
- **Real vaqtda kuzatish:** talaba arizasining qayerda turganini ko'radi —
  "dekanatga borib so'rash" o'rniga.
- **Agent integratsiyasi:** "arizam qayerda?" → `ariza_holati`; xodim uchun:
  "ijro muddati o'tgan hujjatlar qaysi?" Kelgan hujjatni agent rezyume qilib
  beradi (3.4 bilan bog'lanadi).
**Logika:**
- Bu FinTech keysidagi "arizalar va real vaqt statusi" naqshining o'zi —
  universitetga ko'chirilgan varianti; hakamlarga tanish va tushunarli.
- Imzo/muhr masalasi hackathonda soddalashtiriladi: "tasdiqlash" tugmasi =
  shartli imzo; real ERI (elektron raqamli imzo) integratsiyasi — kontsept **[P2]**.
- Har bir status o'zgarishi bildirishnoma yaratadi (3.10 bilan bog'lanadi).

### 3.10. Bildirishnomalar markazi **[P1]** — (ko'tarildi: P2 → P1)
**Nima qiladi:** tizim ichidagi yagona bildirishnoma markazi (qo'ng'iroqcha
belgisi + ro'yxat + o'qildi/o'qilmadi holati).
**Triggerlar (kim nimadan xabar oladi):**

| Hodisa | Kimga |
|---|---|
| Topshiriq deadline'i yaqinlashdi (3 kun / 1 kun qolganda) | talaba |
| Yangi topshiriq/material qo'shildi | talaba (guruh bo'yicha) |
| Kontrakt bo'yicha qarzdorlik / to'lov muddati | talaba, tyutor |
| To'lov cheki yuklandi (tasdiqlash kerak) | tyutor |
| Ariza/hujjat statusi o'zgardi | yuboruvchi |
| Yangi ariza/hujjat keldi | qabul qiluvchi (dekanat/o'qituvchi) |
| Ijro muddati o'tayapti/o'tdi | ijrochi + yuboruvchi |
| O'qituvchi darsga kelmadi ("dars xavf ostida") | dekanat |
| Yangi buyruq e'lon qilindi | tegishli rollar |

**Logika:**
- Hackathonda tizim ichida (in-app), sahifa yangilanishida yoki qisqa polling
  bilan. Real push/SMS/Telegram-bot — kontseptual kengaytma **[P2]**.
- Har bildirishnoma tegishli obyektga havola qiladi (bosilsa — o'sha ariza/
  topshiriq/dashboard ochiladi).
- Agent ham foydalanadi: "menda yangi nima bor?" → o'qilmagan bildirishnomalar
  asosida qisqa svod.

### 3.11. Boshqaruv paneli (admin) **[P1]**
**Nima qiladi:** foydalanuvchilar va rollarni boshqarish, hujjat yuklash/teglash,
demo ma'lumotlarni qayta yuklash (**demo reset tugmasi** — taqdimot oldidan
bir bosishda hamma sintetik ma'lumot boshlang'ich holatga qaytadi).

---

## 4. Ma'lumotlar modeli (asosiy obyektlar)

- **User**: id, ism, rol, guruh_id / fakultet_id, til
- **Group**: id, nomi, tyutor_id, fakultet_id
- **Document**: id, nomi, turi (syllabus/buyruq/topshiriq/adabiyot), til,
  kirish_darajasi, fayl, yuklangan_sana
- **Chunk**: document_id, matn, embedding, tartib
- **Translation**: chunk_id/document_id, til, tarjima_matn (original o'zgarmaydi)
- **Assignment**: fan, guruh, tavsif, deadline, o'qituvchi_id
- **Schedule**: guruh_id, fan, xona, kun, juftlik, o'qituvchi_id
- **Contract**: talaba_id, jami_summa, o'quv_yili
- **Payment**: talaba_id, summa, sana, chek_raqami, chek_fayl, holat
  (avtomatik/yuklangan/tasdiqlangan), o'quv_yili
- **TurnstileLog**: user_id (talaba **ham o'qituvchi ham**), vaqt,
  yo'nalish (kirdi/chiqdi) — sintetik
- **Attendance**: talaba_id, schedule_id, sana, holat (bor/yo'q/kech),
  belgilagan_oqituvchi_id
- **ClassSession**: schedule_id, sana, holat (o'tildi/qoldirildi/aniqlashtirish
  kerak), o'qituvchi_kelgan_vaqti — o'qituvchi davomati uchun
- **FlowDocument**: id, turi (ariza/hisobot/buyruq/xat), shablon_id, yuboruvchi_id,
  qabul_qiluvchi (rol yoki user_id), matn/fayl, ijro_muddati, holat
- **FlowHistory**: flow_document_id, holat, izoh, vaqt, kim_ozgartirdi
- **Notification**: user_id, turi, matn, havola (obyekt turi + id), o'qilgan,
  vaqt

---

## 5. Maxfiylik va keys cheklovlariga moslik

- Barcha shaxsiy ma'lumotlar — **faqat sintetik/demo** (keys talabi).
- Rol asosidagi kirish backend darajasida (promptda emas) majburlanadi.
- AI javoblari "rasmiy hujjat emas" ogohlantirishi bilan beriladi.
- Mavjudlik/davomat: individual ma'lumot faqat vakolatli rolga; ochiq
  interfeysda faqat agregatlar. O'qituvchi davomati — faqat dekanat/admin.
- Tarjima: original manba doim saqlanadi va ko'rsatiladi (akademik halollik).
- Hujjat aylanmasidagi "tasdiqlash" — demo shartli imzo, huquqiy kuchga ega
  hujjat sifatida taqdim etilmaydi.

---

## 6. Texnologiyalar

- **Frontend:** React / Next.js (chat + yonma-yon hujjat paneli + dashboardlar)
- **Backend:** Python FastAPI
- **Vektor baza:** Qdrant yoki Chroma (metadata filtri rol uchun kerak)
- **LLM:** provayderdan mustaqil modul — Yandex API bersa YandexGPT,
  bermasa zaxira provayder. Tool calling qo'llashi shart.
- **DB:** SQLite (hackathon uchun yetadi; SQLAlchemy orqali — keyin PostgreSQL
  ga o'tish oson)
- **Demo ma'lumot generatori:** sintetik talabalar, o'qituvchilar, to'lovlar,
  turniket loglari, jadval, arizalar yaratadigan skript

---

## 7. Ish tartibi

To'liq sessiyalarga bo'lingan reja — **`ISH_REJA.md`** faylida (14 sessiya,
har biri alohida kontekstda, aniq kirish/chiqish shartlari bilan).
Umumiy tartib: MVP yadro (skelet → seed → auth → RAG → agent → chat UI →
summarizatsiya) → P1 modullar (tarjima, to'lov, davomat×2, hujjat aylanmasi,
bildirishnoma, admin) → yakuniy integratsiya va taqdimot.

---

## 8. Demo ssenariysi (hakamlarga ko'rsatiladigan oqim, ~6 daqiqa)

1. **Talaba:** "Ma'lumotlar bazasidan topshiriq nima edi?" → agent topshiriq +
   deadline + manba. Inglizcha maqolani ochadi → yonma-yon tarjima →
   "asosiy xulosasi nima?" → o'zbekcha javob + inglizcha sitata.
2. **Talaba:** "Kontraktimdan qancha qoldi?" → summa + oxirgi chek.
   Ma'lumotnoma uchun ariza yuboradi → statusni kuzatadi.
3. **Tyutor:** guruh dashboardi — to'lovlar (kim qarzdor, chek bilan) va
   davomat. "Aliyev hozir universitetdami?" → agent: binoda, jadval bo'yicha
   214-xonada, davomat tasdiqlangan.
4. **Xodim (dekanat):** bildirishnoma keladi — "O'qituvchi X 3-juftlikdagi
   darsiga kelmagan". O'qituvchilar davomati dashboardini ochadi. Talabaning
   arizasini ko'rib "tasdiqlaydi" → talabaga bildirishnoma boradi.
   "Oxirgi buyruqni qisqartirib ber" → rezyume. Shu hujjatni talaba so'rasa —
   "kirish huquqi yo'q" (rol farqi jonli ko'rinadi).

---

## 9. Ochiq savollar (birga hal qilamiz — shu yerga yozing)

- [ ] Yandex qanday resurs beradi (API/model)? Aniqlanmagan — zaxira provayder tayyorlaymiz.
- [ ] Chekni tyutor tasdiqlashi kerakmi yoki avtomatik qabulmi? (3.6 [?])
- [ ] Atamalar lug'atini fan bo'yicha alohida yuritamizmi? (3.5 [?])
- [ ] Ariza shablonlari ro'yxati: qaysi 4-5 tasi demoda bo'ladi? (3.9)
- [ ] Interfeys tillari: o'zbek + rus + ingliz — uchalasi ham kerakmi?
- [ ] Mobil versiya kerakmi yoki faqat responsive veb yetadimi?
- [ ] Jamoada nechta kishi, kim qaysi qismni oladi?

---

*Qo'shimchalaringizni tegishli bo'lim ostiga yozing yoki yangi bo'lim oching.
Hujjat kelishilgach — `ISH_REJA.md` bo'yicha ish boshlanadi.*
