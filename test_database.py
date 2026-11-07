from database import (
    get_teachers,
    get_classrooms,
    get_teacher_schedule,
    get_available_classrooms,
    add_teacher_leave,
    cancel_teacher_leave,
    get_leave_records
)


print("\n========== TEACHERS ==========")

teachers = get_teachers()

for teacher in teachers:
    print(teacher)


print("\n========== CLASSROOMS ==========")

classrooms = get_classrooms()

for classroom in classrooms:
    print(classroom)


print("\n========== TEACHER SCHEDULE ==========")

schedule = get_teacher_schedule(
    "CS001",
    "2026-11-02"
)

for lecture in schedule:
    print(lecture)


print("\n========== AVAILABLE CLASSROOMS ==========")

available_rooms = get_available_classrooms(
    "2026-11-02",
    "08:00",
    "09:00"
)

print("Available classrooms:", available_rooms)
print("Total available:", len(available_rooms))


print("\n========== LUNCH BREAK ==========")

available_rooms = get_available_classrooms(
    "2026-11-02",
    "13:00",
    "13:30"
)

print("Available classrooms:", len(available_rooms))


print("\n========== ADD TEMPORARY LEAVE ==========")

leave_id = add_teacher_leave(
    "CS002",
    "2026-11-03",
    "2026-11-03"
)

print("Leave added. ID:", leave_id)


print("\n========== ALL LEAVE RECORDS ==========")

for leave in get_leave_records():
    print(leave)


print("\n========== CANCEL TEMPORARY LEAVE ==========")

cancelled = cancel_teacher_leave(leave_id)

print("Leave cancelled:", cancelled)


print("\n========== FINAL LEAVE RECORDS ==========")

for leave in get_leave_records():
    print(leave)
