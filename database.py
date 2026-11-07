import sqlite3
from pathlib import Path
from datetime import datetime

DATABASE_PATH = (
    Path(__file__).resolve().parent
    / "database"
    / "classroom_database.db"
)

def get_connection():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database file not found: {DATABASE_PATH}")

    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def validate_date(date_value):
    try:
        datetime.strptime(date_value, "%Y-%m-%d")
        return True
    except (TypeError, ValueError):
        return False


def validate_time_range(start_time, end_time):
    try:
        start = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")
        return start < end
    except (TypeError, ValueError):
        return False


def ensure_makeup_columns():
    """Add the makeup-class columns to an existing timetable, if needed."""
    connection = get_connection()

    try:
        columns = [
            row["name"]
            for row in connection.execute("PRAGMA table_info(timetable)").fetchall()
        ]

        if "is_makeup" not in columns:
            connection.execute(
                "ALTER TABLE timetable ADD COLUMN is_makeup INTEGER NOT NULL DEFAULT 0"
            )

        if "specific_date" not in columns:
            connection.execute(
                "ALTER TABLE timetable ADD COLUMN specific_date TEXT"
            )

        connection.commit()
    finally:
        connection.close()


def get_teachers():
    connection = get_connection()

    try:
        rows = connection.execute(
            "SELECT teacher_id, teacher_name FROM teachers ORDER BY teacher_name"
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_classrooms():
    connection = get_connection()

    try:
        rows = connection.execute(
            "SELECT classroom_id FROM classrooms ORDER BY classroom_id"
        ).fetchall()

        return [row["classroom_id"] for row in rows]
    finally:
        connection.close()


def is_teacher_on_leave(teacher_id, date_value):
    connection = get_connection()

    try:
        leave = connection.execute(
            """
            SELECT leave_id
            FROM leave_records
            WHERE teacher_id = ?
              AND start_date <= ?
              AND end_date >= ?
            LIMIT 1
            """,
            (teacher_id, date_value, date_value)
        ).fetchone()

        return leave is not None
    finally:
        connection.close()


def get_teacher_schedule(teacher_id, date_value):
    """Return regular classes for the weekday and makeup classes for this exact date."""
    if not validate_date(date_value):
        raise ValueError("Date must be in YYYY-MM-DD format.")

    ensure_makeup_columns()

    day_name = datetime.strptime(date_value, "%Y-%m-%d").strftime("%A")
    teacher_on_leave = is_teacher_on_leave(teacher_id, date_value)

    connection = get_connection()

    try:
        regular_rows = connection.execute(
            """
            SELECT classroom_id, start_time, end_time
            FROM timetable
            WHERE teacher_id = ?
              AND day_of_week = ?
              AND COALESCE(is_makeup, 0) = 0
              AND specific_date IS NULL
            ORDER BY start_time
            """,
            (teacher_id, day_name)
        ).fetchall()

        makeup_rows = connection.execute(
            """
            SELECT classroom_id, start_time, end_time
            FROM timetable
            WHERE teacher_id = ?
              AND is_makeup = 1
              AND specific_date = ?
            ORDER BY start_time
            """,
            (teacher_id, date_value)
        ).fetchall()

        schedule = []

        for row in regular_rows:
            schedule.append({
                "classroom_id": row["classroom_id"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "status": "FREE - TEACHER ON LEAVE" if teacher_on_leave else "OCCUPIED",
                "class_type": "Regular"
            })

        for row in makeup_rows:
            schedule.append({
                "classroom_id": row["classroom_id"],
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "status": "OCCUPIED",
                "class_type": "Makeup"
            })

        schedule.sort(key=lambda item: item["start_time"])
        return schedule
    finally:
        connection.close()


def get_available_classrooms(date_value, start_time, end_time):
    """Return rooms not occupied by a regular class or a date-specific makeup class."""
    if not validate_date(date_value):
        raise ValueError("Date must be in YYYY-MM-DD format.")

    if not validate_time_range(start_time, end_time):
        raise ValueError("Please provide a valid start and end time.")

    ensure_makeup_columns()

    day_name = datetime.strptime(date_value, "%Y-%m-%d").strftime("%A")
    connection = get_connection()

    try:
        classrooms = connection.execute(
            "SELECT classroom_id FROM classrooms ORDER BY classroom_id"
        ).fetchall()

        available_rooms = []

        for room in classrooms:
            classroom_id = room["classroom_id"]

            regular_classes = connection.execute(
                """
                SELECT t.teacher_id
                FROM timetable AS t
                WHERE t.classroom_id = ?
                  AND t.day_of_week = ?
                  AND COALESCE(t.is_makeup, 0) = 0
                  AND t.specific_date IS NULL
                  AND t.start_time < ?
                  AND t.end_time > ?
                """,
                (classroom_id, day_name, end_time, start_time)
            ).fetchall()

            room_is_occupied = False

            for class_record in regular_classes:
                leave = connection.execute(
                    """
                    SELECT leave_id
                    FROM leave_records
                    WHERE teacher_id = ?
                      AND start_date <= ?
                      AND end_date >= ?
                    LIMIT 1
                    """,
                    (class_record["teacher_id"], date_value, date_value)
                ).fetchone()

                if leave is None:
                    room_is_occupied = True
                    break

            if room_is_occupied:
                continue

            makeup_class = connection.execute(
                """
                SELECT schedule_id
                FROM timetable
                WHERE classroom_id = ?
                  AND is_makeup = 1
                  AND specific_date = ?
                  AND start_time < ?
                  AND end_time > ?
                LIMIT 1
                """,
                (classroom_id, date_value, end_time, start_time)
            ).fetchone()

            if makeup_class is not None:
                continue

            available_rooms.append(classroom_id)

        return available_rooms
    finally:
        connection.close()


def book_makeup_class(teacher_id, classroom_id, date_value, start_time, end_time):
    """
    Book one makeup class on one exact date.
    Checks teacher leave, teacher timetable clashes, and room clashes again at booking time.
    Returns the new timetable schedule_id.
    """
    if not validate_date(date_value):
        raise ValueError("Date must be in YYYY-MM-DD format.")

    if not validate_time_range(start_time, end_time):
        raise ValueError("Please provide a valid start and end time.")

    ensure_makeup_columns()

    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        teacher = connection.execute(
            "SELECT teacher_id FROM teachers WHERE teacher_id = ?",
            (teacher_id,)
        ).fetchone()

        if teacher is None:
            raise ValueError("The selected teacher was not found.")

        room = connection.execute(
            "SELECT classroom_id FROM classrooms WHERE classroom_id = ?",
            (classroom_id,)
        ).fetchone()

        if room is None:
            raise ValueError("The selected classroom was not found.")

        leave = connection.execute(
            """
            SELECT leave_id
            FROM leave_records
            WHERE teacher_id = ?
              AND start_date <= ?
              AND end_date >= ?
            LIMIT 1
            """,
            (teacher_id, date_value, date_value)
        ).fetchone()

        if leave is not None:
            raise ValueError("This teacher is on leave on the selected date.")

        day_name = datetime.strptime(date_value, "%Y-%m-%d").strftime("%A")

        # Check the teacher's regular timetable.
        teacher_regular_class = connection.execute(
            """
            SELECT schedule_id
            FROM timetable
            WHERE teacher_id = ?
              AND day_of_week = ?
              AND COALESCE(is_makeup, 0) = 0
              AND specific_date IS NULL
              AND start_time < ?
              AND end_time > ?
            LIMIT 1
            """,
            (teacher_id, day_name, end_time, start_time)
        ).fetchone()

        if teacher_regular_class is not None:
            raise ValueError("This teacher already has a regular class at that time.")

        # Check the teacher's other makeup classes on this exact date.
        teacher_makeup_class = connection.execute(
            """
            SELECT schedule_id
            FROM timetable
            WHERE teacher_id = ?
              AND is_makeup = 1
              AND specific_date = ?
              AND start_time < ?
              AND end_time > ?
            LIMIT 1
            """,
            (teacher_id, date_value, end_time, start_time)
        ).fetchone()

        if teacher_makeup_class is not None:
            raise ValueError("This teacher already has another makeup class at that time.")

        # Check whether the selected room has a regular class.
        room_regular_classes = connection.execute(
            """
            SELECT teacher_id
            FROM timetable
            WHERE classroom_id = ?
              AND day_of_week = ?
              AND COALESCE(is_makeup, 0) = 0
              AND specific_date IS NULL
              AND start_time < ?
              AND end_time > ?
            """,
            (classroom_id, day_name, end_time, start_time)
        ).fetchall()

        for class_record in room_regular_classes:
            teacher_leave = connection.execute(
                """
                SELECT leave_id
                FROM leave_records
                WHERE teacher_id = ?
                  AND start_date <= ?
                  AND end_date >= ?
                LIMIT 1
                """,
                (class_record["teacher_id"], date_value, date_value)
            ).fetchone()

            if teacher_leave is None:
                raise ValueError("This classroom is no longer available at that time.")

        # Check other makeup classes in this room.
        room_makeup_class = connection.execute(
            """
            SELECT schedule_id
            FROM timetable
            WHERE classroom_id = ?
              AND is_makeup = 1
              AND specific_date = ?
              AND start_time < ?
              AND end_time > ?
            LIMIT 1
            """,
            (classroom_id, date_value, end_time, start_time)
        ).fetchone()

        if room_makeup_class is not None:
            raise ValueError("This classroom has just been booked by someone else.")

        cursor = connection.execute(
            """
            INSERT INTO timetable
            (
                teacher_id,
                classroom_id,
                day_of_week,
                start_time,
                end_time,
                is_makeup,
                specific_date
            )
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (
                teacher_id,
                classroom_id,
                day_name,
                start_time,
                end_time,
                date_value
            )
        )

        connection.commit()
        return cursor.lastrowid

    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def add_teacher_leave(teacher_id, start_date, end_date):
    if not validate_date(start_date) or not validate_date(end_date):
        raise ValueError("Leave dates must be in YYYY-MM-DD format.")

    if start_date > end_date:
        raise ValueError("The leave end date cannot be before the start date.")

    connection = get_connection()

    try:
        teacher = connection.execute(
            "SELECT teacher_id FROM teachers WHERE teacher_id = ?",
            (teacher_id,)
        ).fetchone()

        if teacher is None:
            raise ValueError("Teacher not found.")

        cursor = connection.execute(
            """
            INSERT INTO leave_records (teacher_id, start_date, end_date)
            VALUES (?, ?, ?)
            """,
            (teacher_id, start_date, end_date)
        )

        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def cancel_teacher_leave(leave_id):
    connection = get_connection()

    try:
        cursor = connection.execute(
            "DELETE FROM leave_records WHERE leave_id = ?",
            (leave_id,)
        )

        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def get_leave_records():
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT
                leave_records.leave_id,
                leave_records.teacher_id,
                teachers.teacher_name,
                leave_records.start_date,
                leave_records.end_date
            FROM leave_records
            JOIN teachers
                ON leave_records.teacher_id = teachers.teacher_id
            ORDER BY leave_records.leave_id
            """
        ).fetchall()

        return [dict(row) for row in rows]
    finally:
        connection.close()


# Add the two makeup-class columns automatically when this module is imported.
ensure_makeup_columns()
