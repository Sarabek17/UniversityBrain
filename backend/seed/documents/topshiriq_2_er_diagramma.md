# Topshiriq 2 — ER-diagramma loyihalash

**Fan:** Ma'lumotlar bazasi
**Guruhlar:** AT-24-01, AT-24-02
**O'qituvchi:** Umarov Sherzod
**Maksimal ball:** 10
**Topshirish muddati:** e'lon qilingan kundan boshlab 3 hafta ichida (aniq
sana UniAgent tizimidagi topshiriq yozuvida ko'rsatilgan).

## Vazifa

"Universitet o'quv jarayoni" predmet sohasi uchun to'liq ER-diagramma
(Entity-Relationship model) loyihalang. Diagramma keyinchalik relyatsion
sxemaga aylantiriladigan darajada aniq bo'lishi kerak.

## Majburiy talablar

1. Kamida **6 ta obyekt (entity)** bo'lsin. Tavsiya etiladigan to'plam:
   - Talaba, Guruh, O'qituvchi, Fan, Dars jadvali, Baho.
   - Xohlovchilar qo'shimcha obyektlar (Xona, Kafedra, Topshiriq) kiritishi
     mumkin.
2. Har bir obyekt uchun atributlar ko'rsatilsin, birlamchi kalit (PK) alohida
   belgilansin.
3. Bog'lanishlar kardinalligi aniq ko'rsatilsin: 1:1, 1:N yoki M:N.
   - Diagrammada kamida bitta **M:N** bog'lanish bo'lishi shart (masalan,
     Talaba - Fan) va uni oraliq jadval orqali yechish ko'rsatilsin.
4. Har bir bog'lanish uchun 1-2 gaplik izoh yozilsin ("bitta guruhda ko'p
   talaba o'qiydi" kabi).
5. Diagramma asosida hosil bo'ladigan jadvallar ro'yxati (jadval nomi +
   ustunlar + kalitlar) alohida sahifada keltirilsin.

## Vositalar

draw.io (diagrams.net), dbdiagram.io yoki istalgan boshqa vosita. Qo'lda
chizilgan va skaner qilingan diagramma ham qabul qilinadi, agar aniq o'qilsa.

## Topshirish formati

- `topshiriq2_FAMILIYA.pdf` — diagramma + jadvallar ro'yxati;
- manba fayl (`.drawio`, `.png` yoki boshqa) ilova qilinsin;
- UniAgent tizimi orqali yuklanadi.

## Baholash mezonlari

| Mezon | Ball |
|---|---|
| 6+ obyekt, atributlar va PK to'g'ri | 3 |
| Kardinalliklar to'g'ri qo'yilgan | 2 |
| M:N bog'lanish va uning yechimi | 2 |
| Relyatsion sxemaga o'tkazish to'g'ri | 2 |
| Rasmiylashtirish va izohlar | 1 |

**Eslatma:** ikki talabaning bir xil diagrammasi aniqlansa, ikkalasiga ham
0 ball qo'yiladi (syllabusdagi plagiat qoidasi).
