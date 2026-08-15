# PROGRESS — joriy holat

> Har sessiya oxirida yangilanadi. Yangi sessiya SHU FAYLDAN boshlanadi.

## Joriy sessiya: S13 (navbatda)

S12 yakunlandi (DoD 3/3: `pytest` **211/211** — S2 12 + S3 9 + S4 9 + S5 9 +
S6 15 + S7 20 + S8 29 + S9 39 + S10 24 + S11 28 + S12 **17**; `npm run lint`
va `npm run build` toza; jonli tekshiruv uvicorn+curl bilan HAR TRIGGER
bo'yicha: chek yuklandi (karimov → nazarovaga `payment_uploaded`), chek
tasdiqlandi (nazarova → sharipovaga `payment_confirmed`; 6 000 000 →
7 200 000, qoldiq 4 800 000), darsda `absent` (umarov belgiladi → talabaga
`class_absent`, qayta belgilaganda dublikat YO'Q), `flow_due` (rashidova
tursunovga ertangi muddat bilan buyruq yubordi → IKKALASI ham "Ijro muddati
yaqin" oldi, qo'ng'iroqcha qayta ochilganda dublikat yo'q), `flow_status`
(tursunov "ko'rildi" → rashidovaga), qarzdorlik (karimovda seed qatori qayta
ishlatildi — 1 ta; nazarovaga guruh svodi "4 ta talaba qarzdor"),
`POST /notifications/{id}/read` unread 3→2, `read-all` → 0, begona yozuvni
o'qish **404**, chatda `use_tool:bildirishnomalar:{}` → manba
"Bildirishnomalar ro'yxati, 15.08.2026 (2 ta o'qilmagan)".
**Brauzerda** (headless Chrome/CDP, 1440x900): tursunov — qo'ng'iroqchada
**2**, panelda `flow_due` + `flow_incoming` qatorlari, "Ijro muddati" qatorini
bosish → **/docflow** va sanoq 2→1; nazarova — **3** (qarzdorlik svodi +
2 chek), chek qatori → **/group**, 3→2, "Hammasini o'qildi" → **0** (uchala
qator xiralashdi); aliyev — "Davomat" qatori → **/attendance**; konsolda xato
yo'q. **Demo bazasi tekshiruvdan keyin asl holatiga qaytarildi**
(`seed.generate --reset` + `seed.ingest_documents --reset`): 4 flow hujjat,
9 tarix yozuvi, 15 bildirishnoma, 10 hujjat / 28 bo'lak.

S13 (Admin panel + demo reset) uchun izohlar:

- **Admin allaqachon hamma joyga ruxsatli** — yangi RBAC qoidasi yozish shart
  emas: `rbac.require_role(*roles)` ro'yxatdan qat'i nazar adminni o'tkazadi,
  `registry.Tool.is_allowed_for` ham (`role == UserRole.admin`), doira
  helperlari (`visible_group_ids` → `None` = cheklovsiz, `can_access_user` →
  `True`) ham. Ya'ni admin paneli MAVJUD endpointlarni to'g'ridan-to'g'ri
  chaqira oladi; S13 ning ishi — yangi **boshqaruv** endpointlari
  (`app/api/admin.py`; `main.py` da unga joy izoh bilan qoldirilgan) va
  ularga `require_role()` (argumentsiz — faqat admin o'tadi).
- **Statistika uchun tayyor servis funksiyalari** (yangi SQL yozilmasin):
  ```
  payments.group_payment_summary(db, admin)      -> butun universitet bo'yicha
                                                    (admin doirasi = hammasi):
                                                    debtor/partial/paid_count,
                                                    pending_count, summalar
  presence.group_presence(db, admin, now=...)    -> bugun binoda/chiqqan/kelmagan
  presence.teacher_day_overview(db, admin, ...)  -> o'qituvchilar svodi
                                                    (notify=False bering!)
  presence.teacher_month_summary(db, admin, days)-> oylik foizlar
  docflow.inbox/outbox/overview(db, admin)       -> hamma hujjat (admin filtri yo'q)
  notifications.feed(db, user, refresh=False)    -> bildirishnomalar
  services/documents.visible_documents(db, admin)-> hujjatlar ro'yxati
  rag.ingest.ingest_all(db, reset=False)         -> {documents, chunks, missing}
  ```
  Hammasi dataclass qaytaradi (`asdict()` bilan sxemaga o'giriladi) va
  DISCLAIMER/manba maydonlari bor.
- **Demo reset IKKI buyruqni ham chaqirishi shart:** `python -m
  seed.generate --reset` (barcha jadvallarni `ALL_MODELS` bo'yicha tozalaydi
  va qayta yozadi) → `python -m seed.ingest_documents --reset` (Chroma
  kolleksiyasi + `Chunk` jadvali). Ikkinchisisiz qidiruv bo'sh qoladi.
  Endpoint qilishning xavfsiz yo'li:
  - `seed.generate.main()` ni `sys.argv = ["seed.generate", "--reset"]` bilan
    chaqirish mumkin (aynan shu naqsh `tests/conftest.py` da ishlatiladi va
    ishlaydi), indekslash uchun esa CLI shart emas —
    `app.rag.ingest.ingest_all(db, reset=True)` to'g'ridan-to'g'ri chaqiriladi.
  - **Uzoq ishlaydi:** embedding modeli birinchi chaqiruvda yuklanadi
    (~10 s, 450 MB) va 28 bo'lak vektorlanadi — jami ~15-30 s. Demo paytida
    HTTP timeout bo'lmasligi uchun: alohida `POST /admin/reset` (faqat admin),
    frontendda uzun "yuklanmoqda" holati + tugmani bloklash; yoki
    `BackgroundTasks` bilan ishga tushirib, holatni `GET /admin/reset/status`
    dan so'rash. Bir vaqtda ikki reset ketmasin (oddiy modul darajasidagi
    bayroq yetadi).
  - **Reset ochiq turgan sessiyalarni buzadi:** foydalanuvchi id lari qayta
    yaratiladi, ya'ni eski JWT dagi `sub` boshqa odamga tegishli bo'lib
    qolishi mumkin. Demo oldidan reset qilinadi va hamma qaytadan kiradi —
    frontendda resetdan keyin `logout()` chaqirilsin.
- **Foydalanuvchi/rol boshqaruvi uchun endpoint hali YO'Q:** `User` modeli
  (`username`, `password_hash`, `role`, `group_id`, `faculty_id`, `language`)
  va `auth/passwords.hash_password` tayyor; `schemas.UserOut` login javobida
  ishlatiladi. S13 ro'yxat/yaratish/rol o'zgartirishni `app/api/admin.py` ga
  qo'shsin (`services/admin.py` da logika — routerlar yupqa qoidasi).
- **Hujjat yuklash + teglash:** `app/rag/ingest.py` da `SUPPORTED_SUFFIXES`
  faqat `.md`/`.txt`; `Document.file_path` — `backend/` ga nisbatan yo'l.
  Yuklangan faylni `seed/documents/` ga emas, alohida `uploads/documents/`
  ga qo'yish tavsiya etiladi (reset uni o'chirmaydi, lekin `Document` qatori
  o'chadi — S13 buni PROGRESS ga yozsin). Yuklangandan keyin darhol
  `ingest_document(db, document)` yoki `ingest_all(db)` chaqirilsa hujjat
  qidiruvda topiladi (DoD shu).
- **Frontend admin sahifasi uchun kerakli API'lar:** `/admin/users` (GET,
  POST, PATCH rol), `/admin/documents` (GET ro'yxat + POST yuklash,
  `multipart/form-data` — `lib/api.ts` da hozir faqat JSON yordamchilari bor,
  bittasi qo'shiladi), `/admin/stats` (yuqoridagi servislardan yig'ilgan
  raqamlar), `/admin/reset` (POST). Navigatsiyaga "Admin" havolasi
  `(protected)/layout.tsx` dagi `NAV` ga `roles: ["admin"]` bilan
  qo'shiladi. UI matnlari — `src/i18n/uz.json` ga yangi `admin` bo'limi.

**Kesh isboti (mock rejimda vaqt bilan o'lchab bo'lmaydi!):** mock provayder
bir zumda javob beradi, shuning uchun curl vaqtlari sovuq/issiq keshda bir xil
(~0.21 s). Haqiqiy isbot — kechikishi simulyatsiya qilingan klient bilan
(`MockLLMClient` + 40 ms `sleep`): 1-chaqiruv **1.020 s / 25 LLM chaqiruvi**,
2-chaqiruv **0.001 s / 0 chaqiruv**. Keyingi sessiyalarda kesh o'lchansa shu
usul ishlatilsin.

**Mock chatda vositani majburlash:** `use_tool:<nom>:{json}` markeri
xabarning **oxirida** turishi kerak — `_marker_tool_call` markerdan keyingi
butun matnni JSON deb o'qiydi, orqasida so'z qolsa argumentlar bo'sh
`{}` bo'lib qoladi (S10 da shunga duch kelindi). Va marker faqat **rolga
ochiq** vositani chaqira oladi: umarov `use_tool:oqituvchi_davomat:{}` yozsa
mock uni umuman tanlamaydi (ro'yxatda yo'q) va `hujjat_qidir` ga tushadi —
registr blokining o'zi pytest bilan isbotlanadi (`execute_tool` to'g'ridan).

Umumiy (o'zgarmaydigan) izohlar:

- **Hujjatlar API (`app/api/documents.py`) — to'liq ro'yxat:**
  ```
  GET  /documents                -> [{id, title, doc_type, language, access_level, uploaded_at}]
  GET  /documents/{id}           -> yuqoridagilar + text (to'liq matn)
  POST /documents/{id}/summary   -> {document_id, title, summary, parts,
                                     truncated, source, disclaimer}          (S6)
  POST /documents/{id}/translate?target_language=uz
                                 -> {document_id, title, source_language,
                                     target_language, paragraph_count,
                                     paragraphs[{index, original, translated}],
                                     cached, truncated, same_language,
                                     source, disclaimer}                     (S7)
  ```
  Biznes logika `app/services/documents.py` da: `visible_documents`,
  `get_visible_document` (None → **404**), `find_visible_document_by_title`,
  `document_text`. Rol filtri — `rag.search.allowed_access_levels(user)`,
  ya'ni qidiruvda ko'rinmaydigan hujjat ro'yxatda ham, ko'ruvchida ham,
  rezyumeda ham, tarjimada ham ko'rinmaydi (bitta qoida, bitta joy).
- **To'lovlar API (`app/api/payments.py`) — to'liq ro'yxat (S8):**
  ```
  GET  /payments/contract               -> ContractSummaryOut (o'z kontrakti)
  GET  /payments/contract/{student_id}  -> ContractSummaryOut (doira: 403)
  GET  /payments/group[?group_id=]      -> GroupPaymentSummaryOut (tutor/staff/admin)
  GET  /payments/{payment_id}/receipt   -> ReceiptOut (strukturali chek)
  POST /payments/receipts               -> ContractSummaryOut (talaba chek yuklaydi)
  POST /payments/{payment_id}/confirm   -> ContractSummaryOut (tyutor tasdiqlaydi)
  ```
  `ContractSummaryOut`: `student_id, username, student_name, group_id,
  group_name, academic_year, total_amount, paid_amount, pending_amount,
  remaining_amount, paid_percent, state ("paid"|"partial"|"debtor"),
  last_payment_at, payments[{id, amount, paid_at, receipt_number, status,
  has_receipt_file}], source, disclaimer`. Biznes logika
  `app/services/payments.py` da: `contract_summary`, `group_payment_summary`,
  `receipt_view`, `upload_receipt`, `confirm_payment`, `format_amount`,
  `format_contract_for_tool`, `format_group_for_tool`.
- **Davomat/mavjudlik API (`app/api/attendance.py`) — to'liq ro'yxat (S9+S10):**
  ```
  GET  /attendance/presence[?at=]              -> PresenceOut (o'zi)
  GET  /attendance/presence/{user_id}[?at=]    -> PresenceOut (doira: 403)
  GET  /attendance/group[?group_id=&at=]       -> GroupPresenceOut (tutor/staff)
  GET  /attendance/summary[?student_id=&days=] -> AttendanceSummaryOut
  GET  /attendance/my-classes[?on_date=&at=]   -> TeacherDayOut (teacher)
  GET  /attendance/class/{schedule_id}         -> ClassRosterOut (teacher/tutor/staff)
  POST /attendance/class/{schedule_id}/mark    -> ClassRosterOut (faqat o'z darsi)
  GET  /attendance/teachers[?on_date=&at=]     -> TeacherDayOverviewOut (staff)  (S10)
  GET  /attendance/teachers/monthly[?days=&at=]-> TeacherMonthOut (staff)        (S10)
  ```
  `TeacherDayOverviewOut`: `date, at, current_pair, pair_label, faculty_ids,
  rows[TeacherPresenceRowOut], teacher_count, inside_count, left_count,
  absent_count, class_count, held_count, late_count, at_risk_count,
  unclear_count, schedule_note, source, disclaimer`;
  `TeacherPresenceRowOut`: `teacher_id, username, full_name, faculty_id, state
  ("inside"|"left"|"not_arrived"), state_label, in_building, entered_at,
  left_at, classes[TeacherClassStateOut], class_count, held_count, late_count,
  at_risk_count, unclear_count, summary`;
  `TeacherClassStateOut.state`: **hisoblangan** holat —
  `held | late | at_risk | needs_clarification | upcoming | cancelled`
  (DB dagi `session_status` yonida keladi, uni almashtirmaydi).
  `PresenceOut`: `user_id, username, full_name, role, group_id, group_name, at,
  state ("inside"|"left"|"not_arrived"), state_label, in_building, entered_at,
  left_at, last_event_at, current_pair, current_class, next_class,
  attendance_status, attendance_marked, day{total,present,late,absent,percent},
  summary, schedule_note, sources[], disclaimer`. Biznes logika
  `app/services/presence.py` da: `presence`, `student_presence`,
  `group_presence`, `attendance_summary`, `student_attendance_summary`,
  `teacher_classes`, `class_roster`, `mark_attendance`, `current_pair`,
  `pair_bounds`, `building_state` + `format_*_for_tool` yordamchilari.
  S10 shu faylga qo'shdi: `teachers_in_scope`, `class_state` (hisoblangan
  holat), `teacher_day_overview`, `record_risk_notifications`,
  `teacher_month_summary`, `teacher_row_sources`,
  `format_teacher_overview_for_tool`, `format_teacher_row_for_tool`,
  `format_teacher_month_for_tool`.
  **`PAIR_TIMES` shu faylda** (yagona nusxa; `seed/generate.py` va
  `agents/tools/schedule_view.py` shundan import qiladi).
- **Hujjat aylanmasi API (`app/api/docflow.py`) — to'liq ro'yxat (S11):**
  ```
  GET  /docflow/templates            -> [FlowTemplateOut]  (rol bo'yicha filtrlangan)
  GET  /docflow/recipients           -> [FlowRecipientOut]  (buyruq kimga yuborilishi mumkin)
  GET  /docflow/inbox[?sort=new|due] -> FlowListOut (menga kelganlar)
  GET  /docflow/outbox[?sort=]       -> FlowListOut (men yuborganlarim)
  GET  /docflow/{id}                 -> FlowDetailOut (tarix bilan; begona -> 404)
  POST /docflow                      -> FlowDetailOut (shablondan yaratish, 201)
  POST /docflow/{id}/status          -> FlowDetailOut (403/409/422 — pastda)
  POST /docflow/{id}/summary         -> FlowSummaryOut (S6 servisi, body_text bo'yicha)
  ```
  `FlowItemOut` (ro'yxat qatori): `id, doc_type, doc_type_label, template_id,
  title, sender_id, sender_name, sender_role, recipient_role,
  recipient_user_id, recipient_label, status, status_label, created_at,
  updated_at, due_date, due_in_days, overdue, is_incoming, is_outgoing,
  can_change_status, last_comment, preview`; `FlowDetailOut` = shu + `body_text,
  history[FlowHistoryItemOut], next_statuses[], source, disclaimer`;
  `FlowListOut`: `box, sort, rows[], total, new_count, open_count,
  overdue_count, due_soon_count, source, disclaimer`. Biznes logika
  `app/services/docflow.py` da: `TEMPLATES` (5 ta shablon konstantasi),
  `TRANSITIONS`, `inbox`, `outbox`, `flow_detail`, `create_flow`,
  `change_status`, `summarize_flow`, `find_flow`, `overview`,
  `notify_incoming`, `notify_status`, `format_flow_for_tool`,
  `format_flow_list_for_tool`.
- **Bildirishnomalar API (`app/api/notifications.py`) — to'liq ro'yxat (S12):**
  ```
  GET  /notifications[?unread=true&limit=]  -> NotificationListOut
  POST /notifications/{id}/read             -> NotificationListOut (begona -> 404)
  POST /notifications/read-all              -> NotificationListOut
  ```
  `NotificationListOut`: `rows[NotificationOut], total, unread_count,
  unread_only, limit` (qo'ng'iroqchaga bitta so'rov yetadi; ikkala POST ham
  yangilangan ro'yxatni qaytaradi). `NotificationOut` (S0 dan): `id, user_id,
  notif_type, text, link_type, link_id, is_read, created_at` — **`created_at`
  LOKAL vaqtga o'girilgan** (DB da UTC). Biznes logika
  `app/services/notifications.py` da: `write_notification` (YAGONA yozuvchi,
  dublikat himoyasi), `feed`, `unread_count`, `mark_read`, `mark_all_read`,
  `get_own`, triggerlar (`notify_receipt_uploaded`, `notify_payment_confirmed`,
  `notify_absent`, `record_debt_notifications`,
  `record_flow_due_notifications`, `refresh_triggers`),
  `format_feed_for_tool`, `to_local`. Turlar: `flow_status`, `flow_incoming`,
  `flow_due`, `teacher_absence`, `payment_uploaded`, `payment_confirmed`,
  `payment_debt`, `class_absent`, `new_assignment` (`TYPE_LABELS` da
  o'zbekcha yorliqlar, UI esa `i18n/uz.json` dagi `notifications.types` ni
  ishlatadi).
- **Chat API (frontend shu bilan ishlaydi, `lib/api.ts` orqali):**
  ```
  POST /chat                     {message, conversation_id?}
    -> {conversation_id, text, sources[], disclaimer}
  GET  /chat/conversations       -> [{id, user_id, title, created_at}]  (faqat o'ziniki)
  GET  /chat/conversations/{id}  -> yuqoridagi + messages[] + disclaimer
  ```
  `sources[]` elementi (`schemas.ChatSource`): `type` ("document" | "schedule"),
  `label` (tayyor sitata matni — chipga shu yoziladi), `document_id`, `title`,
  `heading`, `order_index`, `chunk_id` (oxirgi 5 tasi ixtiyoriy/None).
  `messages[]` elementi: `role` ("user"/"assistant"/"tool"), `content`,
  `tool_name`, `sources`, `created_at`. Hamma endpoint `Bearer` token talab
  qiladi; begona suhbat → **404**.
- **Disclaimer matni backenddan keladi** (`orchestrator.DISCLAIMER`) —
  frontend uni hardcode qilmasin.
- Mock rejimda javob matni `[mock] '<vosita>' vositasi natijasi asosida: …`
  ko'rinishida bo'ladi (deterministik). UI buni "chiroyli javob" deb emas,
  oqim tirikligi belgisi deb qabul qilsin.
- **Qidiruv imzosi (`hujjat_qidir` tooli shuni chaqiradi):**
  ```python
  from app.rag.search import search, SearchResult
  results: list[SearchResult] = search(query: str, user: User, top_k: int = 5)
  ```
  `SearchResult` — dataclass: `document_id`, `title`, `text`, `order_index`,
  `score`, `heading`, `language`, `doc_type`, `access_level`, `chunk_id`,
  `.as_dict()`. DB sessiyasi KERAK EMAS. Ruxsat filtri qidiruv ICHIDA
  (Chroma metadata filtri), natijadan keyin emas.
- **LLM klient interfeysi:** `app/llm/client.py` —
  `get_llm_client().chat(messages, tools=None, system=None) -> LLMResponse`.
  LLM chaqiruvi FAQAT shu modul orqali.
- **MUHIM (Next 16 + React eslint):** `react-hooks/set-state-in-effect`
  qoidasi `useEffect` ichida **sinxron** `setState` ni XATO deb hisoblaydi
  (`npm run lint` yiqiladi). Yechim: holatni hodisa ishlovchilarida (klik,
  submit) yangilash, effektda esa faqat `.then()/.catch()` ichida; "propdan
  kelgan id o'zgarganda tozalash" o'rniga holatni **derivatsiya** qilish
  (`DocumentPanel` da rezyume `id` bo'yicha, tarjima `id:til` kaliti bo'yicha
  shunday qilingan). Keyingi frontend ishlarida shu naqsh saqlansin.
- **Frontend fayllari:** sahifalar `src/app/(protected)/chat/page.tsx` va
  `.../documents/page.tsx`; komponentlar `src/components/` da: `ChatWindow`,
  `ConversationList`, `SourceChips`, `DocumentPanel`, `DocumentList`,
  `RoleDashboard`, `Markdown` (o'z yozganimiz, kutubxonasiz). Yordamchilar:
  `src/lib/chat.ts`, `src/lib/labels.ts` (enum → o'zbekcha yorliq, sana
  formati, `languageLabel`).
- Testlar uchun `tests/conftest.py`: alohida `backend/test_app.db`
  (`DATABASE_URL` env orqali) va alohida `backend/test_chroma_data/`
  (`CHROMA_PATH` env orqali) — ikkisi ham app importidan OLDIN o'rnatiladi.
  Fixturelar: `seeded_db` (to'liq seed, autouse), `client` (TestClient),
  `db_session` (DB sessiyasi) va `indexed_corpus` (korpusni bir marta
  indekslaydi — embedding modelini yuklaydi, ~10 s). **Eslatma:** `db_session`
  endpoint yozganidan keyin eski snapshotni ushlab qolishi mumkin — qayta
  o'qishdan oldin `db_session.rollback()` chaqiring (S7 testlarida shunday).
- **LLM chaqiruvlarini sanash retsepti (S6/S7 da ishlagan):**
  `monkeypatch.setattr(<servis moduli>, "get_llm_client", lambda: RecordingClient())`
  — namunalar `tests/test_s6_summary.py` va `tests/test_s7_translation.py` da
  (ikkinchisida klient prompt formatiga bo'ysunadigan/bo'ysunmaydigan ikki
  rejimda ishlaydi).
- **Demo/reset ketma-ketligi ikki buyruq:** `python -m seed.generate --reset`
  (Chunk va Translation jadvallarini ham tozalaydi) → `python -m
  seed.ingest_documents --reset` (Chroma kolleksiyasini qayta quradi). S13
  dagi "demo reset" tugmasi IKKALASINI ham chaqirishi kerak.
- **Jonli tekshiruv retsepti:** CORS faqat `http://localhost:3000` ga ochiq va
  `NEXT_PUBLIC_API_URL` build paytida qotadi — backend **8000**, frontend
  **3000** portida. Brauzer sinovi Chrome'ni `--headless=new
  --remote-debugging-port=9222 --user-data-dir=<vaqtinchalik> --window-size=1440,900`
  bilan ishga tushirib, Node 22 ning ichki `WebSocket` i orqali CDP bilan
  qilinadi (npm paketi kerak emas). Viewport 1440x900 qilinmasa `lg:` paneli
  yashirin qoladi. Ro'yxatdan element tanlashda `querySelectorAll("button")`
  ishlating — o'rab turgan `li` ni bosish React `onClick` ni ishga tushirmaydi.

## Sessiyalar holati

| № | Sessiya | Holat | Izoh |
|---|---|---|---|
| S0 | Loyiha skeleti + modellar | ✅ tugadi | DoD 4/4 o'tdi, commit "S0: project skeleton" |
| S1 | Demo ma'lumot generatori | ✅ tugadi | DoD 3/3 o'tdi, commit "S1: demo data generator and document corpus" |
| S2 | Auth + RBAC | ✅ tugadi | DoD 4/4 o'tdi, commit "S2: auth and RBAC" |
| S3 | RAG quvuri | ✅ tugadi | DoD 3/3 o'tdi, commit "S3: RAG pipeline with role-filtered search" |
| S4 | Agent yadrosi + tools | ✅ tugadi | DoD 3/3 o'tdi, commit "S4: agent core with tool calling" |
| S5 | Chat UI | ✅ tugadi | DoD 3/3 o'tdi (pytest 39/39, lint+build toza, 4 rolda brauzer tekshiruvi), commit "S5: chat UI and document panel" |
| S6 | Summarizatsiya | ✅ tugadi | DoD 3/3 o'tdi (pytest 54/54, lint+build toza, curl 3 rolda + brauzerda "Rezyume" tugmasi), commit "S6: role-aware document summarization" |
| S7 | Tarjima moduli | ✅ tugadi | DoD 3/3 o'tdi (pytest 74/74, lint+build toza, curl bilan kesh/ruxsat + brauzerda yonma-yon rejim), commit "S7: document translation with original preserved" |
| S8 | To'lovlar moduli | ✅ tugadi | DoD 3/3 o'tdi (pytest 103/103, lint+build toza, curl bilan raqamlar/doira/tasdiqlash + brauzerda talaba va tyutor sahifalari), commit "S8: payments module with receipt flow" |
| S9 | Davomat + mavjudlik (talaba) | ✅ tugadi | DoD 3/3 o'tdi (pytest 142/142, lint+build toza, curl bilan 4 holat/doira/davomat belgilash + brauzerda o'qituvchi, tyutor va talaba sahifalari), commit "S9: student presence and attendance" |
| S10 | O'qituvchilar davomati | ✅ tugadi | DoD 3/3 o'tdi (pytest 166/166, lint+build toza, curl bilan svod/oylik/doira/403 + bildirishnoma dublikati va brauzerda dekanat ko'rinishi — tursunov qizil), commit "S10: teacher attendance monitoring" |
| S11 | Hujjat almashinuvi | ✅ tugadi | DoD 3/3 o'tdi (pytest 194/194, lint+build toza, curl bilan to'liq zanjir/404/403/409/422 + bildirishnomalar va brauzerda talaba, dekanat, o'qituvchi ko'rinishlari), commit "S11: document flow with status chain" |
| S12 | Bildirishnomalar | ✅ tugadi | DoD 3/3 o'tdi (pytest 211/211, lint+build toza, curl bilan har trigger + dublikat tekshiruvi, brauzerda qo'ng'iroqcha/panel/havola/o'qildi 3 rolda), commit "S12: notifications center" |
| S13 | Admin panel + reset | ⬜ boshlanmagan | |
| S14 | Integratsiya + taqdimot | ⬜ boshlanmagan | |

Holatlar: ⬜ boshlanmagan · 🔄 jarayonda · ✅ tugadi (DoD tekshirilgan)

## Qabul qilingan qarorlar

- **Orkestratsiya:** S3 dan boshlab sessiya-subagentlar **Opus** modelida
  ochiladi (foydalanuvchi ko'rsatmasi, 2026-08-14).
- **LLM provayder: Google Gemini** — API kalit loyiha oxirida ulanadi.
  Ungacha `LLM_PROVIDER=mock` rejimida quriladi va test qilinadi.
  `llm/client.py` Gemini tool calling formatiga mo'ljallanadi.
- **S0 versiyalar (o'rnatilgan, `pip freeze` dan):** Python 3.13.7 (.venv),
  fastapi 0.141.1, uvicorn 0.52.3, sqlalchemy 2.0.52, pydantic 2.13.4,
  pydantic-settings 2.15.0; Node 22.19.0, next 16.3.1, react 19.2.8,
  tailwindcss 4 (create-next-app skeleti).
- **S0 model qarorlari:**
  - Rollar enumi: `student / teacher / tutor / staff / admin`
    (`staff` = dekanat/registrar).
  - `User` ga `username` + `password_hash` qo'shildi (3.1 login/parol talabi;
    S2 shundan foydalanadi).
  - Alohida `Faculty` jadvali YO'Q (4-bo'lim ro'yxatida yo'q) — `faculty_id`
    oddiy int maydon.
  - `Chunk.embedding` o'rniga `embedding_id` (String) — vektorning o'zi S3 da
    Chroma'da saqlanadi, SQLite'da faqat havola.
  - Status enumlari: Payment `automatic/uploaded/confirmed`; ClassSession
    `held/cancelled/needs_clarification`; Flow
    `sent/seen/in_progress/approved/rejected`; Attendance
    `present/absent/late`; Turnstile yo'nalishi `in/out`.
- **LLM interfeysi (S4 shu bilan quriladi):** `llm/client.py` —
  `BaseLLMClient.chat(messages, tools, system) -> LLMResponse(text, tool_calls)`.
  Neytral formatlar: message = `{"role", "content", "tool_name", "tool_result"}`,
  tool = `{"name", "description", "parameters"(JSON Schema)}`. Mock provayder
  deterministik: `use_tool:<nom>:{...}` markeri yoki matnda tool nomi kelsa
  tool call qaytaradi. Gemini — skelet, `chat()` NotImplementedError.
- **Frontend:** `frontend/AGENTS.md` va `frontend/CLAUDE.md` ni `next dev`
  o'zi generatsiya qiladi (Next 16) — o'chirilmaydi, commitda turadi. Next 16
  API'si o'zgargan — frontend ishlashdan oldin `frontend/AGENTS.md` dagi
  yo'riqnomaga qaralsin. API bazaviy URL: `NEXT_PUBLIC_API_URL`
  (`frontend/.env.local`, default `http://localhost:8000`).
- **S1 demo qahramonlar (O'ZGARMAS — keyingi sessiyalar shunga tayanadi):**
  - Fakultetlar: `1` = Axborot texnologiyalari (AT), `2` = Iqtisodiyot (IQ).
    Guruhlar va "uy xonalari": AT-24-01 → 214, AT-24-02 → 215,
    IQ-24-01 → 310, IQ-24-02 → 311.
  - **aliyev** (Aliyev Jasur, talaba, AT-24-01): binoda (bugun 10:02 da
    kirgan, chiqmagan), bugungi barcha darslarida `present`, kontrakt TO'LIQ
    to'langan (qarz yo'q), bitta arizasi (ma'lumotnoma) `approved`.
  - **karimov** (Karimov Diyor, talaba, AT-24-01): QARZDOR (0 so'm to'lagan),
    bugun binoga kelmagan, o'tgan kunlarda davomati past.
  - **sodiqova** (Sodiqova Malika, talaba, AT-24-01): QISMAN to'lagan (50%),
    bugun 08:12 da kirib 13:15 da chiqib ketgan.
  - **mahmudov** (Mahmudov Aziz, talaba, AT-24-01): binoda (08:07 da kirgan),
    lekin bugungi 3-4-juftlik davomatida `absent` — S9 dagi
    "binoda + davomatda belgilanmagan" holati.
  - **tursunov** (Tursunov Akmal, o'qituvchi, fakultet 1): bugun jadvalda
    darslari bor (jumladan 3-juftlik: AT-24-02, "Kompyuter tarmoqlari",
    103-lab), binoga UMUMAN kirmagan — S10 "dars xavf ostida" ssenariysi.
    Uning bugungi ClassSession lari `needs_clarification`; dekanat
    (rashidova, yusupov) uchun `teacher_absence` bildirishnomasi yozilgan.
  - **sharipova** (Sharipova Gulnora, talaba, AT-24-02): kecha chek yuklagan —
    `Payment.status = uploaded`, tyutor tasdig'i kutilmoqda (S8 demo);
    nazarova uchun bildirishnoma bor.
  - Bugungi pin: AT-24-01 3-juftlik = "Ma'lumotlar bazasi", 214-xona, umarov
    (FUNKSIONALLIK 3.7 misoli bilan mos: "10:02 da kirgan, 214-xonada,
    davomatda belgilangan").
  - Demo loginlar: talaba `aliyev`/`karimov`/`sodiqova`; o'qituvchi `umarov`
    (darsda) / `tursunov` (kelmagan); tyutor `nazarova` (AT) / `qodirova`
    (IQ); dekanat `rashidova` (AT) / `yusupov` (IQ); admin `admin`.
- **S2 qarorlar (auth + RBAC):**
  - JWT: **pyjwt** (2.13), HS256, secret `.env` dagi `JWT_SECRET` (≥32 belgi),
    muddat `JWT_EXPIRES_MINUTES` (default 720). Payload: `sub` (user id),
    `role`, `exp`. Logout stateless — klient tokenni o'chiradi.
  - Parol xeshlash: **stdlib PBKDF2** (`hashlib.pbkdf2_hmac`, sha256,
    100 000 iteratsiya) — `app/auth/passwords.py`, tashqi kutubxona yo'q.
    Format: `pbkdf2_sha256$iter$salt$digest`.
  - **Hamma demo foydalanuvchi paroli: `demo123`** (seed bitta xeshni
    hammaga qo'yadi — tezlik uchun).
  - `require_role(*roles)` ro'yxatdagi rollarga + **har doim admin** ga
    ruxsat beradi (admin superuser). Doira helperlari: talaba → o'zi,
    o'qituvchi → o'zi dars beradigan guruhlar (Schedule orqali), tyutor →
    `Group.tutor_id` guruhlari, staff → o'z fakulteti, admin → hammasi.
  - Frontend: token `localStorage` (`uniagent_token`), `lib/api.ts` har
    so'rovga `Authorization: Bearer` qo'shadi, 401 da tokenni o'chirib
    `/login` ga qaytaradi (login so'rovining o'zidan tashqari). Auth
    konteksti `src/lib/auth.tsx` (`AuthProvider`/`useAuth`), himoyalangan
    sahifalar `src/app/(protected)/` route-guruhida (client-side guard +
    header: ism, rol, chiqish). Login: `/login`, 5 ta demo tugma.
  - Backend testlarga `pytest`, `httpx` qo'shildi (`requirements.txt`).
- **S3 qarorlar (RAG quvuri):**
  - **Embedding modeli: `intfloat/multilingual-e5-small`** (lokal
    sentence-transformers, kalitsiz, 384 o'lchov, 512 tokenlik oyna, ~450 MB).
    Tanlov o'lchab qilingan (seed korpusi, 24 ta savol, top-1):
    `paraphrase-multilingual-MiniLM-L12-v2` RAD ETILDI — uning 50 tilli
    distillyatsiya ro'yxatida **o'zbek tili yo'q**; `multilingual-e5-base`
    (1.1 GB) sinovda e5-small dan **yaxshi chiqmadi** (ikkalasi ham 19/24),
    lekin 3 barobar sekin — shuning uchun small.
  - **Model FAQAT `app/rag/embeddings.py` orqali** (CLAUDE.md qoidasi).
    Sozlamalar `config.py` da: `EMBEDDING_MODEL`, `EMBEDDING_QUERY_PREFIX`
    (`"query: "`), `EMBEDDING_PASSAGE_PREFIX` (`"passage: "`) — e5 oilasi shu
    prefikslarni talab qiladi; boshqa model qo'yilsa ularni bo'sh qilish kerak.
  - **Markazlashtirish (mean centering), `EMBEDDING_CENTER=true`** — S3 ning
    eng muhim topilmasi. Ko'p tilli fazo anizotrop: hamma o'xshashlik
    0.79-0.87 oralig'ida siqilgan va qolgan farqni **til** belgilaydi, ma'no
    emas. Natijada "mashinaviy o'qitish nima?" savoli inglizcha ML hujjatini
    **12-o'ringa** tushirgan (oldida — mavzuga aloqasiz o'zbekcha hujjatlar).
    Korpus o'rtacha vektorini ayirish buni yo'qotadi: top-1 12/16 → 15/16.
    O'rtacha vektor to'liq qayta indekslashda hisoblanadi va
    `chroma_data/embedding_bias.json` da saqlanadi; savol ham shu vektor bilan
    markazlashtiriladi. Fayl bo'lmasa — oddiy (markazlashtirilmagan) rejim.
  - **Gibrid reyting:** vektor qidiruvi nomzodlar hovuzini beradi
    (`top_k*4`, kamida 20), keyin ular IDF-vaznli kalit so'z mosligi bilan
    qayta tartiblanadi: `0.7*kosinus + 0.3*leksik`
    (`SEARCH_LEXICAL_WEIGHT`). Kosinus **min-max normallashtirilmaydi** —
    aks holda eng yaxshi nomzod zaif bo'lsa ham 1.0 ga cho'ziladi va mavzuga
    aloqasiz hujjat yutib ketadi. O'lchov (talaba ko'rinishi, 23 savol,
    top-1): 15/23 oddiy → 18/23 markazlashtirilgan → **20/23 gibrid**.
  - **Bo'laklash:** paragraf chegaralarini buzmaydi, markdown sarlavhalarini
    kuzatadi; maqsad ~1600 belgi, qattiq chegara 2200 (`CHUNK_TARGET_CHARS`,
    `CHUNK_MAX_CHARS`) — bu ~260 median token, model oynasi 512 dan past,
    ya'ni **hech narsa kesilmaydi**. Embeddingga beriladigan matn oldiga
    hujjat nomi + bo'lim sarlavhasi qo'shiladi (qisqa bo'lak — masalan
    juftliklar jadvali — kontekstsiz ma'nosiz). Bo'lak bir nechta bo'limni
    qamrasa, `heading` ularning HAMMASINI " · " bilan ko'rsatadi (manba
    ko'rsatish qoidasi buzilmasin). Seed korpusi: 10 hujjat → 28 bo'lak.
  - **Chroma:** `chromadb` 1.5.9, `PersistentClient`,
    kolleksiya `uniagent_documents`, `metadata={"hnsw:space": "cosine"}`,
    `embedding_function=None` (vektorni doim o'zimiz beramiz). Papka
    `backend/chroma_data/` (`CHROMA_PATH`, gitignore da). Metadata:
    `document_id`, `chunk_id`, `title`, `doc_type`, `language`,
    `access_level`, `order_index`, `heading`. Chroma id formati
    `doc{document_id}_c{order_index}` — u `Chunk.embedding_id` ga yoziladi.
  - **Fayllar:** `app/rag/embeddings.py` (yagona embedding nuqtasi),
    `store.py` (yagona chromadb nuqtasi), `ingest.py` (matn → bo'lak →
    vektor → Chroma + `Chunk`), `search.py` (rol filtri + gibrid reyting),
    `seed/ingest_documents.py` (CLI). `seed/generate.py` O'ZGARMADI.
  - **Kutubxonalar:** torch **CPU g'ildiragi** (`--index-url
    https://download.pytorch.org/whl/cpu`, 122 MB; PyPI dagi oddiy g'ildirak
    CUDA bilan ~10 barobar katta), `sentence-transformers` 5.7,
    `chromadb` 1.5.9 — `requirements.txt` da izoh bilan.
- **S4 qarorlar (agent yadrosi + tool calling):**
  - **Tool registri (`app/agents/registry.py`):** `Tool(name, description,
    parameters(JSON Schema), handler, roles)` + `ToolResult(text, sources, ok)`.
    `execute_tool(name, args, db, user)` — **ruxsat shu yerda tekshiriladi**:
    rol mos kelmasa handler CHAQIRILMAYDI, `ToolResult(ok=False, "Ruxsat
    yo'q…")` qaytadi (exception EMAS — agent oqimi davom etadi va model rad
    javobini tushuntiradi). Noma'lum vosita va handler ichidagi xatolik ham
    shu tarzda `ok=False` natijaga aylanadi. `roles` ro'yxatiga qo'shimcha
    ravishda **admin har doim ruxsatli** (rbac dagi `require_role` bilan bir xil
    qoida). `tools_for_role(role)` — LLM ga beriladigan deklaratsiyalar.
    Yangi tool qo'shish: `agents/tools/` ga fayl + o'sha faylda `register(...)`;
    `agents/tools/__init__.py` ga bitta import qatori. Boshqa hech narsa.
  - **S4 dagi 3 vosita — uchalasi ham hamma rolga ochiq**, chunki cheklov
    ma'lumot qatlamida: `hujjat_qidir` (rol filtri `rag.search` ichida),
    `jadval_kor` (`rbac.visible_group_ids` doirasi; o'qituvchi — faqat
    `Schedule.teacher_id == user.id`; doiradan tashqari guruh so'ralsa
    "Ruxsat yo'q" natijasi), `hujjat_rezyume` (`access_level` tekshiruvi
    `rag.search.allowed_access_levels` bilan; **nom bo'yicha qidiruvda**
    ko'rinmaydigan hujjat umuman topilmaydi — mavjudligi ham oshkor bo'lmaydi,
    id bo'yicha so'ralsa ochiq "ruxsat yo'q"). Rol-cheklangan vositalar
    S8-S11 da qo'shiladi (`tolov_holati`, `mavjudlik_tekshir`, …).
  - **Tizim promptlari (`app/agents/prompts/`):** `umumiy.md` (6 ta buzilmas
    qoida: faqat tool natijasiga tayanish, manba ko'rsatish, ruxsat chegarasi,
    "rasmiy hujjat emas", "mavjudlik = xulosa", qisqalik) + rol fayli
    (`student.md`, `teacher.md`, `tutor.md`, `staff.md`, `admin.md`).
    `orchestrator.load_system_prompt(role)` ikkalasini birlashtiradi
    (`lru_cache`) — ya'ni majburiy qoidalar bitta joyda, rol fayli faqat ohang
    va rakursni belgilaydi.
  - **Orkestrator (`app/agents/orchestrator.py`):** tarix (oxirgi 20 ta
    user/assistant xabari) → rol prompti → `llm.chat(messages, tools, system)`
    → tool_calls bo'lsa `execute_tool` → natija xabarlar ro'yxatiga qo'shiladi
    va model qayta chaqiriladi → birinchi matnli javobda to'xtaydi,
    **max 5 iteratsiya** (tugasa oxirgi tool natijasidan fallback javob).
    Manbalar iteratsiyalar bo'ylab yig'iladi va dublikatlari olib tashlanadi.
  - **Yangi modellar (ataylab qilingan kengaytma, ISH_REJA S4 "suhbat DB da
    saqlanadi" talabi):** `Conversation` (id, user_id, title, created_at) va
    `ChatMessage` (id, conversation_id, role: user/assistant/**tool**, content,
    tool_name, sources JSON, created_at). Tool xabarlari **audit izi** sifatida
    saqlanadi (qaysi vosita, nima qaytardi), lekin modelga tarix sifatida
    QAYTA berilmaydi — faqat user/assistant almashinuvi beriladi (kontekst toza
    va deterministik qolsin). `seed/generate.py` dagi `ALL_MODELS` ro'yxatiga
    ikkala jadval qo'shildi, aks holda demo reset eski suhbatlarni qoldirardi.
  - **Chat API (`app/api/chat.py`):** router yupqa — butun oqim orkestratorda.
    Begona suhbat uchun **404** (403 emas): boshqa foydalanuvchi suhbatining
    mavjudligini ham bilib bo'lmasin.
  - **Mock provayder kengaytmasi (`llm/client.py`, deterministik qoldi):**
    tool tanlash tartibi — (1) `use_tool:<nom>:{...}` markeri, (2) xabarda
    tool nomi uchrasa o'sha, (3) aks holda `hujjat_qidir(query=<xabar>)`.
    **Transkriptda tool natijasi paydo bo'lgach mock BOSHQA tool chaqirmaydi**
    — shuning uchun sikl har doim tugaydi (bitta tool aylanmasi). Yakuniy matn
    FAQAT tool natijasidan yasaladi (foydalanuvchi savolini qaytarib aytmaydi —
    "javob" ichida o'ylab topilgan fakt bo'lmasligi kafolatlanadi).
    Shu bilan Gemini kalitisiz ham butun oqim (qidiruv → manba → javob) jonli
    ishlaydi; aniq vosita kerak bo'lsa marker ishlatiladi:
    `use_tool:hujjat_rezyume:{"nom": "91-M"}`.
- **S5 qarorlar (chat UI + hujjat paneli):**
  - **Hujjatlar API rol filtrini QAYTA yozmaydi** — `app/services/documents.py`
    `rag.search.allowed_access_levels(user)` ni chaqiradi. Ya'ni qidiruvda
    ko'rinmaydigan hujjat ro'yxatda ham, ko'ruvchida ham ko'rinmaydi (bitta
    qoida, bitta joy). Ko'rish huquqi yo'q hujjat → **404**, 403 emas
    (chat API dagi begona suhbat qoidasi bilan bir xil).
  - **`services/documents.py` qo'shildi** (CLAUDE.md dagi ro'yxatda yo'q edi):
    routerlar yupqa bo'lsin degan arxitektura qoidasiga amal qilingan; S6
    rezyume tugmasi ham shu servisdan foydalanadi.
  - **`ConversationDetailOut` ga `disclaimer` maydoni qo'shildi** (default —
    `orchestrator.DISCLAIMER`, `api/chat.py` O'ZGARMADI). Sabab: domen
    qoidasi 3 ga ko'ra tarixdan qayta yuklangan javob ostida ham ogohlantirish
    turishi kerak, frontend esa matnni hardcode qilmasligi kerak.
  - **Marshrutlar:** `/` → `/chat` ga yo'naltiradi (kirgandan keyin darhol
    chat); `(protected)/chat` — chat ish maydoni, `(protected)/documents` —
    hujjatlar sahifasi. `(protected)/layout.tsx` ga navigatsiya qo'shildi va
    balandlik `h-screen overflow-hidden` ga o'tkazildi (har sahifa o'z
    ustunini o'zi skroll qiladi).
  - **Layout rolga qarab:** chat markazda (hamma rol), o'ngdagi panel —
    ochilgan hujjat, hujjat ochilmagan bo'lsa `RoleDashboard` (bo'sh
    placeholder) faqat teacher/tutor/staff/admin uchun. Panel `lg:` dan
    kichik ekranda yashiriladi.
  - **Markdown renderer o'zimizniki** (`components/Markdown.tsx`, ~200 qator,
    sarlavha/jadval/ro'yxat/kod/bold): korpus kichik, tashqi markdown
    kutubxonasi bundle'dagi eng og'ir narsa bo'lib qolardi.
  - **Vosita badge'i** (`hujjat_qidir` va h.k.) `role="tool"` xabarlaridan
    olinadi: `POST /chat` javobida vosita nomi yo'q, shuning uchun javob
    kelgandan keyin `GET /chat/conversations/{id}` fonda qayta o'qiladi
    (muvaffaqiyatsiz bo'lsa javob baribir ekranda qoladi).
  - **UI matnlari faqat `src/i18n/uz.json` da** (`nav`, `chat`, `documents`,
    `dashboard`, `common` bo'limlari qo'shildi); enum yorliqlari
    `src/lib/labels.ts` orqali.
  - **Jonli tekshiruv retsepti (keyingi sessiyalar uchun):** CORS faqat
    `http://localhost:3000` ga ochiq va `NEXT_PUBLIC_API_URL` build paytida
    qotadi — shuning uchun brauzer tekshiruvi backend **8000**, frontend
    **3000** portida o'tkaziladi. Brauzer sinovi Chrome'ni
    `--headless=new --remote-debugging-port=9222` bilan ishga tushirib, Node
    22 ning ichki `WebSocket` i orqali CDP bilan qilindi (npm paketi
    o'rnatilmadi); viewport 1440x900 qilinmasa `lg:` paneli yashirin qoladi.
- **S6 qarorlar (summarizatsiya):**
  - **Yagona kod yo'li: `app/services/summarization.py`.** `hujjat_rezyume`
    tooli ham, `POST /documents/{id}/summary` ham AYNAN shu servisni
    chaqiradi (`summarize_document(db, document, user)`), dublikat yo'q.
    Tool endi faqat "qaysi hujjat" savolini hal qiladi va natijani
    `ToolResult` ga o'raydi; matn o'qish `services/documents.document_text`,
    nom bo'yicha qidiruv esa yangi `find_visible_document_by_title` orqali —
    ya'ni ruxsat qoidasi (`rag.search.allowed_access_levels`) hamon bitta
    joyda. Tooldagi eski nusxalar (`_visible_documents`, `_document_text`)
    olib tashlandi.
  - **Rol rakursi ikki qatlamda:** `ROLE_FOCUS` (qisqa ibora, S4 dan meros)
    + yangi `ROLE_POINTS` (har rol uchun 3 ta aniq savol: talaba — "mendan
    nima talab qilinadi / qachongacha / oqibati", dekanat — "raqam va sana /
    ijrochilar / muddatlar", o'qituvchi — "asosiy bandlar / o'quv jarayoniga
    ta'siri / undan talab qilinadigan ish" va h.k.). Ikkalasi HAM tizim
    promptiga (`system_prompt(role)`), HAM foydalanuvchi promptiga
    (`build_summary_prompt`/`build_part_prompt`/`build_reduce_prompt`) kiradi
    — provayder tizim promptini qanchalik hisobga olishidan qat'i nazar
    rakurs yo'qolmaydi. 5 rolning 5 ta har xil rakursi bor (test bilan
    qotirilgan).
  - **Map-reduce, `PART_CHARS = 4000` (`MAX_PARTS = 12`):** matn shu
    chegaradan uzun bo'lsa paragraf chegaralari bo'yicha bo'linadi
    (`split_parts`), har bo'lakka bitta "oraliq qayd" chaqiruvi (map), so'ng
    bitta birlashtiruvchi chaqiruv (reduce) — jami `parts + 1` chaqiruv;
    qisqa hujjatda bitta chaqiruv. 4000 model chegarasi emas, sifat/tezlik
    byudjeti: 6000 da demo korpusining BIRORTA hujjati map-reduce'ga
    tushmasdi (eng uzuni 4858 belgi — ruscha fayl 6793 BAYT, lekin kirill
    2 baytdan, ya'ni ~3.8k belgi). 4000 da syllabus/nizom/ML hujjatlari
    2 bo'lakka bo'linadi, 2 sahifalik buyruq esa bitta chaqiruvda qoladi —
    ikkala yo'l ham demoda jonli ko'rinadi. `MAX_PARTS` dan oshsa
    `truncated=True` va javobda ogohlantirish qatori chiqadi.
  - **Endpoint `POST /documents/{id}/summary`** (GET emas: LLM chaqiruvi —
    qimmat, keshlanmaydigan amal). Javob `schemas.DocumentSummaryOut`:
    `document_id, title, summary, parts, truncated, source (ChatSource),
    disclaimer`. Manba va disclaimer MAJBURIY maydon — rezyume ham faktik
    javob (domen qoidalari 3 va 5). Ruxsati yo'q hujjat → **404** (viewer
    bilan bir xil), matni bo'sh hujjat → 422.
  - **Mock provayder kengaytmasi (`llm/client.py`, ataylab minimal):**
    `tools` berilmagan chaqiruvda (rezyume shunday chaqiradi) javob endi
    `[mock:<digest>] Echo: <promptning ilk 600 belgisi> […]` — oldin butun
    prompt qaytarardi, ya'ni "rezyume" hujjatning o'zidan uzun bo'lardi.
    Digest hamon TO'LIQ matndan olinadi, shuning uchun deterministiklik va
    kirishga bog'liqlik saqlanadi; tool natijasidan javob yasash yo'li
    o'zgarmadi (endi u ham shu `_clip()` yordamchisini ishlatadi). Yoqimli
    yon ta'sir: mock rejimda ham rezyume matnining boshida rol rakursi
    ko'rinadi — 3 rolda farqni ko'z bilan tekshirish mumkin.
  - **Frontend:** "Rezyume" tugmasi `DocumentPanel` header'idagi amal
    tugmalari qatorida; natija hujjat matni TEPASIDA alohida `<section>`
    blokida (manba + disclaimer + "Yopish"), original matn hech qachon
    almashtirilmaydi. Holat S5 naqshi bilan — id bo'yicha derivatsiya
    (`summary.id === documentId`), `setState` faqat hodisa ishlovchisida va
    `.then()/.catch()` ichida (Next 16 `react-hooks/set-state-in-effect`).
- **S7 qarorlar (tarjima):**
  - **Yagona kod yo'li: `app/services/translation.py`.** `tarjima_qil` tooli
    ham, `POST /documents/{id}/translate` ham AYNAN shu servisni chaqiradi
    (`translate_document(db, document, user, target_language)`). Tool faqat
    "qaysi hujjat" savolini hal qiladi (S6 dagi `find_visible_document_by_title`
    / `get_visible_document` bilan) va natijani `ToolResult` ga o'raydi.
  - **Paragraf sonining tengligi — kafolat, ishonch emas.** Javob paragraf
    juftliklari ro'yxati (`{index, original, translated}`), va tarjima paragraf
    soni HAR DOIM original bilan teng. Buni model formatga rioya qilishiga
    tashlab qo'yilmadi: paragraflar `[[n]]` markerlari bilan **to'plam bo'lib**
    (`BATCH_CHARS = 3000`) yuboriladi, javob qat'iy tekshiriladi
    (`parse_batch_response`), marker soni/tartibi mos kelmasa yoki bo'sh bo'lsa
    — o'sha to'plam **paragrafma-paragraf** qayta tarjima qilinadi. Ya'ni
    yomon model tezlikni yo'qotadi, tekislikni emas. Gemini formatga rioya
    qilsa bitta hujjat ~2 chaqiruv, mock (formatni bilmaydi) 25 chaqiruv.
  - **Nega to'plam + zaxira yo'l, sof "har paragrafga bitta chaqiruv" emas:**
    korpusdagi eng uzun hujjatda 38 paragraf bor — jonli demoda Gemini bilan
    38 ketma-ket chaqiruv ~1 daqiqa bo'lardi. To'plam buni ~2 chaqiruvga
    tushiradi, zaxira yo'l esa domen qoidasini saqlaydi.
  - **Kesh `Translation` jadvalida, kalit `(document_id, language)`**
    (`chunk_id` bo'sh — u bo'lak tarjimasi uchun zaxirada qoladi).
    `translated_text` — paragraflar bo'sh qator bilan birlashtirilgan matn;
    shuning uchun har paragraf `normalize_paragraph` bilan ichki bo'sh
    qatorlaridan tozalanadi (aks holda kesh ko'proq paragrafga bo'linib
    ketardi). O'qishda paragraf soni original bilan solishtiriladi —
    mos kelmasa kesh **eskirgan** deb hisoblanadi va qayta quriladi.
    Ikkinchi so'rov: **0 LLM chaqiruvi**, `cached=true`.
  - **Atama qoidasi promptda (`TERM_RULE`)** — "mashinaviy o'qitish (machine
    learning)" naqshi HAM tizim promptida, HAM to'plam promptida, HAM bitta
    paragraf promptida takrorlanadi (provayder tizim promptini qanchalik
    hisobga olishidan qat'i nazar yo'qolmaydi). Test bilan qotirilgan.
  - **`same_language` qisqa tutashuvi:** hujjat tili maqsad tiliga teng bo'lsa
    LLM umuman chaqirilmaydi va keshga hech narsa yozilmaydi — ikkala ustunda
    original turadi, UI "tarjima kerak emas" deb yozadi. Demo korpusining
    8 ta hujjati o'zbekcha, shuning uchun bu holat tez-tez uchraydi.
  - **Maqsad tili tanlanadi:** `uz` / `ru` / `en` (`SUPPORTED_LANGUAGES`),
    default `uz`. Endpoint `?target_language=` so'rov parametri bilan
    (body emas — curl bilan tekshirish oson), noma'lum til → **400**.
    Tool `til` argumentini oladi, berilmasa `user.language` dan foydalanadi.
    Bu tufayli o'zbekcha hujjatni ham inglizchaga o'girib demo qilish mumkin.
  - **Ruxsat hujjat qatlamida:** vosita hamma rolga ochiq (`ALL_ROLES`),
    chunki cheklov `services/documents` da — talaba 91-M ni tarjima qila
    olmaydi (**404**, nom bo'yicha esa "topilmadi": mavjudligi oshkor
    bo'lmaydi), dekanat oladi.
  - **`agents/prompts/umumiy.md` ga 7-qoida qo'shildi** (tillar aro javob):
    javob foydalanuvchi tilida, sitata va atama manba tilida qavsda, to'liq
    matn kerak bo'lsa `tarjima_qil`. Rol fayllari o'zgarmadi.
  - **Frontend:** "Tarjima" tugmasi + til tanlagichi `DocumentPanel`
    header'ida; natija — bitta skroll konteynerida paragraf juftliklari
    qatorlari (`sm:grid-cols-2`), chapda original, o'ngda tarjima.
    **Alohida ikki skroll panel qilinmadi** — bitta konteynerda juftliklar
    qatori sinxronlikni o'z-o'zidan beradi va skroll sinxronlash kodi
    (hamda uning bugi) umuman kerak emas. Ustun sarlavhalari `sticky`.
    Holat `id:til` kaliti bo'yicha derivatsiya qilinadi (Next 16 eslint
    qoidasi), til o'zgarsa ko'rinish o'z-o'zidan oddiy rejimga qaytadi.
- **S8 qarorlar (to'lovlar):**
  - **`uploaded` — pul emas, va'da.** Yagona muhim arifmetika:
    `paid_amount` faqat `automatic` + `confirmed` ni qo'shadi, talaba yuklagan
    (`uploaded`) chek esa alohida `pending_amount` da turadi va
    `remaining_amount = total - paid` ni KAMAYTIRMAYDI. Tyutor tasdiqlagach
    pul "paid" ga o'tadi (sharipova: 6 000 000 → 7 200 000, qoldiq
    6 000 000 → 4 800 000). Aks holda "chekni yukladim" bilan "to'ladim"
    farqi yo'qoladi — bu esa aynan modul yopmoqchi bo'lgan muammo.
  - **Chek = strukturali ma'lumot, fayl emas** (`GET /payments/{id}/receipt`
    → `ReceiptOut`: talaba, chek raqami, summa, sana, holat, to'lov usuli,
    o'quv yili + `file_available:false` va izoh matni). Placeholder
    rasm/SVG generatsiya qilinmadi: (a) `<img>` tegi `Authorization`
    sarlavhasini yubormaydi, ya'ni rasm uchun alohida token mexanizmi kerak
    bo'lardi, (b) soxta "chek rasmi" demo tomoshabinini chalg'itadi.
    Frontend shu ma'lumotni chek ko'rinishidagi modalda chizadi. **Fayl
    yo'qligi hech qachon 404 bermaydi** — demo yiqilmaydi.
  - **Ruxsat: 403, 404 emas.** Hujjat/suhbatda "ko'rinmasa yo'q" qoidasi
    ishlaydi (404), lekin shaxsiy ma'lumotda `ensure_can_access_user` ning
    **403** i ishlatildi: guruhdoshning mavjudligi sir emas, kontrakti sir.
    Bu S7 izohidagi ochiq savolning javobi.
  - **O'qituvchi to'lovlarni umuman ko'rmaydi:** `GET /payments/group` →
    `require_role(tutor, staff)` (admin avtomatik), `tolov_holati` tooli
    `roles=(student, tutor, staff)`. Asos — FUNKSIONALLIK 3.6 "maxfiylik:
    talaba faqat o'zini, tyutor faqat o'z guruhini". Bu loyihadagi birinchi
    rol-cheklangan vosita: registr handlerni chaqirmasdan rad etadi.
  - **`tolov_holati` argumentsiz ham foydali:** tyutor/dekanat uchun
    argumentsiz chaqiruv butun doiraning svodini beradi ("guruhimda kimlar
    qarzdor?"), talaba uchun esa o'z kontraktini. Talaba boshqa ism bersa —
    rad javobi (`ok=False`), lekin o'z ismini/loginini bersa ishlaydi.
  - **Ortiqcha to'lov rad etiladi (422):** yuklangan chek summasi qoldiqdan
    katta bo'lsa qabul qilinmaydi (aliyev — 0 qoldiq — hech narsa yuklolmaydi).
    Manfiy/nol summa ham 422. Ikki marta tasdiqlash — **409**.
  - **Saralash serverda ham, klientda ham:** servis qatorlarni qoldiq
    bo'yicha kamayish tartibida qaytaradi (tyutorga eng kerakli tartib),
    frontend esa `sortRows` bilan ism/guruh bo'yicha qayta saralaydi —
    qo'shimcha so'rov yubormasdan.
  - **`RoleDashboard` placeholderi to'ldirildi** (tutor/staff/admin uchun
    to'lov vidjeti: holatlar soni, eng katta 4 qarzdor, kutayotgan cheklar,
    `/group` ga havola). Teacher uchun placeholder qolgan edi — **S9 uni
    "Bugungi darslar" vidjeti bilan to'ldirdi**.
    Navigatsiya rolga qarab filtrlanadi: talaba "Kontrakt", tyutor/dekanat/
    admin "Guruh".
  - **`errorDetail(error)` yordamchisi `lib/api.ts` ga qo'shildi** — FastAPI
    ning `{"detail": "..."}` matnini UI da ko'rsatish uchun (masalan "summa
    kontrakt qoldig'idan ko'p: qoldiq 0 so'm"), har komponent `ApiError` ni
    o'zi ochib o'tirmasin.
- **S9 qarorlar (davomat + mavjudlik):**
  - **Yagona funksiya, uch manba:** `presence(db, user, now=None)` turniket
    (fakt) → jadval (xulosa) → davomat (jurnal) tartibida ishlaydi va
    `Presence` strukturasini qaytaradi. **Talaba ham, o'qituvchi ham shu
    funksiyadan o'tadi** (rol farqi bitta joyda: joriy darsni topishda talaba
    guruh bo'yicha, o'qituvchi `Schedule.teacher_id` bo'yicha) — S10 uchun
    yangi mexanizm kerak emas. `now` in'ektsiya qilinadi: seed kunning hamma
    juftligini oldindan yozgani uchun test va demo istalgan payt holatini
    ko'rsata oladi.
  - **Turniket loglari `timestamp <= now` bilan filtrlanadi** — aks holda
    sodiqova soat 11:40 da ham "chiqib ketgan" bo'lib ko'rinardi (u 13:15 da
    chiqadi). Shu tufayli 3-juftlikda u "binoda", 5-juftlikda "chiqib ketgan".
  - **Kunlik davomat foizi faqat BOSHLANGAN juftliklarni sanaydi**
    (`pair_start <= now`). Seed kunning hamma juftligini oldindan yozadi —
    ularni ham qo'shsa "kelajakdagi dars" foizga ta'sir qilardi.
    `late` kelgan deb hisoblanadi (`ATTENDED_STATUSES`).
  - **Domen qoidasi 6 backendda qotirilgan:** `SCHEDULE_HINT =
    "jadval bo'yicha"` va `ROOM_NOTE` — servisda; har javobda `schedule_note`
    maydoni bor, UI matnni hardcode qilmaydi. Manba turlari: `turnstile`
    (fakt + vaqt), `schedule` (xulosa), `attendance` (jurnal).
    "Binoda, lekin darsda belgilanmagan" holati alohida ibora bilan
    yoziladi (`_attendance_phrase`) — mahmudov keysi ko'zga tashlanadi.
  - **Davomat belgilash — faqat o'sha darsning o'qituvchisi.** Router
    `require_role(teacher)` (admin avtomatik), servis esa
    `can_mark_class(actor, schedule)` bilan `Schedule.teacher_id == actor.id`
    ni tekshiradi → **403**. Ro'yxatni o'qish kengroq: o'qituvchi faqat o'z
    darsini, tyutor/dekanat `visible_group_ids` doirasidagi darsni
    (`can_view_class`). Talaba ro'yxatni umuman ko'rmaydi (guruhdoshlarining
    davomati — shaxsiy ma'lumot).
  - **Belgilash mavjud yozuvni YANGILAYDI, dublikat yaratmaydi** — seed
    bugungi davomatni oldindan yozgani uchun bu majburiy. Bir amalda
    `Attendance` qatorlari + `ClassSession` (`held`, `teacher_arrived_at`
    turniketdan) yoziladi va javobda yangilangan ro'yxat qaytadi (frontend
    qayta so'rov yubormaydi — S8 dagi `confirm` naqshi).
  - **"Bir klik" = turniket taklifi + saqlash:** har talaba uchun
    `suggested` maydoni turniket logidan hisoblanadi (seed bilan bir xil
    qoida: juftlik boshida binoda → `present`, +5 daqiqadan keyin kirgan →
    `late`, aks holda `absent`), UI dagi "Turniket bo'yicha to'ldirish"
    tugmasi butun ro'yxatni shu bilan to'ldiradi, o'qituvchi kerakli joyini
    qo'lda o'zgartiradi va bitta "Saqlash" bilan yozadi.
  - **`?at=` / `?on_date=` — demo/what-if parametrlari** (faqat o'qish).
    Seed kunning hammasini yozgani uchun soat 23:00 da ham "11:40 holati" ni
    ko'rsatish mumkin; `mavjudlik_tekshir` toolida shu maqsadda `vaqt`
    argumenti bor. Frontend ularni yubormaydi.
  - **Ikkala tool ham `ALL_ROLES`** (`tolov_holati` dan farqli o'laroq):
    mavjudlik — "kuzatuv" emas, davomat vositasi, va cheklov ma'lumot
    qatlamida (`can_access_user`): talaba faqat o'zini, o'qituvchi/tyutor
    o'z guruhlarini, dekanat o'z fakultetini ko'radi.
  - **`/attendance` sahifasi rolga qarab uch ko'rinish** beradi (teacher —
    belgilash, tutor/staff — guruh mavjudligi, student — o'z holati va svodi).
    Alohida uch marshrut yasalmadi: ma'lumot bir xil, savol boshqacha;
    navigatsiyada bitta "Davomat" havolasi hamma rolga ochiq. `/group`
    (to'lovlar) sahifasidan unga havola qo'yildi.
  - **Sxema maydoni `on_date`, `date` emas** (`AttendanceMarkRequest`):
    pydantic klass tanasida `date: date | None = None` yozilsa `date` nomi
    tipni soya qiladi va `TypeError` beradi.
- **S10 qarorlar (o'qituvchilar davomati):**
  - **Holat hisoblanadi, saqlanmaydi.** `ClassSessionStatus` (DB enumi) —
    `held/cancelled/needs_clarification` — O'ZGARTIRILMADI; dekanat ko'radigan
    "xavf ostida" va "kechikkan" esa `class_state(session, building_state,
    starts_at, ends_at, marked_count, now)` funksiyasining **xulosasi**:
    ```
    session.cancelled                         -> cancelled
    davomat belgilangan yoki session.held      -> held  (kirish qo'ng'iroqdan
                                                 keyin bo'lsa -> late)
    now < start - 10 daq                       -> upcoming
    binoda emas, now <= end                    -> at_risk
    binoda emas, now > end                     -> needs_clarification
    binoda, davomat yo'q                       -> needs_clarification
    ```
    Shu sabab tursunovning AYNAN o'sha satri 11:40 da "xavf ostida",
    13:00 da "aniqlashtirish kerak" bo'lib ko'rinadi (ikkalasi ham test bilan
    qotirilgan). `RISK_LEAD_MINUTES = 10` (qo'ng'iroqdan 10 daqiqa oldin
    ogohlantirish boshlanadi), `LATE_GRACE_MINUTES = 5` (talaba `suggested`
    qoidasi bilan bir xil).
  - **Doira — `visible_group_ids` EMAS, `can_access_user`.** O'qituvchi
    guruhga tegishli emas, fakultetga tegishli; shuning uchun
    `teachers_in_scope(db, actor)` barcha o'qituvchilarni olib
    `rbac.can_access_user(db, actor, teacher)` bilan filtrlaydi (staff → o'z
    fakulteti, admin → hammasi). Yangi RBAC qoidasi yozilmadi.
  - **Endpoint faqat dekanatga:** `require_role(UserRole.staff)` (admin
    avtomatik) — o'qituvchi ham, **tyutor** ham 403 oladi (FUNKSIONALLIK 3.8
    "maxfiylik: o'qituvchi davomatini faqat dekanat/admin ko'radi").
    O'qituvchi o'z kunini S9 dagi `/attendance/my-classes` orqali ko'radi.
  - **`oqituvchi_davomat` — loyihadagi ikkinchi rol-cheklangan vosita**
    (`roles=(UserRole.staff,)`, `tolov_holati` naqshi): registr handlerni
    umuman chaqirmaydi. Test buni `presence_service.teacher_day_overview` ni
    "chaqirilsa yiqiladigan" spy bilan almashtirib isbotlaydi.
    Argumentlar: `oqituvchi` (bo'sh bo'lsa — butun fakultet svodi),
    `davr` ("oy" → oylik foizlar), `vaqt` (demo soati; `parse_moment`
    `presence_check.py` dan import qilinadi — ikkinchi nusxa yasalmadi).
  - **Bildirishnoma svod so'ralganda yoziladi** (`teacher_day_overview(...,
    notify=True)` → `record_risk_notifications`): har "xavf ostida" dars
    uchun o'sha o'qituvchi **fakultetidagi** har bir `staff` ga bitta yozuv,
    kalit `(user_id, link_id=schedule_id, notif_type="teacher_absence")` +
    o'sha kun. Seed yozgan qatorlar shu kalit bo'yicha tanib olinadi va
    dublikat yaratilmaydi (jonli tekshiruvda: 1-so'rov 1 yangi yozuv,
    2-so'rov 0). Matn seed bilan bir xil formatda. **Kim va qaysi dars
    haqida — `presence.py` da, yozuvning o'zi esa S12 dan beri
    `services/notifications.write_notification` da** (kunlik oyna
    `since`/`until` argumentlari orqali).
  - **`Notification.created_at` — UTC, qolgan hamma narsa lokal vaqt.**
    `server_default=func.now()` SQLite'da `CURRENT_TIMESTAMP` ga aylanadi,
    u esa **UTC** yozadi; O'zbekiston UTC+5, ya'ni lokal 00:00-05:00 oralig'ida
    yaratilgan yozuvning `created_at` sanasi **kechagi kun** bo'ladi.
    Shu sabab dublikat tekshiruvi oynasi kechagi yarim tundan boshlanadi
    (`day_start - 1 kun`); jadval satri haftada bir marta takrorlangani uchun
    bu oyna hech qachon haqiqiy yangi ogohlantirishni yashira olmaydi.
    (Bu tuzoq soat 00:00 dan keyin testlar yiqilishi bilan topildi — S12
    boshqa bildirishnoma turlarini yozganda ham shu qoidaga amal qilsin.)
  - **Testlar hafta kuniga bog'liq emas:** `tests/test_s10_teacher_attendance.py`
    daqiqalarni `pair_bounds(TODAY, 3)` dan oladi va tursunov/umarovning
    **3-juftlik** darsiga tayanadi (seed uni har kuni pin qiladi), juftliklar
    ro'yxatini qattiq yozmaydi — shanba (1-3 juftlik) va boshqa kunlarda ham
    o'tadi. Oylik test `?at=` bilan kun oxirini beradi: yarim tunda hali
    birorta juftlik boshlanmagani uchun bugungi darslar aks holda sanalmaydi.
  - **Oylik svod = `ClassSession` hisobi:** `teacher_month_summary(db, actor,
    days=30)` oxirgi N kun (`MAX_MONTH_DAYS = 180`) ichidagi, **boshlangan**
    juftliklarning sessiyalarini sanaydi: `held` (shundan `late` — kirish
    qo'ng'iroqdan keyin), `cancelled`, `needs_clarification`; foiz =
    `held/total`. Eng past foiz **birinchi** qatorda (dekanat aynan shuni
    qidiradi) — demo'da tursunov 8/10 (80%), umumiy 95%.
  - **Xona matni:** `_room_text()` faqat raqam bilan tugaydigan xonaga
    "-xona" qo'shadi (`214-xona`, lekin `103-lab` o'zicha qoladi). S9 dagi
    eski matnlarga tegilmadi.
  - **UI: `/attendance` dekanat uchun uch tab** ("O'qituvchilar" /
    "Oylik jadval" / "Talabalar") — S9 ning guruh mavjudligi ko'rinishi
    yo'qolmadi, `TutorView` uchinchi tabda o'sha holicha ishlatiladi.
    Ranglar `lib/labels.ts` da: `classStateClass` (o'tildi yashil, xavf
    ostida qizil, aniqlashtirish sariq, kechikkan to'q sariq, boshlanmagan/
    qoldirilgan kulrang) va `percentClass` (≥90 yashil, ≥75 sariq, past
    qizil).
  - **Qizil karta soat 23:00 da ham ko'rinadi:** karta ramkasi
    `at_risk_count > 0` YOKI "bugun binoga kirmagan + bugun darsi bor"
    bo'lganda qizil bo'ladi. Sabab: dars vaqtidan keyin holat
    "aniqlashtirish kerak" (sariq) ga o'tadi, lekin demo istalgan soatda
    ko'rsatiladi — kelmagan o'qituvchi baribir ko'zga tashlanishi kerak.
  - **Frontend `?at=` yubormaydi** (S9 qarori kuchda): demo soati faqat
    backend/curl darajasida in'ektsiya qilinadi.
- **S11 qarorlar (hujjat almashinuvi):**
  - **Shablonlar — kod konstantasi, jadval EMAS** (`services/docflow.TEMPLATES`,
    5 ta: `malumotnoma`, `akademik_tatil` (S11 qo'shdi), `qayta_topshirish`,
    `semestr_hisobot`, `buyruq_topshiriq`). Har shablonda `roles` (kim yubora
    oladi), `recipient_role`, `needs_recipient_user`, `needs_due_date` va
    `body_hint` (UI matn maydonini oldindan to'ldiradi) bor. `seed/generate.py`
    ga TEGILMADI — u yozgan 4 ta `template_id` shu katalogda topiladi.
  - **Status zanjiri faqat oldinga:** `TRANSITIONS` —
    `sent → seen|in_progress|approved|rejected`, `seen → in_progress|approved|
    rejected`, `in_progress → approved|rejected`, `approved`/`rejected` →
    **hech qayerga** (terminal, **409**). Orqaga (`… → sent`) yo'l yo'q, bir
    xil holatni qayta qo'yish ham 409. Rad etishda izoh **majburiy** (**422**),
    tasdiqlashda ixtiyoriy. Frontend tugmalarni rolga qarab EMAS, backend
    qaytargan `next_statuses` / `can_change_status` bo'yicha chizadi — qoida
    bitta joyda.
  - **Ikki xil rad javobi, ataylab:** ko'rinmaydigan hujjat → **404**
    (`get_visible_flow` → None; begona arizaning mavjudligi ham oshkor
    bo'lmasin — hujjat/suhbat qoidasi), ko'rinadigan hujjatda qaror qabul
    qilishga ruxsat yo'q → **403** (yuboruvchi o'z arizasini tasdiqlay
    olmaydi). Router avval 404 ni tekshiradi, keyin 403 ni.
  - **Doira uchun yangi mexanizm yozilmadi:** `is_recipient` shaxsga
    yuborilgan hujjatda `recipient_user_id == user.id`, rolga yuborilganda
    `recipient_role == user.role` **va** `rbac.can_access_user(db, user,
    sender)` — ya'ni rolga yo'naltirilgan hujjat **yuboruvchining fakulteti**
    ichida qoladi (yusupov AT arizasini ko'rmaydi). Admin — hammasi.
  - **Bildirishnoma dublikat kaliti ikki xil** (S10 naqshining kengaytmasi):
    `flow_incoming` — `(user, type, link_id)`, matnsiz (shuning uchun seed
    yozgan boshqacha matnli qator tanib olinadi va ikkinchi marta
    yozilmaydi); `flow_status` — matn ham kalitda (har qadam yangi yozuv).
    Ikkalasi ham `link_type="flow_document"`, `link_id=<flow id>`.
  - **`ariza_holati` — `ALL_ROLES`** (`mavjudlik_tekshir` naqshi): cheklov
    ma'lumot qatlamida (`docflow.can_view`), shuning uchun talaba faqat
    o'zinikini so'raydi. Argumentlar: `ariza` (raqam yoki mavzudagi so'z;
    ko'rinmaydigan id "topilmadi" javobini beradi — mavjudligi oshkor
    bo'lmaydi) va `yonalish` (`kelgan`/`yuborilgan`; bo'sh bo'lsa talaba va
    o'qituvchiga — yuborilganlar, dekanat/tyutorga — kelganlar). Javobning
    birinchi qatori majburiy manba formatida:
    `"Ariza №{id}, {sana}, holat: {status}"`, oxirida oxirgi `FlowHistory`
    izohi.
  - **Rezyume uchun S6 buzilmadi:** `services/summarization.summarize_text(...)`
    (mavjud funksiya) `body_text` bilan chaqiriladi — `summarize_document`
    `Document` obyektini kutgani uchun yangi qatlam yozilmadi, prompt
    quruvchilar ham o'zgarmadi. Natijada rol rakursi (dekanat: "raqam, sana,
    ijrochilar") hujjat aylanmasida ham ishlaydi.
  - **Vaqt maydonlari lokal:** `FlowDocument.created_at` va
    `FlowHistory.timestamp` `datetime.now()` bilan aniq yoziladi (server
    default UTC bo'lardi) — seed ham lokal vaqt yozadi, ya'ni tarix qatorlari
    bir xil o'lchovda. `Notification.created_at` esa hamon UTC (S10 qaydi).
  - **UI: bitta sahifa, uch savol** (`/docflow`, navigatsiyada "Arizalar",
    hamma rolga ochiq): talaba — "Arizalarim" (tab yo'q, faqat yuborilganlar +
    "Yangi ariza"), o'qituvchi/tyutor/dekanat/admin — ikki tab
    ("Kelgan hujjatlar" / "Yuborilganlar"), saralash `new`/`due`. Qaror
    tugmalari faqat `can_change_status` bo'lganda; "Rad etish" avval sabab
    maydonini ochadi (klientda ham, serverda ham majburiy). Komponentlar:
    `FlowList`, `FlowDetailPanel`, `FlowComposer`. Next 16 qoidasi uchun
    holat derivatsiya qilinadi: ochilgan hujjat `detail.id === selectedId`,
    rezyume `summary.flow_id === detail.id`, qaror formasi
    `pending.flowId === detail.id`, yangi hujjat matni `body ?? body_hint`.
- **S12 qarorlar (bildirishnomalar markazi):**
  - **Yagona yozuvchi: `services/notifications.write_notification(db, user_id,
    notif_type, text, link_type, link_id, *, match_text=True, since=None,
    until=None)`.** Loyihada bildirishnoma FAQAT shu funksiya orqali
    yoziladi. Dublikat kaliti `(user_id, notif_type, link_type, link_id
    [, text])`: `match_text=False` — hodisa obyektga bir marta bo'ladi
    (`flow_incoming`, `payment_uploaded`, `payment_confirmed`,
    `payment_debt`, `teacher_absence`), shuning uchun seed yozgan
    boshqacha matnli qator ham tanib olinadi va ustiga yozilmaydi;
    `match_text=True` — har qadam yangi voqea (`flow_status`, `flow_due`,
    `class_absent`). `since`/`until` — S10 ning "kunlik oyna" ehtiyoji
    (haftalik takrorlanadigan jadval satri keyingi hafta yana ogohlantirsin).
    `db.commit()` chaqiruvchida (bir trigger bir nechta qator yozadi).
  - **Ikki xil trigger, ataylab:** (a) hodisa yozadiganlar —
    `payments.upload_receipt`/`confirm_payment` (S8), `presence.mark_attendance`
    (S9), `presence.record_risk_notifications` (S10),
    `docflow.notify_incoming`/`notify_status` (S11); (b) qo'ng'iroqcha
    ochilganda **hisoblanadiganlar** — kontrakt qarzdorligi va ijro muddati
    (`refresh_triggers`, `GET /notifications` ichida). Cron/fon vazifasi
    YO'Q (ISH_REJA S12: "sodda yo'l — login/sahifa ochilganda hisoblash").
    GET ning yon ta'siri S10 da qabul qilingan naqsh.
  - **`flow_due` matnida "N kun qoldi" YO'Q** — aks holda har kuni yangi
    qator paydo bo'lardi. Bitta hujjat butun umri davomida ko'pi bilan
    ikkita yozuv beradi: "Ijro muddati yaqin: … — 16.08.2026 gacha." va
    "Ijro muddati o'tdi: … — muddat 16.08.2026 edi.". Ijrochi ham,
    yuboruvchi ham o'z `inbox`/`outbox` ro'yxatidan oladi — S11 ning
    `overdue` / `due_in_days` / `DUE_SOON_DAYS` hisoblagichlari ishlatildi,
    yangi so'rov yozilmadi.
  - **UTC → lokal servisda o'giriladi:** `Notification.created_at` DB da UTC
    (SQLite `CURRENT_TIMESTAMP`), lekin `feed()` qaytaradigan har qator
    `to_local()` dan o'tadi (`datetime.now().astimezone().utcoffset()` —
    mashinaga bog'liq, +5 hardcode qilinmagan). Shuning uchun qo'ng'iroqcha,
    chat javobi va qolgan hamma sahifa bir xil soatni ko'rsatadi. Dublikat
    oynalari esa hamon kechagi yarim tundan boshlanadi (S10 tuzog'i).
  - **Qarzdorlik: `link_type="contract"`, `link_id=None`, `match_text=False`**
    — ya'ni har odamda ko'pi bilan bitta eslatma bo'ladi va seed'dagi
    karimov qatori qayta ishlatiladi (summa matni o'zgarsa ham ikkinchi
    qator yozilmaydi). Talabaga — o'z qoldig'i, tyutorga — guruh svodi
    ("Guruhingizda 4 ta talaba … qarzdor"). O'qituvchi/dekanat qarzdorlik
    eslatmasini olmaydi (FUNKSIONALLIK 3.10: "talaba, tyutor").
  - **`link_type` → sahifa jadvali frontendda bitta joyda**
    (`lib/labels.ts: notificationHref`): `flow_document` → `/docflow`,
    `schedule` → `/attendance`, `assignment` → `/documents`,
    `payment`/`contract` → **rolga qarab** `/contract` (talaba) yoki
    `/group` (tyutor/dekanat/admin) — konventsiyaning yagona rolga bog'liq
    satri, chunki tyutorda kontrakt sahifasi yo'q.
  - **Ikkala POST ham yangilangan ro'yxatni qaytaradi** (`NotificationListOut`)
    — S8 dagi `confirm` naqshi: qo'ng'iroqcha sanoqni yangilash uchun
    ikkinchi so'rov yubormaydi. Begona bildirishnoma → **404**
    (hujjat/suhbat qoidasi: mavjudligi ham oshkor bo'lmaydi).
  - **`bildirishnomalar` tooli — `ALL_ROLES`** (`ariza_holati` naqshi):
    cheklov ma'lumot qatlamida (`Notification.user_id == user.id`).
    Javobning BIRINCHI qatori manba yorlig'ining o'zi
    ("Bildirishnomalar ro'yxati, 15.08.2026 (2 ta o'qilmagan)") va
    `sources[0]["label"]` bilan aynan bir xil — test shuni qotiradi.
    Argumentlar: `holat` ("hammasi" bo'lsa o'qilganlar ham), `nechta`.
  - **`NotifBell` — bitta so'rov, 60 s polling.** Ro'yxat va `unread_count`
    bitta javobda kelgani uchun badge alohida so'rov talab qilmaydi;
    "faqat o'qilmaganlar" filtri klientda (qo'shimcha so'rov yo'q).
    `setState` faqat `.then()` va hodisa ishlovchilarida (Next 16
    `react-hooks/set-state-in-effect`). Panel tashqarisiga bosilsa yopiladi.
  - **Seed O'ZGARMADI** — 15 demo qatori (jumladan sharipovaning
    `payment_uploaded` i va karimovning `payment_debt` i) joyida qoldi va
    yangi triggerlar ular bilan dublikat yaratmaydi (jonli tekshiruvda
    isbotlangan).
  - **Ko'chirish, qayta yozish emas:** `presence.record_risk_notifications`
    va `docflow.notify_incoming`/`notify_status` NOMLARI saqlandi (S10/S11
    testlari ularga tayanadi), ichkarida esa endi `write_notification`
    chaqiriladi; `docflow._write_notification` yupqa o'ram bo'lib qoldi.
- **S1 texnik qarorlar:**
  - Juftlik vaqtlari (ichki tartib nizomi 3.1-band bilan bir xil):
    1) 08:30-09:50, 2) 10:00-11:20, 3) 11:30-12:50, 4) 13:30-14:50,
    5) 15:00-16:20, 6) 16:30-17:50. **S9 dan beri yagona joyda:**
    `app/services/presence.py` → `PAIR_TIMES` (`time` obyektlari) va
    `PAIR_TIME_LABELS` (satrlar); seed ham, `jadval_kor` tooli ham shundan
    import qiladi.
  - Jadval Dush-Shan (weekday 0-5), 1-4-juftlik (shanba 1-3), deterministik
    rotatsiya — o'qituvchi/xona to'qnashuvlari yo'q (SQL bilan tekshirilgan).
    Aliyev guruhining bugungi jadvali 2-juftlikdan boshlanadi (10:02 da
    kirgani bilan zid kelmasligi uchun).
  - Turniket loglari faqat "bugun" (skript ishga tushgan kun) uchun
    yaratiladi; bugungi davomat kunning HAMMA juftliklari uchun oldindan,
    turniket loglaridan hisoblab yoziladi — demo istalgan soatda ishlaydi.
    (Ertalab ishga tushirilsa ba'zi loglar/davomat "kelajakda" bo'ladi —
    demo uchun qabul qilingan soddalashtirish.)
  - Topshiriq deadlinelari nisbiy (bugun +4/+7/+11/+18 kun, 23:59) — hujjat
    matnlarida qat'iy sana YO'Q ("e'lon qilingan kundan N kun" deyilgan),
    shuning uchun DB va hujjat zid kelmaydi; S12 deadline triggerlari har
    resetdan keyin ham ishlayveradi.
  - Hujjat kirish darajalari: hammasi `public`, faqat "Buyruq 91-M
    (attestatsiya)" — `staff` (demo ssenariyda talabaga rad etiladi).
    `Document.file_path` — backend/ ga nisbatan yo'l (`seed/documents/...`).
  - Kontrakt summalari: fakultet 1 → 12 000 000, fakultet 2 → 10 500 000
    so'm; to'liq to'lov sxemasi 40/30/30 (nizom 5.1-band bilan mos).
  - Chek raqamlari: `CLK-...` (avtomatik, sintetik Click), `CHK-...`
    (qo'lda yuklangan). `Payment.receipt_file` — faqat yo'l-platzholder
    (`uploads/receipts/...`), haqiqiy fayl yo'q.

## Keyinga qoldirilganlar

- **FUNKSIONALLIK 3.10 jadvalining uch qatori hali triggersiz:** "Topshiriq
  deadline'i yaqinlashdi (3 kun / 1 kun)", "Yangi topshiriq/material
  qo'shildi" va "Yangi buyruq e'lon qilindi". Sabab — `Assignment` modeli
  bor, lekin unga endpoint ham, UI ham yo'q (topshiriqlar faqat seed'da va
  hujjat matnlarida), buyruq e'lon qilish esa admin ishi. Seed'dagi
  `new_assignment` qatorlari demo uchun qoladi. S13 (admin hujjat yuklashi →
  `new_order`) yoki S14 da qo'shilsin — `write_notification` tayyor, faqat
  chaqiruv joyi kerak.
- **Bildirishnomani o'chirish/arxivlash YO'Q:** faqat "o'qildi" belgisi
  (orqaga qaytarish ham yo'q). Ro'yxat `limit` bilan cheklanadi
  (default 30, maksimum 100), sahifalash (`offset`/kursor) yo'q — demo
  hajmida 15-25 qator bo'ladi.
- **Real-time yo'q:** qo'ng'iroqcha 60 soniyada bir marta so'rov yuboradi
  (`NotifBell.POLL_MS`); WebSocket/SSE yoki push/SMS/Telegram —
  FUNKSIONALLIK 3.10 dagi **[P2]** kengaytma.
- **`assignment` havolasi taxminiy:** `link_type="assignment"` (seed'dagi
  `new_assignment` qatorlari) `/documents` ga olib boradi — alohida
  "Topshiriqlar" sahifasi yo'q. Sahifa paydo bo'lsa `notificationHref` dagi
  bitta qator o'zgaradi.
- **Hujjatga fayl ilova qilinmaydi:** `FlowDocument.file_path` hech qachon
  to'ldirilmaydi (ariza — faqat matn). S13 da fayl saqlash qo'shilsa
  `multipart/form-data` endpoint + `uploads/` papkasi kerak bo'ladi (S8 dagi
  chek fayli bilan bir xil qaror).
- **Rad etilgan arizani tahrirlab qayta yuborish yo'li yo'q** — yangi hujjat
  yaratiladi (zanjir orqaga qaytmaydi). "Qayta ishlash uchun qaytarish"
  (`returned`) holati kerak bo'lsa `FlowStatus` enumiga qo'shish kerak, ya'ni
  S0 modeliga tegish — S14 gacha qilinmasin.
- **Ijro muddati bildirishnomasi faqat qo'ng'iroqcha ochilganda hisoblanadi**
  (S12 `record_flow_due_notifications`): hech kim `GET /notifications` ni
  chaqirmasa yozuv ham paydo bo'lmaydi. Hujjat ro'yxatining o'zi
  (`/docflow`) buni chaqirmaydi — kerak bo'lsa S14 da `inbox`/`outbox` ga
  ham qo'shiladi.
- **Hujjat aylanmasida tyutor qabul qiluvchi emas:** birorta shablon
  `recipient_role=tutor` bilan kelmaydi, ya'ni tyutorning "Kelgan hujjatlar"
  tabi doim bo'sh (faqat unga shaxsan yuborilgan buyruq tushishi mumkin).
  Kerak bo'lsa `TEMPLATES` ga bitta qator qo'shiladi.
- **Flow rezyumesi keshlanmaydi** (hujjat rezyumesi bilan bir xil muammo):
  har bosishda LLM qayta chaqiriladi.
- **"Xavf ostida" bildirishnomasi faqat svod so'ralganda yoziladi**
  (`GET /attendance/teachers` yon ta'siri). S12 uni umumiy servisga ko'chirdi,
  lekin **qo'ng'iroqcha ochilganda hisoblanmaydi**: butun fakultetning
  kunlik svodini har `GET /notifications` da qayta qurish qimmat. Ya'ni
  dekanat `/attendance` sahifasini ochmasa yangi "xavf ostida" yozuvi
  paydo bo'lmaydi (seed bugungi qatorni oldindan yozgani uchun demo
  baribir ishlaydi).
- **Oylik svodda sana oralig'ini tanlash yo'q:** `?days=` (default 30,
  maksimum 180) faqat "oxirgi N kun" beradi; seed esa atigi 5 ish kuni +
  bugungi `ClassSession` yozadi, ya'ni "oylik" jadval amalda 6 kunlik.
  Haqiqiy oy kesimi kerak bo'lsa seed tarixini uzaytirish kerak (S13/S14).
- **Eksport (P2) qilinmadi:** FUNKSIONALLIK 3.8 dagi "hisobot uchun eksport"
  **[P2]** deb belgilangan — CSV/XLSX yuklab olish S14 ga qoldirildi.
- **Dekanat ko'rinishida fakultet kesimidagi talaba davomati foizi hamon
  yo'q** (S9 dan qolgan qayd): `/attendance/teachers` faqat o'qituvchilarni
  qamraydi, "fakultet bo'yicha bugun davomat 87%" ko'rsatkichi
  `group_presence` ma'lumotidan S13/S14 da yig'ilsin.
- **Kichik ekran (mobil) layouti:** hujjat paneli va dashboard `lg:` dan
  kichik ekranda yashiringan — telefonda manba chipini bosish ko'zga
  ko'rinadigan natija bermaydi. S14 (sayqal) da modal/drawer qilinsin.
- **`type: "schedule"` / `"turnstile"` / `"attendance"` manba chiplari
  bosilmaydi** — `SourceChips` faqat `document` chipini havolaga aylantiradi.
  Endi ochadigan sahifa bor (`/attendance`), shuning uchun S14 (sayqal) da shu
  uch tur ham havolaga aylantirilsin.
- Suhbatni o'chirish/nomini o'zgartirish YO'Q (faqat ro'yxat + yangi suhbat).
  Kerak bo'lsa S13 (admin) yoki S14 da qo'shiladi.
- `schemas.DocumentOut`, `ChunkOut`, `ContractOut`, `PaymentOut`,
  `FlowDocumentOut`, `FlowHistoryOut` (S0 dan qolgan) hech qayerda
  ishlatilmaydi — S5, S8 va S11 o'z sxemalarini qo'shdi
  (`DocumentListItemOut`/`DocumentDetailOut`, `ContractSummaryOut`/
  `PaymentRowOut`, `FlowItemOut`/`FlowDetailOut`/`FlowListOut`). Kerak
  bo'lmasa S14 da tozalansin. `NotificationOut` S12 da ishga tushdi
  (`NotificationListOut` bilan birga).
- **Davomat bildirishnomasi faqat talabaning o'ziga boradi** (S12
  `class_absent`): "farzandingiz darsga kelmadi" uchun ota-ona roli ham,
  aloqa kanali ham yo'q (FUNKSIONALLIK 3.10 da ota-ona yo'q). Bir darsda
  10 ta talaba `absent` bo'lsa 10 ta yozuv yoziladi — demo hajmida muammo
  emas, ommaviy tizimda guruhlash kerak bo'ladi.
- **`/attendance` sahifasi kichik ekranda siqiladi:** o'qituvchi ko'rinishi
  ikki ustunli (`w-80` ro'yxat + varaq), telefonda tor bo'ladi. S14 da
  ro'yxat drawer/accordion ga o'tkazilsin (chat va `/group` bilan bir xil
  muammo).
- **Guruh mavjudligida fakultet kesimi yo'q:** `attendance_percent` faqat
  chaqiruvchi doirasi bo'yicha hisoblanadi. FUNKSIONALLIK 3.7 dagi
  "fakultet kesimida: bugun davomat 87%" dekanat ko'rinishi S10 da
  qo'shilsin (ma'lumot allaqachon `group_presence` da bor, faqat guruhlar
  bo'yicha guruhlash kerak).
- **Davomat tarixida sana filtri yo'q:** `?days=` (default 7, maksimum 60)
  oxirgi N kunni beradi, oraliq tanlash (`from`/`to`) yo'q. Oylik hisobot
  (S10 dagi "oylik svod") kerak bo'lsa endpointga qo'shiladi.
- **Rezyume keshlanmaydi** — bitta hujjatga har bosishda LLM qayta
  chaqiriladi (rol bo'yicha farq qilgani uchun kesh kaliti
  `(document_id, role)` bo'lishi kerak). S7 da `Translation` keshi yozildi
  (`services/translation.py` dagi `cached_row`/`store_translation` naqshi) —
  S14 da xuddi shuni rezyumega qo'llash mumkin; hozircha demo tezligi yetarli.
- **Tarjima sifati Gemini bilan tekshirilmagan:** mock rejimda tarjima MATNI
  deterministik echo, shuning uchun ISH_REJA S7 DoD dagi "inglizcha maqola
  yonma-yon o'zbekchada o'qiladi" bandini faqat mexanika darajasida
  (paragraf tekisligi, kesh, ruxsat, prompt) tasdiqlash mumkin bo'ldi.
  S14 da kalit ulangach ko'rilsin: (a) atama naqshi ("… (machine learning)")
  haqiqatan chiqyaptimi, (b) model `[[n]]` markerlariga rioya qiladimi —
  qilsa chaqiruvlar soni 25 dan 2 ga tushadi (`translate_document` natijasidagi
  `llm_calls` shuni ko'rsatadi), qilmasa `BATCH_CHARS` ni kichraytirish yoki
  prompt matnini kuchaytirish kerak.
- **Bo'lak (chunk) tarjimasi ishlatilmaydi:** `Translation.chunk_id` bo'sh
  qoladi — chatdagi sitata tarjimasi hozircha alohida keshlanmaydi (butun
  hujjat tarjimasi kifoya). Kerak bo'lsa S14 da.
- **`MAX_PARAGRAPHS = 80` chegarasi demo korpusida hech qachon urilmaydi**
  (eng uzun hujjatda 38 paragraf), ya'ni `truncated=true` yo'li jonli
  ko'rilmagan — faqat testda. PDF/DOCX qo'shilsa (S13) qayta ko'rilsin.
- **Tarjima keshi rolga bog'liq emas** (tarjima rakursi yo'q, rezyumeda bor).
  Bu ataylab: bir hujjatning bir tildagi tarjimasi hamma uchun bir xil.
  Agar S14 da "fan bo'yicha lug'at" (FUNKSIONALLIK 3.5 dagi **[?]**) qo'shilsa,
  kesh kalitiga lug'at versiyasi qo'shilishi kerak bo'ladi.
- **Rezyume sifati Gemini bilan tekshirilmagan:** ISH_REJA S6 DoD dagi
  "2 sahifalik buyruq 5-6 qatorli aniq rezyumega tushadi" bandi mock
  rejimda o'lchab bo'lmaydi (matn — deterministik echo). S14 da kalit
  ulangach 3 rolda qayta ko'rilsin; kerak bo'lsa `SYSTEM_BASE` va
  `ROLE_POINTS` matnlari o'sha yerda sozlanadi.
- **`_document_text` mantiqi ikki joyda emas, lekin `extract_text` faqat
  `.md/.txt` ni biladi** — S13 da PDF/DOCX qo'shilsa rezyume ham avtomatik
  ishlaydi (u `services/documents.document_text` ga tayanadi).
- Gemini provayderi hali `NotImplementedError` — kalit ulangach
  `GeminiLLMClient.chat()` yozilishi kerak (neytral message/tool formatini
  google-genai formatiga o'girish). Butun tizim shu bitta metodga bog'liq.
- **Chek FAYLI hech qachon yuklanmaydi** (S8 qarori: chek — strukturali
  ma'lumot). Yangi yuklangan to'lovlarda `Payment.receipt_file = None`,
  seed'dagilarda esa mavjud bo'lmagan yo'l turadi. Agar S13 da fayl saqlash
  qo'shilsa: `multipart/form-data` endpoint + `uploads/` papkasi + `ReceiptOut`
  ga `file_url` maydoni kerak bo'ladi.
- **To'lov bildirishnomasi tyutorga boradi, dekanatga emas** (S12):
  `upload_receipt` faqat guruh tyutoriga yozadi (`Group.tutor_id`), guruhda
  tyutor bo'lmasa hech kim xabar olmaydi. Dekanat/buxgalteriya kanali kerak
  bo'lsa `notifications._tutors_of` kengaytiriladi.
- **`/group` sahifasining o'ng paneli `lg:` dan kichik ekranda yashirin**
  (chat sahifasidagi bilan bir xil muammo) — telefonda talaba qatorini bosish
  ko'zga ko'rinadigan natija bermaydi. S14 da modal/drawer bilan yechilsin.
- **Kontrakt to'lovlari uchun sana filtri yo'q:** `academic_year` bo'yicha eng
  oxirgi kontrakt olinadi (demo'da har talabada bittadan). Ko'p yillik tarix
  kerak bo'lsa endpointga `?academic_year=` qo'shiladi.
- Qidiruv sifati: 24 savollik o'lchovda 4-5 tasi hali ham xato hujjatni
  birinchi qo'yadi (masalan "birlamchi kalit va tashqi kalit" → ruscha hujjat
  o'rniga inglizcha ML hujjati; savolda ruscha atama bilan hech qanday
  leksik moslik yo'q). Sabab — 118M parametrli kichik modelning chegarasi.
  Agar S14 da vaqt bo'lsa: kattaroq model (`bge-m3`, `LaBSE`) yoki
  savolni LLM bilan inglizcha/ruschaga kengaytirish (query expansion)
  sinab ko'rilsin. MVP uchun hozirgi sifat yetarli (talaba ko'rinishida
  top-1 20/23, top-3 21/23).
- `Document.language` maydoni ingest da metadata sifatida yoziladi, lekin
  til bo'yicha FILTR hali qo'llanilmaydi (tillar aro qidiruv shart) — S7
  tarjima moduli kerak bo'lsa shu metadatadan foydalanadi.
- Faqat `.md`/`.txt` fayllar indekslanadi (`app/rag/ingest.py`
  `SUPPORTED_SUFFIXES`) — S13 da PDF/DOCX yuklash kerak bo'lsa,
  `extract_text()` kengaytiriladi.

## Ochiq savollar

`FUNKSIONALLIK_LOGIKA.md` 9-bo'limga qarang — javoblar shu yerga ko'chiriladi.
