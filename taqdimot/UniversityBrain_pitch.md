# UniversityBrain — pitch-deck spetsifikatsiyasi

> Bu hujjat dizayner (Claude Design) uchun: 12 slaydlik investor-pitch'ning
> to'liq mazmuni. Har slaydda nima yozilishi, qaysi raqam ko'rsatilishi va
> vizual qanday bo'lishi aniq belgilangan. Matnni o'zgartirmasdan ko'chirish
> mumkin — u "bir satr" qoidasiga moslab yozilgan.

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
6. Har slayd **20–25 soniya** gapirishga mo'ljallangan (jami ~5 daqiqa).

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
  muammo→yechim kartochkalari flip bo'ladi, demo slaydda chat yozilib boradi,
  before/after taymlayn chapdan o'ngga jonlanadi.
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

**Speaker (25 s):** "Talaba nizomdan bitta bandni izlab yarim soat yo'qotadi.
Adabiyotning 95 foizi ingliz tilida. Tushunmagan bo'lsa — bitta o'qituvchiga
31 talaba, navbat. Universitet haqida so'rasa — mas'ul xodim yo'q, ertaga
keling. Bularning hammasi bitta kasallik: bilim bor, yo'l yo'q."

---

## Slayd 3 — `02 YECHIM` · UniversityBrain

**Vazifa:** 2-slayddagi har muammoga ko'zga ko'rinadigan javob. Ko'zgu
prinsipi — muammo chapda xira, yechim o'ngda yorqin.

**Sarlavha:** Universitet bilgan hamma narsa — **bitta suhbatda**.

**4 juftlik (muammo → yechim, strelka bilan):**

| Bugun | → | UniversityBrain bilan |
|---|---|---|
| 30 daqiqa hujjat titkilash | → | **25 soniyada** javob, manbasi bilan |
| Inglizcha manba — to'siq | → | Yonma-yon **tarjima + qisqa rezyume** |
| O'qituvchiga navbat | → | AI **24/7** birinchi javob beradi |
| "Kimdan so'rayman?" | → | So'rash shart emas — **o'zi topib beradi** |

**Vizual:** 4 qator, chap tomonda kulrang "bugun", o'ngda yashil/indigo
kartochka. Strelkalar animatsiya bilan. Yechim tomonidagi raqamlar yashil.

**Footer-satr:** Har muammoga — o'lchanadigan javob.

**Speaker (20 s):** "Yechim — har muammoga to'g'ridan-to'g'ri. 30 daqiqalik
izlanish 25 soniyaga tushadi. Inglizcha manba yonma-yon tarjima bilan ochiladi.
Navbat yo'q — AI kechasi ham javob beradi. Va endi 'kimdan so'rayman' degan
savolning o'zi qolmaydi."

---

## Slayd 4 — `03 MAHSULOT` · Javob o'ylab topilmaydi

**Vazifa:** ishonch mexanizmini ko'rsatish. AI'ga ishonmaydiganlar uchun slayd.

**Sarlavha:** Javob **o'ylab topilmaydi** — universitetdan **olinadi**.

**Zanjir (gorizontal, 4 qadam):**

`Savol` → `Kerakli vositani tanlaydi` → `Universitet ma'lumotidan oladi` → `Javob + manba`

**3 ta qisqa satr (zanjir ostida):**

- Har javobda manba: *hujjat + bo'lim* yoki *"turniket logi, 10:02"*
- 5 rol — har biri **faqat o'z ma'lumotini** ko'radi
- Cheklov ekranda emas — **serverda**

**Vizual:** o'ng tomonda jonli skrinshot (`screenshots/01_chat_talaba.png`) —
chat oynasi, manba chiplari ko'rinib tursin. Zanjir chapda, qadam-baqadam
yonib chiqadi.

**Footer-satr:** Ishonch = manba. Har javobda.

**Speaker (25 s):** "Bizning AI ChatGPT'dek 'ehtimol shunday' demaydi. U
universitetning hujjatlari va tizimlaridan javob oladi va manbasini yozadi:
qaysi hujjat, qaysi bo'lim, hattoki 'turniket logi, soat 10:02'. Talaba
dekanatning, dekanat talabaning shaxsiy ma'lumotini ko'ra olmaydi — bu
cheklov ekranda emas, serverda."

---

## Slayd 5 — `04 NEGA HOZIR` · Payt keldi

**Vazifa:** "nega bu 3 yil oldin qilinmadi, nega endi?" savoliga javob.

**Sarlavha:** Ikki yil oldin **qimmat** edi. Bugun — **arzon va tayyor**.

**3 katta raqam (yonma-yon):**

| **280×** | **208 OTM** | **1,5 mln** |
|---|---|---|
| AI narxi 2 yilda shuncha arzonlashdi (Stanford HAI, 2025) | HEMIS bilan raqamlashgan — ma'lumot allaqachon elektron | talaba — tariximizdagi eng katta avlod (Statistika agentligi) |

**Vizual:** 3 ustun, katta raqamlar indigo, count-up. Boshqa hech narsa.

**Footer-satr:** Texnologiya arzonlashdi + ma'lumot raqamlashdi = ayni payt.

**Speaker (20 s):** "Nega aynan hozir? AI ishlatish narxi ikki yilda 280
barobar tushdi. O'zbekistonning 208 universiteti HEMIS orqali allaqachon
raqamlashgan — ma'lumot tayyor turibdi. Va 1,5 million talaba — bu
tariximizdagi eng katta avlod. Uchchala eshik bir vaqtda ochildi."

---

## Slayd 6 — `05 DEMO` · "Arizam qayerda?"

**Vazifa:** bitta jonli hikoya. Eng esda qoladigan slayd.

**Sarlavha:** Bitta savol: **"Arizam qayerda?"**

**Ikki taymlayn (ustma-ust):**

**Bugun (kulrang, qizil belgilar):**
`Dekanatga bordi` → `Mas'ul yo'q` → `Ertaga keldi` → `Navbat` → **2 kun**

**UniversityBrain (indigo, yashil belgi):**
`Yozdi` → `Javob: holati, kim ko'rgani, manbasi` → **25 soniya**

**Katta taqqos (o'ngda yoki markazda):** **2 kun → 25 soniya**

**Vizual:** yuqori taymlayn xira/kulrang, pastkisi yorqin. Agar format
qo'llasa — pastki taymlaynda chat xabari yozilib chiqadi. 25 soniya —
jonli demoda o'lchangan haqiqiy vaqt, shuni speaker aytadi.

**Footer-satr:** 2 kunlik yugurish — 25 soniyalik suhbat bo'ldi.

**Speaker (25 s):** "Real ssenariy. Talaba ariza topshirgan, holatini
bilmoqchi. Bugun bu — dekanatga borish, mas'ulni topa olmaslik, ertaga yana
kelish. Ikki kun. UniversityBrain'da — bitta xabar: 25 soniyada holati, kim
ko'rgani va manbasi keladi. Bu raqam taxmin emas — jonli demoda o'lchaganmiz,
hozir ko'rsatamiz."

---

## Slayd 7 — `06 BOZOR` · TAM / SAM / SOM

**Vazifa:** bozor bor va o'lchanganini ko'rsatish. 3 raqam, 3 manba.

**Sarlavha:** Bozor: dunyoda **milliardlar**, uyda — **ochiq maydon**.

**3 doira (katta → kichik, ichma-ich yoki yonma-yon):**

| TAM | SAM | SOM |
|---|---|---|
| **$8,3 mlrd** | **$3,1 mln/yil** | **$450 ming/yil** |
| dunyoda ta'limdagi AI, 2030 (Grand View Research) | O'zbekistondagi 208 OTM × yillik litsenziya | 3 yilda 30 OTM — realistik ulush |

**Vizual:** klassik 3 doira, raqamlar indigo. Pastda kichik satr:
*"Keyingi qadam — Markaziy Osiyo: model tilga emas, tizimga bog'langan."*

**Footer-satr:** Boshlanish — O'zbekiston. Model — eksportga tayyor.

**Speaker (20 s):** "Dunyoda ta'limdagi AI bozori 2030-yilga borib 8,3
milliard dollar. Bizning maydonimiz — O'zbekistonning 208 universiteti,
yiliga 3,1 million dollarlik bozor. Uch yilda 30 universitet — 450 ming
dollar. Va model Markaziy Osiyoga bemalol ko'chadi."

---

## Slayd 8 — `07 BIZNES MODEL` · Oddiy SaaS

**Vazifa:** pul qayerdan kelishini bitta ekranda tushuntirish.

**Sarlavha:** Universitet to'laydi. Talabaga — **bepul**.

**Markazda bitta katta raqam:**

**$15 000 / OTM / yil**
*(litsenziya $9 000 + joriy qo'llab-quvvatlash $6 000 — narx taxmin,
pilotda aniqlanadi)*

**2 ta qisqa satr:**

- Bu — har talabaga yiliga **~$2** *(o'rtacha OTM ≈ 7 400 talaba)*
- O'rnatish oson: mavjud tizimlar ustiga qo'shiladi, almashtirmaydi

**Vizual:** bitta katta narx-kartochka markazda, "taxmin" belgisi halol
ko'rsatilgan (kichik amber chip). Ortiqcha jadval yo'q.

**Footer-satr:** Universitetga — xizmat, talabaga — bepul.

**Speaker (20 s):** "Model oddiy SaaS: universitet yiliga 15 ming dollar
to'laydi — bu har talabaga ikki dollar atrofida. Narx hozircha taxmin,
pilotda aniqlaymiz. Muhimi: biz HEMIS'ni almashtirmaymiz, ustiga
qo'shilamiz — o'rnatish og'riqsiz."

---

## Slayd 9 — `08 RAQOBAT` · Bo'shliqni to'ldiramiz

**Vazifa:** halol taqqoslash jadvali. Raqobatchini yomonlamaslik — farqni
ko'rsatish.

**Sarlavha:** Har birida **bittasi** bor. Bizda — **hammasi**.

**Jadval (✓ / ✕):**

| Imkoniyat | HEMIS | ChatGPT | Telegram-bot | **UniversityBrain** |
|---|---|---|---|---|
| Universitet ma'lumotiga ulangan | ✓ | ✕ | ✕ | **✓** |
| Savol-javob suhbati | ✕ | ✓ | ✕ | **✓** |
| Javobda manba ko'rsatadi | ✕ | ✕ | ✕ | **✓** |
| Rolga qarab cheklaydi | ✓ | ✕ | ✕ | **✓** |
| O'zbek tilida to'liq | ✓ | qisman | ✓ | **✓** |
| 24/7 javob beradi | ✕ | ✓ | qisman | **✓** |

**Vizual:** oxirgi ustun indigo fon bilan ajratilgan, ✓ lar yashil.
Qator nomlari sodda tilda, texnik so'zsiz.

**Footer-satr:** Biz hech kimni almashtirmaymiz — bo'shliqni to'ldiramiz.

**Speaker (20 s):** "HEMIS'da ma'lumot bor, lekin u bilan gaplashib
bo'lmaydi. ChatGPT gaplashadi, lekin universitetni bilmaydi va manba
ko'rsatmaydi. Telegram-botlar faqat e'lon tarqatadi. Biz shu uch dunyoni
birlashtirgan yagona yechimmiz."

---

## Slayd 10 — `09 NATIJA` · G'oya emas — mahsulot

**Vazifa:** traction. Hackathon uchun eng kuchli dalil — ishlab turgani.

**Sarlavha:** Bu prezentatsiya emas — **ishlayotgan tizim**.

**5 raqam (bir qatorda):**

| **281** | **10** | **5** | **25 s** | **3 til** |
|---|---|---|---|---|
| avtomatik test | aqlli vosita | rol | savoldan javobgacha | hujjat tarjimasi |

**Vizual:** pastda 3 ta kichik skrinshot lenta bo'lib turadi
(`02_dekanat_oqituvchilar.png`, `04_talaba_arizalar.png`,
`05_admin_statistika.png`) — brauzer ramkasida. Ustiga bosilganda demo
ko'rsatiladi degan taassurot.

**Footer-satr:** Hammasi GitHub'da — hozir jonli ko'rsatamiz.

**Speaker (25 s):** "Bu slaydlar ortida ishlab turgan tizim bor: 281
avtomatik test, 10 vosita, 5 rol — to'lovdan davomatgacha, arizadan
tarjimagacha. Savoldan javobgacha 25 soniya. Hammasi ochiq kodda, va biz
buni hozir jonli ko'rsatishga tayyormiz."

---

## Slayd 11 — `10 YO'L XARITASI` · Uch qadam

**Vazifa:** kelajak reja aniq va bosqichli ekanini ko'rsatish.

**Sarlavha:** Pilotdan — **milliy miqyosgacha**.

**3 bosqich (gorizontal yo'l):**

| 1 · Pilot | 2 · Integratsiya | 3 · Miqyos |
|---|---|---|
| 1 fakultet, 3 oy | HEMIS bilan rasmiy ulanish | 30 OTM / 3 yil |
| natijani o'lchaymiz: javob vaqti, qamrov | ma'lumot avtomatik yangilanadi | Markaziy Osiyoga chiqish |

**Vizual:** chapdan o'ngga yo'l chizig'i, 3 nuqta, hozirgi holat "Pilotga
tayyor" belgisi bilan 0-nuqtada.

**Footer-satr:** Har bosqichning o'z o'lchanadigan natijasi bor.

**Speaker (20 s):** "Reja uch qadam: avval bitta fakultetda uch oylik pilot —
javob vaqti va qamrovni o'lchaymiz. Keyin HEMIS bilan rasmiy integratsiya —
ma'lumot o'z-o'zidan yangilanadi. Uch yilda — 30 universitet va Markaziy
Osiyo bozori."

---

## Slayd 12 — `11 JAMOA & SO'ROV` · Bizga nima kerak

**Vazifa:** yakun. Kim qilgani va nima so'ralayotgani — bitta ekranda.

**Chap yarim — Jamoa:**

- **Mannonov Sarabek** — asoschi, full-stack + AI
- Bir kishi, 15 bosqich, 281 test — **ijro tezligi isbotlangan**

**O'ng yarim — So'rov (Ask):**

- 🏆 NEXUS30 g'olibligi
- 🎓 Pilot uchun **1 fakultet**
- ☁️ Yandex Cloud resurslari
- 🧭 EdTech mentorlik

**Pastda katta yakuniy satr:**
**Universitetning miyasi tayyor. Unga birinchi auditoriya kerak.**

**Vizual:** ikki ustun, o'ng tomonda 4 qisqa so'rov-chip. Yakuniy satr
titul uslubida, logo bilan.

**Speaker (20 s):** "Men bu tizimni yolg'iz, 15 bosqichda, har qadamini test
bilan mustahkamlab qurdim. Endi bizga kod emas — birinchi auditoriya kerak:
bitta pilot fakultet, Yandex resurslari va mentorlik. Universitetning miyasi
tayyor. Uni ishga tushiraylik."

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
