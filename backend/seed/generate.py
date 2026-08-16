"""Synthetic demo data generator for UniAgent.

Usage (from backend/, venv active):
    python -m seed.generate --reset

Creates the full demo scenario: 2 faculties, 4 groups, ~30 students,
8 teachers, 2 tutors, 2 staff, 1 admin, weekly schedule, contracts and
payments (paid / partial / debtor), today's turnstile logs (someone inside,
someone left, one teacher absent for his class), attendance + class sessions,
document corpus registration, flow documents and notifications.

Demo heroes (fixed, see PROGRESS.md):
    aliyev   - student, in building, attendance marked, no debt, approved app
    karimov  - student, debtor (0 paid), absent today
    sodiqova - student, partially paid, entered and left the building
    mahmudov - student, in building but not marked in attendance (S9 case)
    tursunov - teacher, has a class today but never entered (S10 case)
"""

import argparse
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from random import Random

from app import models as m
from app.auth.passwords import hash_password
from app.db import SessionLocal, init_db

# Pair times live in ONE place (S9): the presence service imports nothing from
# the seed, so this is a plain shared constant, not a dependency inversion.
from app.services.presence import PAIR_TIMES

RND = Random(42)

BACKEND_DIR = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = BACKEND_DIR / "seed" / "documents"

DEMO_PASSWORD = "demo123"  # every demo user logs in with this password

# --- static rosters ---------------------------------------------------------

GROUP_DEFS = [
    # (name, faculty_id, tutor_username)
    ("AT-24-01", 1, "nazarova"),
    ("AT-24-02", 1, "nazarova"),
    ("IQ-24-01", 2, "qodirova"),
    ("IQ-24-02", 2, "qodirova"),
]

STUDENT_DEFS = {
    "AT-24-01": [
        ("aliyev", "Aliyev Jasur"),
        ("karimov", "Karimov Diyor"),
        ("sodiqova", "Sodiqova Malika"),
        ("rahimov", "Rahimov Sardor"),
        ("torayeva", "To'rayeva Nilufar"),
        ("yusupova", "Yusupova Kamola"),
        ("mahmudov", "Mahmudov Aziz"),
        ("qosimova", "Qosimova Sevara"),
    ],
    "AT-24-02": [
        ("abdullayev", "Abdullayev Timur"),
        ("ibragimova", "Ibragimova Zarina"),
        ("nazarov", "Nazarov Ulug'bek"),
        ("sharipova", "Sharipova Gulnora"),
        ("olimov", "Olimov Bobur"),
        ("xudoyberdiyev", "Xudoyberdiyev Sanjar"),
        ("mirzayeva", "Mirzayeva Dildora"),
        ("ganiyev", "G'aniyev Otabek"),
    ],
    "IQ-24-01": [
        ("ismatov", "Ismatov Farrux"),
        ("roziyeva", "Ro'ziyeva Shahnoza"),
        ("jorayev", "Jo'rayev Dilshod"),
        ("berdiyeva", "Berdiyeva Munisa"),
        ("hamidov", "Hamidov Javohir"),
        ("saidov", "Saidov Akbar"),
        ("norboyeva", "Norboyeva Oysha"),
    ],
    "IQ-24-02": [
        ("elmurodov", "Elmurodov Shohruh"),
        ("tosheva", "Tosheva Madina"),
        ("ochilov", "Ochilov Suxrob"),
        ("qurbonova", "Qurbonova Laylo"),
        ("boboyev", "Boboyev Islom"),
        ("ergasheva", "Ergasheva Nigora"),
        ("ravshanov", "Ravshanov Doston"),
    ],
}

TEACHER_DEFS = [
    # (username, full_name, faculty_id)
    ("umarov", "Umarov Sherzod", 1),
    ("tursunov", "Tursunov Akmal", 1),  # HERO: absent teacher (S10)
    ("bekmurodov", "Bekmurodov Alisher", 1),
    ("ismoilova", "Ismoilova Nodira", 1),
    ("xolmatov", "Xolmatov Rustam", 1),
    ("saidova", "Saidova Feruza", 2),
    ("ergashev", "Ergashev Zafar", 2),
    ("muminova", "Muminova Gulchehra", 2),
]

TUTOR_DEFS = [
    ("nazarova", "Nazarova Dilfuza", 1),
    ("qodirova", "Qodirova Madina", 2),
]

STAFF_DEFS = [
    ("rashidova", "Rashidova Nilufar", 1),
    ("yusupov", "Yusupov Bekzod", 2),
]

ADMIN_DEF = ("admin", "Abdusattorov Botir", None)

# --- weekly schedule rotation ----------------------------------------------

FAC1_SUBJECTS = [
    ("Ma'lumotlar bazasi", "umarov"),
    ("Dasturlash asoslari", "bekmurodov"),
    ("Kompyuter tarmoqlari", "tursunov"),
    ("Ingliz tili", "ismoilova"),
    ("Matematik tahlil", "xolmatov"),
]
FAC2_SUBJECTS = [
    ("Iqtisodiyot nazariyasi", "saidova"),
    ("Buxgalteriya hisobi", "ergashev"),
    ("Statistika", "muminova"),
    ("Ingliz tili", "ismoilova"),
    ("Matematik tahlil", "xolmatov"),
]
HOME_ROOMS = {"AT-24-01": "214", "AT-24-02": "215", "IQ-24-01": "310", "IQ-24-02": "311"}
SUBJECT_ROOMS = {
    "Ingliz tili": "108",
    "Matematik tahlil": "305",
    "Dasturlash asoslari": "101-lab",
    "Kompyuter tarmoqlari": "103-lab",
}

# --- documents corpus -------------------------------------------------------

DOCUMENT_DEFS = [
    # (filename, title, doc_type, language, access_level)
    ("syllabus_malumotlar_bazasi.md", "Ma'lumotlar bazasi — fan dasturi (syllabus)",
     m.DocumentType.syllabus, "uz", m.AccessLevel.public),
    ("topshiriq_1_sql_sorovlar.md", "Topshiriq 1: SQL so'rovlar (Ma'lumotlar bazasi)",
     m.DocumentType.assignment, "uz", m.AccessLevel.public),
    ("topshiriq_2_er_diagramma.md", "Topshiriq 2: ER-diagramma loyihalash (Ma'lumotlar bazasi)",
     m.DocumentType.assignment, "uz", m.AccessLevel.public),
    ("topshiriq_3_normalizatsiya.md", "Topshiriq 3: Normalizatsiya (Ma'lumotlar bazasi)",
     m.DocumentType.assignment, "uz", m.AccessLevel.public),
    ("topshiriq_4_python_funksiyalar.md", "Topshiriq 4: Python funksiyalar (Dasturlash asoslari)",
     m.DocumentType.assignment, "uz", m.AccessLevel.public),
    ("ichki_tartib_nizomi.md", "Universitet ichki tartib-qoidalari nizomi",
     m.DocumentType.regulation, "uz", m.AccessLevel.public),
    ("stipendiya_nizomi.md", "Stipendiya tayinlash va to'lash tartibi nizomi",
     m.DocumentType.regulation, "uz", m.AccessLevel.public),
    ("talaba_faq.md", "Talabalar uchun ko'p so'raladigan savollar (FAQ)",
     m.DocumentType.other, "uz", m.AccessLevel.public),
    ("buyruq_2026_87_oquv_yili.md", "Buyruq 87-U: 2026-2027 o'quv yiliga tayyorgarlik",
     m.DocumentType.order, "uz", m.AccessLevel.public),
    ("buyruq_2026_91_attestatsiya_maxfiy.md",
     "Buyruq 91-M: O'qituvchilar attestatsiyasi (xizmat foydalanishi uchun)",
     m.DocumentType.order, "uz", m.AccessLevel.staff),  # confidential!
    ("intro_machine_learning_en.md", "Introduction to Machine Learning (Chapter 1)",
     m.DocumentType.literature, "en", m.AccessLevel.public),
    ("vvedenie_v_bazy_dannyh_ru.md", "Введение в базы данных (глава 1)",
     m.DocumentType.literature, "ru", m.AccessLevel.public),
]

# Assignments: (subject, teacher, description, deadline offset in days)
ASSIGNMENT_DEFS = [
    ("Ma'lumotlar bazasi", "umarov",
     "Topshiriq 1: SQL so'rovlar — 'kutubxona' sxemasi bo'yicha 10 ta SELECT/JOIN "
     "so'rov yozish. Batafsil: 'Topshiriq 1: SQL so'rovlar' hujjatida.", 4),
    ("Ma'lumotlar bazasi", "umarov",
     "Topshiriq 2: 'Universitet o'quv jarayoni' predmet sohasi uchun ER-diagramma "
     "loyihalash. Batafsil: 'Topshiriq 2: ER-diagramma loyihalash' hujjatida.", 11),
    ("Ma'lumotlar bazasi", "umarov",
     "Topshiriq 3: berilgan NATIJALAR jadvalini 3NF gacha normallashtirish. "
     "Batafsil: 'Topshiriq 3: Normalizatsiya' hujjatida.", 18),
    ("Dasturlash asoslari", "bekmurodov",
     "Topshiriq 4: 5 ta Python funksiya (ekub, palindrom, ikkinchi eng katta, "
     "so'z chastotasi, kalkulyator). Batafsil: 'Topshiriq 4: Python funksiyalar' "
     "hujjatida.", 7),
]

# --- payments ---------------------------------------------------------------

FACULTY_CONTRACT_TOTALS = {1: 12_000_000, 2: 10_500_000}
DEBTOR_USERNAMES = {"karimov", "olimov", "hamidov", "tosheva"}  # 0 paid
PARTIAL_USERNAMES = {"sodiqova", "sharipova", "roziyeva", "berdiyeva", "boboyev"}
ACADEMIC_YEAR = "2025-2026"

# --- today's turnstile plans ------------------------------------------------

IN = m.TurnstileDirection.entry
OUT = m.TurnstileDirection.exit

# Fixed plans for heroes and non-student roles: list of (hour, minute, direction)
FIXED_LOG_PLANS = {
    "aliyev": [(10, 2, IN)],                                # HERO: inside since 10:02
    "karimov": [],                                          # HERO: absent today
    "sodiqova": [(8, 12, IN), (13, 15, OUT)],               # HERO: entered, then left
    "mahmudov": [(8, 7, IN)],                               # inside, skips class (S9)
    "umarov": [(7, 55, IN)],
    "tursunov": [],                                         # HERO: absent teacher (S10)
    "bekmurodov": [(8, 5, IN)],
    "ismoilova": [(8, 10, IN)],
    "xolmatov": [(7, 50, IN), (14, 55, OUT)],
    "saidova": [(8, 15, IN)],
    "ergashev": [(8, 2, IN), (13, 5, OUT)],
    "muminova": [(8, 20, IN)],
    "nazarova": [(8, 40, IN)],
    "qodirova": [(8, 35, IN), (12, 30, OUT), (13, 10, IN)],
    "rashidova": [(8, 15, IN)],
    "yusupov": [(8, 25, IN)],
    "admin": [(8, 0, IN)],
}

# Deletion order: children first (SQLite does not enforce FKs here, but keep it clean)
ALL_MODELS = [
    m.ChatMessage, m.Conversation,
    m.Notification, m.FlowHistory, m.FlowDocument, m.ClassSession, m.Attendance,
    m.TurnstileLog, m.Payment, m.Contract, m.Schedule, m.Assignment,
    m.Translation, m.Chunk, m.Document, m.User, m.Group,
]

COUNT_TABLES = [
    (m.User, "users"), (m.Group, "groups"), (m.Document, "documents"),
    (m.Chunk, "chunks"), (m.Translation, "translations"),
    (m.Assignment, "assignments"), (m.Schedule, "schedules"),
    (m.Contract, "contracts"), (m.Payment, "payments"),
    (m.TurnstileLog, "turnstile_logs"), (m.Attendance, "attendances"),
    (m.ClassSession, "class_sessions"), (m.FlowDocument, "flow_documents"),
    (m.FlowHistory, "flow_history"), (m.Notification, "notifications"),
]


def reset_db(db):
    for model in ALL_MODELS:
        db.query(model).delete(synchronize_session=False)
    db.commit()
    print("Reset: barcha jadvallar tozalandi.")


def create_users_and_groups(db):
    """Returns (users_by_username, groups_by_name)."""
    users: dict[str, m.User] = {}
    groups: dict[str, m.Group] = {}
    # One hash for all demo users (same password) — keeps seeding fast.
    demo_hash = hash_password(DEMO_PASSWORD)

    for name, fac, _tutor in GROUP_DEFS:
        g = m.Group(name=name, faculty_id=fac)
        db.add(g)
        groups[name] = g
    db.flush()

    def add_user(username, full_name, role, faculty_id=None, group=None):
        u = m.User(
            username=username,
            password_hash=demo_hash,
            full_name=full_name,
            role=role,
            faculty_id=faculty_id,
            group_id=group.id if group else None,
            language="uz",
        )
        db.add(u)
        users[username] = u
        return u

    for gname, roster in STUDENT_DEFS.items():
        g = groups[gname]
        for username, full_name in roster:
            add_user(username, full_name, m.UserRole.student, g.faculty_id, g)

    for username, full_name, fac in TEACHER_DEFS:
        add_user(username, full_name, m.UserRole.teacher, fac)
    for username, full_name, fac in TUTOR_DEFS:
        add_user(username, full_name, m.UserRole.tutor, fac)
    for username, full_name, fac in STAFF_DEFS:
        add_user(username, full_name, m.UserRole.staff, fac)
    add_user(ADMIN_DEF[0], ADMIN_DEF[1], m.UserRole.admin, ADMIN_DEF[2])
    db.flush()

    for name, _fac, tutor_username in GROUP_DEFS:
        groups[name].tutor_id = users[tutor_username].id
    db.flush()
    return users, groups


def create_schedule(db, users, groups, today_wd):
    """Weekly schedule (Mon-Sat, pairs 1-4, Sat 1-3) with demo pins for today."""
    rows: dict[tuple[int, int, int], m.Schedule] = {}
    group_list = [groups[name] for name, _f, _t in GROUP_DEFS]

    def room_for(subject, group):
        return SUBJECT_ROOMS.get(subject, HOME_ROOMS[group.name])

    def add_row(group, weekday, pair, subject, teacher_username):
        row = m.Schedule(
            group_id=group.id,
            subject=subject,
            room=room_for(subject, group),
            weekday=weekday,
            pair_number=pair,
            teacher_id=users[teacher_username].id,
        )
        db.add(row)
        rows[(group.id, weekday, pair)] = row
        return row

    for gi, group in enumerate(group_list):
        subjects = FAC1_SUBJECTS if group.faculty_id == 1 else FAC2_SUBJECTS
        for weekday in range(6):  # Mon-Sat; Sunday is free
            n_pairs = 4 if weekday < 5 else 3
            for pair in range(1, n_pairs + 1):
                # Hero group starts at pair 2 today: Aliyev enters at 10:02
                # and must be "present" in every marked class of the day.
                if gi == 0 and weekday == today_wd and pair == 1:
                    continue
                subject, teacher_username = subjects[(weekday + pair + gi) % 5]
                add_row(group, weekday, pair, subject, teacher_username)

    def pin(group, weekday, pair, subject, teacher_username):
        row = rows.get((group.id, weekday, pair))
        if row is None:  # only possible if today is Sunday
            row = add_row(group, weekday, pair, subject, teacher_username)
        else:
            row.subject = subject
            row.teacher_id = users[teacher_username].id
            row.room = room_for(subject, group)
        return row

    # Demo pins for today (scenario anchors, FUNKSIONALLIK 3.7 / 3.8):
    # - Aliyev's group: pair 3, "Ma'lumotlar bazasi", room 214, teacher present.
    # - AT-24-02: pair 3 taught by Tursunov, who never shows up ("dars xavf ostida").
    pin(groups["AT-24-01"], today_wd, 3, "Ma'lumotlar bazasi", "umarov")
    risk_row = pin(groups["AT-24-02"], today_wd, 3, "Kompyuter tarmoqlari", "tursunov")
    db.flush()
    return rows, risk_row


def create_assignments(db, users, groups, today):
    for gname in ("AT-24-01", "AT-24-02"):
        group = groups[gname]
        for subject, teacher_username, description, offset in ASSIGNMENT_DEFS:
            db.add(m.Assignment(
                subject=subject,
                group_id=group.id,
                description=description,
                deadline=datetime.combine(today + timedelta(days=offset), time(23, 59)),
                teacher_id=users[teacher_username].id,
            ))
    db.flush()


def create_documents(db):
    for filename, title, doc_type, language, access in DOCUMENT_DEFS:
        path = DOCUMENTS_DIR / filename
        if not path.exists():
            print(f"OGOHLANTIRISH: hujjat fayli topilmadi: {path}")
        db.add(m.Document(
            title=title,
            doc_type=doc_type,
            language=language,
            access_level=access,
            file_path=f"seed/documents/{filename}",
        ))
    db.flush()


def create_contracts_and_payments(db, users, today):
    """Mix of fully paid / partial / debtor students. Returns uploaded payment."""
    uploaded_payment = None
    students = [u for u in users.values() if u.role == m.UserRole.student]
    for student in students:
        total = FACULTY_CONTRACT_TOTALS[student.faculty_id]
        db.add(m.Contract(
            student_id=student.id, total_amount=total, academic_year=ACADEMIC_YEAR
        ))

        def pay(share, year, month, status=m.PaymentStatus.automatic, paid_at=None):
            amount = int(total * share)
            if paid_at is None:
                paid_at = datetime(
                    year, month, RND.randint(2, 26), RND.randint(9, 17), RND.randint(0, 59)
                )
            if status == m.PaymentStatus.automatic:
                receipt, receipt_file = f"CLK-{RND.randrange(10**7, 10**8)}", None
            else:
                receipt = f"CHK-{RND.randrange(10**5, 10**6)}"
                receipt_file = f"uploads/receipts/chek_{student.username}_{month}.jpg"
            p = m.Payment(
                student_id=student.id, amount=amount, paid_at=paid_at,
                receipt_number=receipt, receipt_file=receipt_file,
                status=status, academic_year=ACADEMIC_YEAR,
            )
            db.add(p)
            return p

        if student.username in DEBTOR_USERNAMES:
            continue  # 0 paid — debtor
        if student.username in PARTIAL_USERNAMES:
            pay(0.30, 2025, 9)
            pay(0.20, 2025, 12, status=m.PaymentStatus.confirmed)
            if student.username == "sharipova":
                # Receipt uploaded yesterday, still waiting for tutor confirmation
                uploaded_payment = pay(
                    0.10, today.year, today.month,
                    status=m.PaymentStatus.uploaded,
                    paid_at=datetime.combine(today - timedelta(days=1), time(16, 40)),
                )
            continue
        # Fully paid: 40% + 30% + 30%
        pay(0.40, 2025, 9)
        pay(0.30, 2025, 11)
        last_status = (
            m.PaymentStatus.confirmed if RND.random() < 0.25 else m.PaymentStatus.automatic
        )
        pay(0.30, 2026, 2, status=last_status)
    db.flush()
    return uploaded_payment


def create_turnstile_logs(db, users, today):
    """Today's logs. Returns {username: [(datetime, direction), ...]}."""
    plans: dict[str, list[tuple[datetime, m.TurnstileDirection]]] = {}

    def to_dt(h, mm):
        return datetime.combine(today, time(h, mm))

    for username, plan in FIXED_LOG_PLANS.items():
        plans[username] = [(to_dt(h, mm), d) for h, mm, d in plan]

    students = [u for u in users.values() if u.role == m.UserRole.student]
    for student in students:
        if student.username in plans:
            continue
        r = RND.random()
        entry = to_dt(8, RND.randint(0, 28))
        if r < 0.15:  # did not come today
            plans[student.username] = []
        elif r < 0.30:  # entered, left after pair 3
            out = to_dt(12, 50 + RND.randint(0, 9))
            plans[student.username] = [(entry, IN), (out, OUT)]
        elif r < 0.45:  # lunch break: out and back in
            plans[student.username] = [
                (entry, IN),
                (to_dt(12, 52 + RND.randint(0, 6)), OUT),
                (to_dt(13, 20 + RND.randint(0, 8)), IN),
            ]
        else:  # entered in the morning, still inside
            plans[student.username] = [(entry, IN)]

    for username, logs in plans.items():
        user = users[username]
        for ts, direction in logs:
            db.add(m.TurnstileLog(user_id=user.id, timestamp=ts, direction=direction))
    db.flush()
    return plans


def _attendance_status_today(logs, pair_start_dt):
    """Derive today's attendance from turnstile presence at pair start."""
    inside = False
    last_entry = None
    for ts, direction in logs:
        if ts > pair_start_dt + timedelta(minutes=15):
            break
        inside = direction == IN
        if inside:
            last_entry = ts
    if not inside:
        return m.AttendanceStatus.absent
    if last_entry and last_entry > pair_start_dt + timedelta(minutes=5):
        return m.AttendanceStatus.late
    return m.AttendanceStatus.present


def create_sessions_and_attendance(db, users, groups, schedule_rows, log_plans, today):
    students_by_group: dict[int, list[m.User]] = {}
    for u in users.values():
        if u.role == m.UserRole.student:
            students_by_group.setdefault(u.group_id, []).append(u)

    tursunov_id = users["tursunov"].id

    # Past 5 working days (skip Sundays)
    past_days = []
    d = today - timedelta(days=1)
    while len(past_days) < 5:
        if d.weekday() != 6:
            past_days.append(d)
        d -= timedelta(days=1)
    past_days.reverse()

    def random_past_status(student):
        r = RND.random()
        if student.username == "aliyev":
            return m.AttendanceStatus.present
        if student.username == "karimov":  # debtor with weak attendance
            if r < 0.40:
                return m.AttendanceStatus.present
            if r < 0.50:
                return m.AttendanceStatus.late
            return m.AttendanceStatus.absent
        if r < 0.85:
            return m.AttendanceStatus.present
        if r < 0.92:
            return m.AttendanceStatus.late
        return m.AttendanceStatus.absent

    for pd in past_days:
        for row in schedule_rows.values():
            if row.weekday != pd.weekday():
                continue
            start, _end = PAIR_TIMES[row.pair_number]
            if RND.random() < 0.04:
                db.add(m.ClassSession(
                    schedule_id=row.id, date=pd,
                    status=m.ClassSessionStatus.cancelled, teacher_arrived_at=None,
                ))
                continue
            arrived = datetime.combine(pd, start) - timedelta(minutes=RND.randint(3, 14))
            db.add(m.ClassSession(
                schedule_id=row.id, date=pd,
                status=m.ClassSessionStatus.held, teacher_arrived_at=arrived,
            ))
            for student in students_by_group.get(row.group_id, []):
                db.add(m.Attendance(
                    student_id=student.id, schedule_id=row.id, date=pd,
                    status=random_past_status(student),
                    marked_by_teacher_id=row.teacher_id,
                ))

    # Today: all scheduled pairs are pre-seeded so the demo works at any hour.
    for row in schedule_rows.values():
        if row.weekday != today.weekday():
            continue
        start, _end = PAIR_TIMES[row.pair_number]
        if row.teacher_id == tursunov_id:
            # Absent teacher: no attendance, session needs clarification (S10)
            db.add(m.ClassSession(
                schedule_id=row.id, date=today,
                status=m.ClassSessionStatus.needs_clarification, teacher_arrived_at=None,
            ))
            continue
        arrived = datetime.combine(today, start) - timedelta(minutes=RND.randint(2, 10))
        db.add(m.ClassSession(
            schedule_id=row.id, date=today,
            status=m.ClassSessionStatus.held, teacher_arrived_at=arrived,
        ))
        for student in students_by_group.get(row.group_id, []):
            if student.username == "mahmudov" and row.pair_number >= 3:
                # In the building but skipping class (S9 "binoda + belgilanmagan")
                status = m.AttendanceStatus.absent
            else:
                status = _attendance_status_today(
                    log_plans.get(student.username, []),
                    datetime.combine(today, start),
                )
            db.add(m.Attendance(
                student_id=student.id, schedule_id=row.id, date=today,
                status=status, marked_by_teacher_id=row.teacher_id,
            ))
    db.flush()


def create_flow_documents(db, users, today):
    """3 applications/reports + 1 order, in different statuses. Returns dict."""

    def dt(days_ago, h, mm):
        return datetime.combine(today - timedelta(days=days_ago), time(h, mm))

    def add_history(fd, status, days_ago, h, mm, by, comment=None):
        db.add(m.FlowHistory(
            flow_document_id=fd.id, status=status, comment=comment,
            timestamp=dt(days_ago, h, mm), changed_by_id=users[by].id,
        ))

    # 1) Aliyev's approved application (demo hero)
    fd1 = m.FlowDocument(
        doc_type=m.FlowDocumentType.application, template_id="malumotnoma",
        sender_id=users["aliyev"].id, recipient_role=m.UserRole.staff,
        body_text=(
            "Dekanatga talaba Aliyev Jasurdan (AT-24-01 guruhi).\n\n"
            "ARIZA\n\nMenga o'qish joyimdan ma'lumotnoma berishingizni so'rayman. "
            "Ma'lumotnoma harbiy xizmatga chaqiruv bo'limiga taqdim etish uchun kerak."
        ),
        status=m.FlowStatus.approved, created_at=dt(2, 9, 14),
    )
    # 2) Application in "seen" status
    fd2 = m.FlowDocument(
        doc_type=m.FlowDocumentType.application, template_id="qayta_topshirish",
        sender_id=users["abdullayev"].id, recipient_role=m.UserRole.staff,
        body_text=(
            "Dekanatga talaba Abdullayev Timurdan (AT-24-02 guruhi).\n\n"
            "ARIZA\n\n'Matematik tahlil' fanidan oraliq nazoratni kasalligim sababli "
            "(ma'lumotnoma ilova qilinadi) qayta topshirishga ruxsat berishingizni "
            "so'rayman."
        ),
        status=m.FlowStatus.seen, created_at=dt(1, 11, 40),
    )
    # 3) Teacher's report, just sent
    fd3 = m.FlowDocument(
        doc_type=m.FlowDocumentType.report, template_id="semestr_hisobot",
        sender_id=users["umarov"].id, recipient_role=m.UserRole.staff,
        body_text=(
            "Dekanatga katta o'qituvchi Umarov Sherzoddan.\n\n"
            "2025-2026 o'quv yili bahorgi semestri bo'yicha 'Ma'lumotlar bazasi' "
            "fanidan yakuniy hisobot ilova qilinadi: o'zlashtirish 84%, "
            "qayta topshirishga qolganlar 3 nafar."
        ),
        status=m.FlowStatus.sent, created_at=dt(0, 8, 50),
    )
    # 4) Staff order to the absent teacher, in progress
    fd4 = m.FlowDocument(
        doc_type=m.FlowDocumentType.order, template_id="buyruq_topshiriq",
        sender_id=users["rashidova"].id, recipient_user_id=users["tursunov"].id,
        body_text=(
            "O'qituvchi Tursunov Akmalga.\n\n"
            "Rektorning 91-M-son buyrug'iga asosan attestatsiya uchun hujjatlaringizni "
            "(ishchi dastur, sillabus, yuklama hisoboti) dekanatga topshirishingiz "
            "so'raladi."
        ),
        due_date=today + timedelta(days=5),
        status=m.FlowStatus.in_progress, created_at=dt(3, 10, 20),
    )
    db.add_all([fd1, fd2, fd3, fd4])
    db.flush()

    add_history(fd1, m.FlowStatus.sent, 2, 9, 14, "aliyev")
    add_history(fd1, m.FlowStatus.seen, 1, 10, 5, "rashidova")
    add_history(fd1, m.FlowStatus.approved, 1, 15, 30, "rashidova",
                comment="Ma'lumotnoma tayyorlandi. Dekanatdan (204-xona) olib ketishingiz mumkin.")
    add_history(fd2, m.FlowStatus.sent, 1, 11, 40, "abdullayev")
    add_history(fd2, m.FlowStatus.seen, 0, 9, 10, "rashidova")
    add_history(fd3, m.FlowStatus.sent, 0, 8, 50, "umarov")
    add_history(fd4, m.FlowStatus.sent, 3, 10, 20, "rashidova")
    add_history(fd4, m.FlowStatus.seen, 2, 12, 45, "tursunov")
    add_history(fd4, m.FlowStatus.in_progress, 1, 9, 30, "tursunov",
                comment="Hujjatlar tayyorlanmoqda.")
    db.flush()
    return {"approved": fd1, "seen": fd2, "sent": fd3, "order": fd4}


def create_notifications(db, users, groups, flows, risk_row, uploaded_payment, today):
    def notify(username, notif_type, text, link_type=None, link_id=None, is_read=False):
        db.add(m.Notification(
            user_id=users[username].id, notif_type=notif_type, text=text,
            link_type=link_type, link_id=link_id, is_read=is_read,
        ))

    notify("aliyev", "flow_status",
           "Arizangiz tasdiqlandi: o'qish joyidan ma'lumotnoma. Izoh: dekanatdan "
           "(204-xona) olib ketishingiz mumkin.",
           "flow_document", flows["approved"].id)
    notify("abdullayev", "flow_status",
           "Arizangiz dekanat tomonidan ko'rildi: qayta topshirishga ruxsat so'rovi.",
           "flow_document", flows["seen"].id)
    for staff_username in ("rashidova", "yusupov"):
        notify(staff_username, "teacher_absence",
               "Dars xavf ostida: Tursunov Akmal bugun 3-paradagi darsiga "
               "(AT-24-02, Kompyuter tarmoqlari, 103-lab) hali binoga kirmagan.",
               "schedule", risk_row.id)
    notify("rashidova", "flow_incoming",
           "Yangi hisobot keldi: Umarov Sherzod — semestr yakuniy hisoboti.",
           "flow_document", flows["sent"].id)
    if uploaded_payment is not None:
        notify("nazarova", "payment_uploaded",
               "Sharipova Gulnora (AT-24-02) to'lov chekini yukladi — tasdiqlash "
               "kutilmoqda.",
               "payment", uploaded_payment.id)
    notify("karimov", "payment_debt",
           "Kontrakt bo'yicha qarzdorlik mavjud: 12 000 000 so'm. To'lov jadvali "
           "bilan tanishing (ichki tartib nizomi, 5-bo'lim).",
           "contract", None)
    # New assignment announcement for the hero group
    for username, _fn in STUDENT_DEFS["AT-24-01"]:
        notify(username, "new_assignment",
               "Yangi topshiriq: Ma'lumotlar bazasi — Topshiriq 3 (Normalizatsiya). "
               "Muddat tizimda ko'rsatilgan.",
               "assignment", None, is_read=(username != "aliyev"))
    db.flush()


# --- verification -----------------------------------------------------------

def scenario_checks(db, today):
    """DoD: debtor exists, a student is inside, a teacher missed his class."""
    ok = True
    day_start = datetime.combine(today, time(0, 0))
    day_end = day_start + timedelta(days=1)

    def result(label, passed, detail):
        nonlocal ok
        ok = ok and passed
        print(f"  [{'OK' if passed else 'FAIL'}] {label}: {detail}")

    # 1) Debtor student
    karimov = db.query(m.User).filter_by(username="karimov").one()
    contract = db.query(m.Contract).filter_by(student_id=karimov.id).one()
    paid = sum(
        p.amount for p in db.query(m.Payment).filter_by(student_id=karimov.id)
    )
    result(
        "Qarzdor talaba", float(paid) < float(contract.total_amount),
        f"Karimov Diyor - kontrakt {int(contract.total_amount):,} so'm, "
        f"to'langan {int(paid):,} so'm",
    )

    # 2) Student currently in the building
    aliyev = db.query(m.User).filter_by(username="aliyev").one()
    last_log = (
        db.query(m.TurnstileLog)
        .filter(
            m.TurnstileLog.user_id == aliyev.id,
            m.TurnstileLog.timestamp >= day_start,
            m.TurnstileLog.timestamp < day_end,
        )
        .order_by(m.TurnstileLog.timestamp.desc())
        .first()
    )
    inside = last_log is not None and last_log.direction == IN
    result(
        "Binoda turgan talaba", inside,
        "Aliyev Jasur - oxirgi log: "
        + (f"{last_log.timestamp:%H:%M} ({last_log.direction.value})" if last_log else "yo'q"),
    )

    # 3) Teacher with a scheduled class today who never entered
    tursunov = db.query(m.User).filter_by(username="tursunov").one()
    todays_classes = (
        db.query(m.Schedule)
        .filter_by(teacher_id=tursunov.id, weekday=today.weekday())
        .count()
    )
    logs_today = (
        db.query(m.TurnstileLog)
        .filter(
            m.TurnstileLog.user_id == tursunov.id,
            m.TurnstileLog.timestamp >= day_start,
            m.TurnstileLog.timestamp < day_end,
        )
        .count()
    )
    result(
        "Darsga kelmagan o'qituvchi",
        todays_classes > 0 and logs_today == 0,
        f"Tursunov Akmal - bugun jadvalda {todays_classes} ta dars, "
        f"turniket loglari: {logs_today} ta",
    )
    return ok


def print_counts(db):
    print("\nJadvallar bo'yicha yozuvlar soni:")
    for model, name in COUNT_TABLES:
        print(f"  {name:<16} {db.query(model).count():>5}")


def print_demo_logins():
    print(f"\nDemo loginlar (hammasi uchun parol: {DEMO_PASSWORD}):")
    print("  student : aliyev (binoda, qarzsiz), karimov (qarzdor),")
    print("            sodiqova (qisman to'lagan, chiqib ketgan)")
    print("  teacher : umarov (darsda), tursunov (darsga KELMAGAN)")
    print("  tutor   : nazarova (AT guruhlari), qodirova (IQ guruhlari)")
    print("  staff   : rashidova (AT dekanati), yusupov (IQ dekanati)")
    print("  admin   : admin")


def main():
    parser = argparse.ArgumentParser(description="UniAgent demo data generator")
    parser.add_argument(
        "--reset", action="store_true",
        help="clear all tables before seeding (idempotent full rebuild)",
    )
    args = parser.parse_args()

    today = date.today()
    init_db()
    db = SessionLocal()
    try:
        if args.reset:
            reset_db(db)
        elif db.query(m.User).count() > 0:
            print("Bazada ma'lumot bor. To'liq qayta yaratish uchun: "
                  "python -m seed.generate --reset")
            return 0

        print(f"Seed boshlandi: {today} ({today.strftime('%A')})")
        users, groups = create_users_and_groups(db)
        schedule_rows, risk_row = create_schedule(db, users, groups, today.weekday())
        create_assignments(db, users, groups, today)
        create_documents(db)
        uploaded_payment = create_contracts_and_payments(db, users, today)
        log_plans = create_turnstile_logs(db, users, today)
        create_sessions_and_attendance(
            db, users, groups, schedule_rows, log_plans, today
        )
        flows = create_flow_documents(db, users, today)
        create_notifications(
            db, users, groups, flows, risk_row, uploaded_payment, today
        )
        db.commit()

        print_counts(db)
        print("\nSsenariy tekshiruvi:")
        all_ok = scenario_checks(db, today)
        print_demo_logins()
        if not all_ok:
            print("\nXATO: ssenariy tekshiruvi o'tmadi!")
            return 1
        print("\nSeed muvaffaqiyatli yakunlandi.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
