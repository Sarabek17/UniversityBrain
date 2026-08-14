# Topshiriq 4 — Python funksiyalar

**Fan:** Dasturlash asoslari
**Guruhlar:** AT-24-01, AT-24-02
**O'qituvchi:** Bekmurodov Alisher
**Maksimal ball:** 10
**Topshirish muddati:** e'lon qilingan kundan boshlab 2 hafta ichida (aniq
sana UniAgent tizimidagi topshiriq yozuvida ko'rsatilgan).

## Vazifa

Quyidagi 5 ta funksiyani Python tilida yozing. Har bir funksiya uchun:

- docstring (nima qilishi, parametrlari, qaytaruvchi qiymati);
- kamida 2 tadan tekshiruv misoli (`assert` yoki oddiy chaqiruv + izoh).

### 1. `ekub(a, b)`

Ikki natural sonning eng katta umumiy bo'luvchisini Evklid algoritmi bilan
hisoblasin. Sikl yoki rekursiya — talabaning tanlovi.

### 2. `palindrommi(matn)`

Berilgan matn palindrom ekanini (`True`/`False`) aniqlasin. Katta-kichik harf
va probellar hisobga olinmasin: `"Ana ona"` — palindrom.

### 3. `ikkinchi_eng_katta(sonlar)`

Ro'yxatdagi ikkinchi eng katta qiymatni qaytarsin. Takrorlanuvchi qiymatlar
bitta hisoblansin: `[7, 7, 5, 3]` uchun javob `5`. Ro'yxatda 2 tadan kam farqli
qiymat bo'lsa `None` qaytarsin. `sort()` dan foydalanmasdan yechish qo'shimcha
+1 ball beradi (jami ball 10 dan oshmaydi).

### 4. `soz_chastotasi(matn)`

Matndagi har bir so'z necha marta uchraganini lug'at (`dict`) ko'rinishida
qaytarsin. So'zlar kichik harfga keltirilsin, tinish belgilari olib tashlansin.
Masalan: `"Olma olma anor"` uchun `{"olma": 2, "anor": 1}`.

### 5. `kalkulyator(a, amal, b)`

`amal` parametri `"+"`, `"-"`, `"*"`, `"/"` qiymatlaridan biri bo'ladi.
Amalni bajarib natijani qaytarsin. Yechimda `if-elif` zanjiri o'rniga lug'at
(dictionary dispatch) ishlatilsin. Nolga bo'lishda `None` qaytarilsin va
ogohlantirish chop etilsin.

## Topshirish formati

- Bitta fayl: `topshiriq4_FAMILIYA.py`;
- fayl boshida izoh: F.I.Sh., guruh, sana;
- fayl ishga tushganda barcha tekshiruv misollari xatosiz o'tishi kerak;
- UniAgent tizimi orqali yuklanadi.

## Baholash mezonlari

| Mezon | Ball |
|---|---|
| Har bir ishlaydigan funksiya (5 x 1.5) | 7.5 |
| Docstring va tekshiruv misollari | 1.5 |
| Kod uslubi (nomlash, sodda yechim) | 1 |

Kechikish siyosati syllabusda: har kechikkan kun uchun -10%.
