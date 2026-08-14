# Topshiriq 1 — SQL so'rovlar

**Fan:** Ma'lumotlar bazasi
**Guruhlar:** AT-24-01, AT-24-02
**O'qituvchi:** Umarov Sherzod
**Maksimal ball:** 10
**Topshirish muddati:** e'lon qilingan kundan boshlab 10 kun ichida (aniq sana
UniAgent tizimidagi topshiriq yozuvida ko'rsatilgan).

## Berilgan sxema

Topshiriq "kutubxona" o'quv ma'lumotlar bazasi ustida bajariladi:

```sql
mualliflar (id, ism, mamlakat)
kitoblar   (id, nomi, muallif_id, chiqqan_yil, janr)
oquvchilar (id, ism, guruh)
ijaralar   (id, kitob_id, oquvchi_id, olingan_sana, qaytarilgan_sana)
```

`ijaralar.qaytarilgan_sana` NULL bo'lsa — kitob hali qaytarilmagan.
Sxemani yaratish va namunaviy ma'lumotlar bilan to'ldirish skripti amaliyot
mashg'ulotida tarqatilgan (`kutubxona_seed.sql`).

## Topshiriqlar

Quyidagi 10 ta so'rovni yozing. Har bir so'rov alohida izoh (`-- 1-topshiriq`)
bilan belgilansin:

1. Barcha kitoblarning nomi va chiqqan yilini alifbo tartibida chiqaring.
2. 2015-yildan keyin chiqqan "dasturlash" janridagi kitoblarni toping.
3. Har bir kitob uchun muallif ismini ham chiqaring (JOIN).
4. Eng ko'p ijaraga olingan 5 ta kitobni ijaralar soni bilan chiqaring.
5. Hech qachon ijaraga olinmagan kitoblarni toping.
6. Qaytarilgan ijaralar bo'yicha o'rtacha ijara muddatini (kunlarda) hisoblang.
7. Har bir janr bo'yicha kitoblar sonini chiqaring (GROUP BY).
8. Eng ko'p kitob ijaraga olgan o'quvchini ichma-ich so'rov (subquery) bilan
   toping.
9. Barcha o'quvchilarni, ijara olmaganlarini ham qo'shib, oxirgi ijara sanasi
   bilan chiqaring (LEFT JOIN).
10. O'zingiz o'ylab topgan, kamida bitta JOIN va bitta agregat funksiya
    qatnashgan mazmunli so'rov yozing va izohda nimani hisoblashini
    tushuntiring.

## Topshirish formati

- Bitta `.sql` fayl: `topshiriq1_FAMILIYA.sql` (masalan,
  `topshiriq1_ALIYEV.sql`).
- Fayl boshida izoh: F.I.Sh., guruh, sana.
- Fayl UniAgent tizimi orqali yuklanadi.

## Baholash mezonlari

| Mezon | Ball |
|---|---|
| 1-7-so'rovlar to'g'ri ishlaydi | 5 |
| 8-9-so'rovlar (subquery, LEFT JOIN) to'g'ri | 3 |
| 10-so'rov mazmunli va izohlangan | 1 |
| Kod uslubi: izohlar, o'qiluvchan formatlash | 1 |

Savollar bo'lsa — amaliyot mashg'ulotida yoki UniAgent chat orqali murojaat
qiling.
