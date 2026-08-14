# Topshiriq 3 — Normalizatsiya

**Fan:** Ma'lumotlar bazasi
**Guruhlar:** AT-24-01, AT-24-02
**O'qituvchi:** Umarov Sherzod
**Maksimal ball:** 10
**Topshirish muddati:** e'lon qilingan kundan boshlab 4 hafta ichida (aniq
sana UniAgent tizimidagi topshiriq yozuvida ko'rsatilgan).

## Berilgan jadval

Quyidagi yagona "katta" jadval berilgan (denormalizovan holat):

```
NATIJALAR (
    talaba_id,
    talaba_ismi,
    guruh_nomi,
    guruh_tyutori,
    fan_nomi,
    fan_krediti,
    oqituvchi_ismi,
    oqituvchi_kafedrasi,
    oqituvchi_telefoni,
    baho,
    baho_sanasi,
    xona_raqami
)
```

Bitta talaba ko'p fandan baho oladi, bitta fanni ko'p talaba o'qiydi, bitta
o'qituvchi bir nechta fan o'tishi mumkin.

## Vazifa

1. Jadvaldagi barcha **funksional bog'liqliklarni** yozib chiqing
   (masalan: `talaba_id -> talaba_ismi, guruh_nomi`).
2. Jadval nima uchun 2NF va 3NF talablarini buzayotganini aniq misollar bilan
   tushuntiring (qanday anomaliyalar yuzaga keladi: qo'shish, o'chirish,
   yangilash anomaliyalari).
3. Jadvalni bosqichma-bosqich normallashtiring:
   - **1NF** — atomar qiymatlar, takrorlanuvchi guruhlarsiz;
   - **2NF** — qisman bog'liqliklarni yo'qotish;
   - **3NF** — tranzitiv bog'liqliklarni yo'qotish.
   Har bosqichda hosil bo'lgan jadvallar to'plamini (nomi, ustunlari, PK/FK)
   yozing va qaysi bog'liqlik sababli ajratganingizni izohlang.
4. Yakuniy 3NF sxema uchun `CREATE TABLE` SQL skriptlarini yozing (FOREIGN KEY
   cheklovlari bilan).

## Topshirish formati

- `topshiriq3_FAMILIYA.pdf` — 1-3-bandlar (matn va jadvallar);
- `topshiriq3_FAMILIYA.sql` — 4-band skripti;
- UniAgent tizimi orqali yuklanadi.

## Baholash mezonlari

| Mezon | Ball |
|---|---|
| Funksional bog'liqliklar to'liq va to'g'ri | 2 |
| Anomaliyalar to'g'ri tushuntirilgan | 2 |
| 1NF-2NF-3NF bosqichlari asoslangan | 4 |
| SQL skript ishlaydi va cheklovlar to'g'ri | 2 |
