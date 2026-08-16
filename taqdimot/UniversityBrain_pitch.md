# UniversityBrain — pitch-deck spetsifikatsiyasi (6 slayd)

> Bu hujjat dizayner (Claude Design) uchun: 6 slaydlik investor-pitch'ning
> to'liq mazmuni. Har slaydda nima yozilishi, qaysi raqam ko'rsatilishi va
> vizual qanday bo'lishi aniq belgilangan. Matn "bir satr" qoidasiga moslab
> yozilgan — o'zgartirmasdan ko'chirish mumkin.

---

## Loyiha bir abzatsda (dizayner uchun kontekst)

**UniversityBrain** — universitetning "miyasi". Talaba, o'qituvchi, tyutor va
dekanat **bitta AI yordamchi** bilan oddiy tilda gaplashadi: "Arizam qayerda?",
"Kontraktim qancha qoldi?", "Bu nizomda nima deyilgan?". Yordamchi javobni
o'ylab topmaydi — universitetning hujjatlari va tizimlaridan **oladi** va har
javobda **manbasini ko'rsatadi**. Har rol faqat o'z doirasidagi ma'lumotni
ko'radi. Bu g'oya emas — **ishlab turgan mahsulot**: 281 avtomatik test,
10 aqlli vosita, 5 rol, jonli demo. NEXUS30 hackathoni, EdTech trek (Yandex).

---

## Qat'iy qoidalar (har slaydga tegishli)

1. **Bir satr qoidasi** — har fikr bitta qisqa satr, maksimum 8 so'z.
   Uzun gap slaydga chiqmaydi, u speaker-notega ketadi.
2. **Jargon taqiqlanadi** — slaydda "RAG", "embedding", "backend", "API"
   yozilmaydi. Buning o'rniga: "universitet ma'lumotidan oladi",
   "cheklov serverda".
3. **Har raqam manbali** — raqam ostida kichik harflar bilan manba yoziladi.
   Taxmin bo'lsa — ochiq "taxmin" deb belgilanadi.
4. **Bir slayd — bitta xabar** — slaydga qarab 3 soniyada nima demoqchi
   ekanimiz tushunilishi kerak.
5. **Auditoriya — hakam va investor**, dasturchi emas. Texnik bilimi yo'q
   odam ham har slaydni tushunishi shart.
6. Har slayd **30–40 soniya** gapirishga mo'ljallangan (jami ~4 daqiqa).

---

## Dizayn tizimi

- **Format:** 16:9, keng bo'sh joylar, havo ko'p.
- **Fon:** och (#FAFAFA), kontent oq kartochkalarda, yumshoq soya,
  radius katta (16–24px).
- **Aksent rang:** indigo/binafsha `#4F46E5` (miya, neyron tarmoq motivi).
  Muammo raqamlari — qizil/amber, yechim raqamlari — yashil.
- **Kicker (har slayd tepasida, mayda mono harflar):**
  masalan `MUAMMO · VAQT YO'QOTISH`. O'ng yuqorida slayd raqami: `01 MUAMMO`.
- **Footer (har slayd pastida):** chapda bitta xulosa-satr (quyida har slayd
  uchun berilgan), o'ngda `UNIVERSITYBRAIN · NEXUS30`.
- **Interaktivlik** (format qo'llasa): raqamlar count-up bilan chiqadi,
  muammo→yechim strelkalari jonlanadi, demo slaydda chat yozilib boradi.
- **Logo g'oyasi:** miya konturi + bitiruv qalpog'i, neyron nuqta-chiziqlar.
- **Skrinshotlar:** `taqdimot/screenshots/` papkasida 5 ta jonli ekran bor —
  brauzer ramkasiga solib ishlatilsin.

---

# SLAYDLAR

---

## Slayd 1 — Titul

**Vazifa:** 5 soniyada esda qolish. Ortiqcha hech narsa yo'q.

- Markazda katta: **UniversityBrain**
- Tagline: **Universitetning miyasi. Har savolga — bitta javob.**
- Chiplar: `NEXUS30 · EDTECH TREK · YANDEX`
- Pastda: Jamoa — Mannonov Sarabek

**Vizual:** markazda logo, orqa fonda juda och neyron chiziqlar tarmog'i.
Skrinshot yo'q, jadval yo'q — faqat nom va tagline.

**Speaker (20 s):** "Universitetda har savolning javobi bor — lekin unga
yetguncha soatlab, ba'zan kunlab kutiladi. Biz kutishni bekor qilamiz.
Bu — UniversityBrain, universitetning miyasi."

---

## Slayd 2 — `01 MUAMMO` · Javob kutish odatga aylangan

**Vazifa:** hakam har kartochkada o'zini tanisin. Hook + 4 muammo, har birida
bitta raqam.

**Sarlavha:** Bilim universitetda bor. Unga **yo'l yo'q**.

**4 kartochka** (ikon + bitta satr + raqam + manba):

| # | Muammo (bitta satr) | Katta raqam | Raqam osti izoh (mayda) |
|---|---|---|---|
| 📄 | Kerakli band — ming sahifa ichida | **~19%** | ish vaqti ma'lumot izlashga ketadi (McKinsey) |
| 🌍 | Ilmiy adabiyot talaba tilida emas | **~95%** | ilmiy maqolalar ingliz tilida (Scopus) |
| ⏳ | Tushunmagan talaba navbat kutadi | **31 : 1** | bitta o'qituvchiga 31 talaba (Statistika agentligi, 2024/25) |
| 🚪 | "Mas'ul xodim yo'q — ertaga keling" | **4 manba** | HEMIS, Telegram, e'lonlar taxtasi, dekanat — javob sochilgan |

**Vizual:** 2×2 kartochka to'ri. Raqamlar qizil/amber, count-up bilan chiqadi.

**Footer-satr:** To'rt muammo — bitta ildiz: bilim bor, unga tez yo'l yo'q.

**Speaker (30 s):** "Talaba nizomdan bitta bandni izlab yarim soat yo'qotadi.
Adabiyotning 95 foizi ingliz tilida. Tushunmagan bo'lsa — bitta o'qituvchiga
31 talaba, navbat. Universitet haqida so'rasa — mas'ul xodim yo'q, ertaga
keling. Bularning hammasi bitta kasallik: bilim bor, yo'l yo'q."

---

## Slayd 3 — `02 YECHIM` · UniversityBrain

**Vazifa:** har muammoga ko'zga ko'rinadigan javob + qanday ishlashi bitta
zanjirda. Ko'zgu prinsipi — muammo chapda xira, yechim o'ngda yorqin.

**Sarlavha:** Universitet bilgan hamma narsa — **bitta suhbatda**.

**4 juftlik (muammo → yechim, strelka bilan):**

| Bugun | → | UniversityBrain bilan |
|---|---|---|
| 30 daqiqa hujjat titkilash | → | **25 soniyada** javob, manbasi bilan |
| Inglizcha manba — to'siq | → | Yonma-yon **tarjima + qisqa rezyume** |
| O'qituvchiga navbat | → | AI **24/7** birinchi javob beradi |
| "Kimdan so'rayman?" | → | So'rash shart emas — **o'zi topib beradi** |

**Pastda zanjir (bitta qator, 4 qadam):**

`Savol` → `Kerakli vositani tanlaydi` → `Universitet ma'lumotidan oladi` → `Javob + manba`

Zanjir ostida bitta satr: *Cheklov ekranda emas — serverda. 5 rol, har biri
faqat o'z ma'lumotini ko'radi.*

**Vizual:** 4 qator ko'zgu-juftlik (chap kulrang, o'ng indigo/yashil),
pastda gorizontal zanjir qadam-baqadam yonib chiqadi.

**Footer-satr:** Javob o'ylab topilmaydi — universitetdan olinadi.

**Speaker (35 s):** "Yechim — har muammoga to'g'ridan-to'g'ri: 30 daqiqalik
izlanish 25 soniyaga tushadi, inglizcha manba yonma-yon tarjima bilan
ochiladi, navbat yo'q — AI kechasi ham javob beradi. Eng muhimi: bizning AI
'ehtimol shunday' demaydi — javobni universitetning hujjatlari va
tizimlaridan oladi, manbasini yozadi: qaysi hujjat, qaysi bo'lim, hattoki
'turniket logi, 10:02'. Va har rol faqat o'z ma'lumotini ko'radi — bu
cheklov serverda."

---

## Slayd 4 — `03 ISBOT` · G'oya emas — ishlayotgan mahsulot

**Vazifa:** demo-hikoya + traction bitta ekranda. Eng esda qoladigan slayd.

**Sarlavha:** Bitta savol: **"Arizam qayerda?"**

**Ikki taymlayn (ustma-ust):**

**Bugun (kulrang, qizil belgilar):**
`Dekanatga bordi` → `Mas'ul yo'q` → `Ertaga keldi` → `Navbat` → **2 kun**

**UniversityBrain (indigo, yashil belgi):**
`Yozdi` → `Javob: holati, kim ko'rgani, manbasi` → **25 soniya**

**Pastda traction-qator (4 raqam):**

| **281** | **10** | **5** | **3 til** |
|---|---|---|---|
| avtomatik test | aqlli vosita | rol | hujjat tarjimasi |

**Vizual:** yuqori taymlayn xira, pastkisi yorqin; o'ngda bitta jonli
skrinshot (`screenshots/01_chat_talaba.png`) brauzer ramkasida. 25 soniya —
jonli demoda o'lchangan haqiqiy vaqt.

**Footer-satr:** Hammasi ishlab turibdi — hozir jonli ko'rsatamiz.

**Speaker (35 s):** "Real ssenariy: talaba ariza holatini bilmoqchi. Bugun bu
ikki kunlik yugurish. UniversityBrain'da — bitta xabar, 25 soniyada holati,
kim ko'rgani va manbasi keladi. Bu taxmin emas, jonli demoda o'lchangan. Va
bu prezentatsiya emas — ishlab turgan tizim: 281 avtomatik test, 10 vosita,
5 rol. Hozir jonli ko'rsatamiz."

---

## Slayd 5 — `04 IMKONIYAT` · Nega hozir va qancha turadi

**Vazifa:** payt + bozor + model — bitta ekranda, uch blok.

**Sarlavha:** Ikki yil oldin **qimmat** edi. Bugun — **arzon va tayyor**.

**Yuqori qator — nega hozir (2 raqam):**

| **280×** | **208 OTM** |
|---|---|
| AI narxi 2 yilda shuncha arzonlashdi (Stanford HAI, 2025) | HEMIS bilan raqamlashgan — ma'lumot tayyor |

**O'rta qator — bozor (3 doira):**

| TAM **$8,3 mlrd** | SAM **$3,1 mln/yil** | SOM **$450 ming/yil** |
|---|---|---|
| dunyoda ta'limdagi AI, 2030 (Grand View Research) | O'zbekiston, 208 OTM | 3 yilda 30 OTM |

**Pastki qator — model (bitta satr):**

**$15 000 / OTM / yil** — har talabaga ~$2 *(narx taxmin, pilotda aniqlanadi)*.
Talabaga — bepul.

**Raqobat bir satrda (mayda, pastda):**
*HEMIS — ma'lumot bor, suhbat yo'q · ChatGPT — universitetni bilmaydi ·
Biz — ikkalasi birga, manba bilan.*

**Vizual:** uch gorizontal blok, raqamlar indigo, count-up. "Taxmin" — kichik
amber chip bilan halol belgilangan.

**Footer-satr:** Texnologiya arzonlashdi + ma'lumot raqamlashdi = ayni payt.

**Speaker (35 s):** "Nega hozir? AI narxi ikki yilda 280 barobar tushdi, 208
universitet HEMIS orqali allaqachon raqamlashgan. Bozor: dunyoda 8,3
milliard, uyda 208 OTM — yiliga 3,1 million dollar, uch yilda 30 OTM
realistik. Model oddiy: universitet yiliga 15 ming dollar to'laydi — har
talabaga ikki dollar, talabaga bepul. HEMIS'da ma'lumot bor, lekin suhbat
yo'q; ChatGPT gaplashadi, lekin universitetni bilmaydi. Biz — ikkalasi birga."

---

## Slayd 6 — `05 JAMOA & SO'ROV` · Bizga nima kerak

**Vazifa:** yakun. Kim qilgani, keyingi qadam va so'rov — bitta ekranda.

**Chap yarim — Jamoa:**

- **Mannonov Sarabek** — asoschi, full-stack + AI
- Bir kishi, 15 bosqich, 281 test — **ijro tezligi isbotlangan**

**O'ng yarim — So'rov (Ask):**

- 🏆 NEXUS30 g'olibligi
- 🎓 Pilot uchun **1 fakultet** (3 oy, natija o'lchanadi)
- ☁️ Yandex Cloud resurslari
- 🧭 EdTech mentorlik

**Pastda yo'l bitta satrda:**
`Pilot (1 fakultet)` → `HEMIS integratsiya` → `30 OTM / 3 yil`

**Yakuniy katta satr:**
**Universitetning miyasi tayyor. Unga birinchi auditoriya kerak.**

**Vizual:** ikki ustun, o'ngda 4 so'rov-chip, pastda mini yo'l chizig'i.
Yakuniy satr titul uslubida, logo bilan.

**Speaker (30 s):** "Men bu tizimni yolg'iz, 15 bosqichda, har qadamini test
bilan mustahkamlab qurdim. Yo'l aniq: bitta fakultetda pilot, keyin HEMIS
bilan integratsiya, uch yilda 30 universitet. Bizga kod emas — birinchi
auditoriya kerak: pilot fakultet, Yandex resurslari va mentorlik.
Universitetning miyasi tayyor. Uni ishga tushiraylik."

---

## Manbalar (slaydlardagi raqamlar)

| Raqam | Manba |
|---|---|
| 1,5 mln talaba · 208 OTM | O'zbekiston Statistika agentligi, 2024/25 o'quv yili |
| 49,6 ming professor-o'qituvchi → 31:1 nisbat | [kun.uz / Statistika agentligi, 2024/25](https://m.kun.uz/news/2025/11/27/oliy-talimda-ayol-professor-oqituvchilar-ulushi-46-foizga-yetdi) |
| ~95% ilmiy maqolalar ingliz tilida | [Scopus qamrovi tadqiqotlari](https://scispace.com/pdf/web-of-science-and-scopus-language-coverage-20wspx7xud.pdf) |
| ~19% ish vaqti ma'lumot izlashga | McKinsey Global Institute, "The social economy" |
| 280× — AI narxining pasayishi | Stanford HAI, AI Index Report 2025 |
| $8,3 mlrd — ta'limdagi AI bozori (2030) | Grand View Research, AI in Education Market |
| 25 soniya · 281 test · 10 vosita · 5 rol | Loyihaning o'zi (o'lchangan/hisoblangan) |
| $15 000/OTM/yil narxi | **Taxmin** — pilotda aniqlanadi (slaydda ham shunday belgilanadi) |

> Eslatma dizaynerga: manba yozuvlari slaydda kichik, xira harflar bilan
> raqam ostida turadi — ishonch beradi, lekin diqqatni tortmaydi.
