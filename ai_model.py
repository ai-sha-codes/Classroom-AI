
import requests
import json
import re
from datetime import datetime, date, timedelta

from database import (
    get_teachers,
    get_teacher_schedule,
    get_available_classrooms,
    add_teacher_leave,
    cancel_teacher_leave,
    get_leave_records
)


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2"


def resolve_date_expression(date_expression):

    if not date_expression:
        return None

    date_expression = date_expression.strip().lower()
    today = date.today()

    if date_expression == "today":
        return today.strftime("%Y-%m-%d")

    if date_expression == "tomorrow":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    if date_expression == "yesterday":
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")

    weekday_names = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }

    for weekday_name, weekday_number in weekday_names.items():

        if date_expression in [weekday_name, "next " + weekday_name]:

            days_ahead = (weekday_number - today.weekday()) % 7

            if date_expression.startswith("next ") or days_ahead == 0:
                if days_ahead == 0:
                    days_ahead = 7

            result_date = today + timedelta(days=days_ahead)

            return result_date.strftime("%Y-%m-%d")

    try:
        return date.fromisoformat(date_expression).strftime("%Y-%m-%d")
    except ValueError:
        return None


def get_date_from_response(ai_result, expression_key, fallback_key=None):

    date_expression = ai_result.get(expression_key)

    if not date_expression and fallback_key:
        date_expression = ai_result.get(fallback_key)

    return resolve_date_expression(str(date_expression)) if date_expression else None


def understand_request(user_message):

    current_date = date.today().strftime("%Y-%m-%d")
    current_day = date.today().strftime("%A")

    prompt = f"""
You are an AI assistant for a university classroom management system.

Today's date is {current_date}.
Today's day is {current_day}.

Understand the user's request and return ONLY a valid JSON object.

AVAILABLE OPERATIONS:

1. add_leave
2. check_teacher_schedule
3. check_classroom_availability
4. cancel_leave
5. unknown

DATE RULES:

- If the user says today, return the expression "today".
- If the user says tomorrow, return the expression "tomorrow".
- If the user says yesterday, return the expression "yesterday".
- If the user mentions a weekday, return its name or "next weekday".
- For specific dates, return YYYY-MM-DD.
- Never invent missing dates.

TIME RULES:

- University working hours are 08:00 to 17:30.
- Lectures last one hour.
- At 9 AM means 09:00 to 10:00.
- At 2 PM means 14:00 to 15:00.
- If a time is missing, return unknown for classroom availability.
- For a time range, use the exact start and end times.

JSON FORMATS:

For adding leave:
{{
    "operation": "add_leave",
    "teacher_name": "teacher name",
    "start_date_expression": "tomorrow",
    "end_date_expression": "tomorrow"
}}

For checking teacher schedule:
{{
    "operation": "check_teacher_schedule",
    "teacher_name": "teacher name",
    "date_expression": "tomorrow"
}}

For classroom availability:
{{
    "operation": "check_classroom_availability",
    "date_expression": "tomorrow",
    "start_time": "09:00",
    "end_time": "10:00"
}}

For cancelling leave:
{{
    "operation": "cancel_leave",
    "leave_id": 2
}}

For unclear requests:
{{
    "operation": "unknown"
}}

For teacher-related requests, extract the teacher's full name if provided.
Do not invent missing information.
Do not add explanations outside JSON.

User request: {user_message}
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0
            }
        },
        timeout=120
    )

    response.raise_for_status()

    ai_response = response.json()["message"]["content"]

    return json.loads(ai_response)


def find_teacher(teacher_name):

    if not teacher_name:
        return None

    teachers = get_teachers()

    search_value = teacher_name.strip().casefold()

    for teacher in teachers:

        if teacher["teacher_id"].casefold() == search_value:
            return teacher

        if teacher["teacher_name"].strip().casefold() == search_value:
            return teacher

    return None


def ask_confirmation():

    answer = input("\nDo you want to continue? (yes/no): ")

    return answer.strip().lower() in ["yes", "y"]


def handle_add_leave(ai_result):

    teacher_name = ai_result.get("teacher_name")

    teacher = find_teacher(teacher_name)

    if teacher is None:
        print("\nTeacher not found.")
        print("Available teachers:")

        for item in get_teachers():
            print(item["teacher_id"], "-", item["teacher_name"])

        return

    start_date = get_date_from_response(
        ai_result,
        "start_date_expression",
        "start_date"
    )

    end_date = get_date_from_response(
        ai_result,
        "end_date_expression",
        "end_date"
    )

    if not start_date or not end_date:
        print("\nI could not understand the leave dates.")
        return

    if start_date > end_date:
        print("\nThe leave end date cannot be before the start date.")
        return

    print("\n========== LEAVE DETAILS ==========")
    print("Teacher:", teacher["teacher_name"])
    print("Teacher ID:", teacher["teacher_id"])
    print("Start date:", start_date)
    print("End date:", end_date)

    if not ask_confirmation():
        print("\nLeave request cancelled.")
        return

    leave_id = add_teacher_leave(
        teacher["teacher_id"],
        start_date,
        end_date
    )

    print("\nLeave successfully added.")
    print("Leave ID:", leave_id)


def handle_teacher_schedule(ai_result):

    teacher_name = ai_result.get("teacher_name")

    if not teacher_name:
        teacher_name = ai_result.get("teacher_id")

    teacher = find_teacher(teacher_name)

    if teacher is None:
        print("\nTeacher not found.")
        return

    selected_date = get_date_from_response(
        ai_result,
        "date_expression",
        "date"
    )

    if not selected_date:
        print("\nI could not understand the date.")
        return

    print("\n========== TEACHER SCHEDULE ==========")
    print("Teacher:", teacher["teacher_name"])
    print("Date:", selected_date)

    schedule = get_teacher_schedule(
        teacher["teacher_id"],
        selected_date
    )

    if not schedule:
        print("\nNo classes scheduled for this teacher on this date.")
        return

    for item in schedule:
        print("\nDay:", item["day_of_week"])
        print("Time:", item["start_time"], "-", item["end_time"])
        print("Classroom:", item["classroom_id"])
        print("Status:", item["status"])


def handle_classroom_availability(ai_result):

    selected_date = get_date_from_response(
        ai_result,
        "date_expression",
        "date"
    )

    start_time = ai_result.get("start_time")
    end_time = ai_result.get("end_time")

    if not selected_date or not start_time or not end_time:
        print("\nI could not understand the date or time.")
        return

    try:
        available_classrooms = get_available_classrooms(
            selected_date,
            start_time,
            end_time
        )

    except ValueError as error:
        print("\nInvalid request:", error)
        return

    print("\n========== CLASSROOM AVAILABILITY ==========")
    print("Date:", selected_date)
    print("Time:", start_time, "-", end_time)

    if not available_classrooms:
        print("\nNo classrooms are available.")
        return

    print("\nAvailable classrooms:")

    for classroom in available_classrooms:
        print("-", classroom)

    print("\nTotal available:", len(available_classrooms))


def handle_cancel_leave(ai_result):

    leave_id = ai_result.get("leave_id")

    if not isinstance(leave_id, int) or isinstance(leave_id, bool):
        print("\nInvalid leave ID.")
        return

    leave_records = get_leave_records()

    selected_record = None

    for record in leave_records:

        if record["leave_id"] == leave_id:
            selected_record = record
            break

    if selected_record is None:
        print("\nLeave record not found.")
        return

    print("\n========== CANCEL LEAVE ==========")
    print("Leave ID:", selected_record["leave_id"])
    print("Teacher:", selected_record["teacher_name"])
    print("Start date:", selected_record["start_date"])
    print("End date:", selected_record["end_date"])

    if not ask_confirmation():
        print("\nCancellation aborted.")
        return

    cancelled = cancel_teacher_leave(leave_id)

    if cancelled:
        print("\nLeave successfully cancelled.")
    else:
        print("\nCould not cancel the leave record.")



def apply_user_date_rules(ai_result, user_message):

    message = user_message.lower()
    operation = ai_result.get("operation")

    is_date_range = bool(re.search(r"\bfrom\b.*\bto\b", message))

    if is_date_range:
        return ai_result

    relative_dates = ["today", "tomorrow", "yesterday"]

    for relative_date in relative_dates:

        if re.search(r"\b" + relative_date + r"\b", message):

            if operation == "add_leave":
                ai_result["start_date_expression"] = relative_date
                ai_result["end_date_expression"] = relative_date

            elif operation in [
                "check_teacher_schedule",
                "check_classroom_availability"
            ]:
                ai_result["date_expression"] = relative_date

            return ai_result

    weekday_names = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday"
    ]

    for weekday in weekday_names:

        if re.search(r"\bnext " + weekday + r"\b", message):
            expression = "next " + weekday

        elif re.search(r"\bon " + weekday + r"\b", message):
            expression = weekday

        else:
            continue

        if operation == "add_leave":
            ai_result["start_date_expression"] = expression
            ai_result["end_date_expression"] = expression

        elif operation in [
            "check_teacher_schedule",
            "check_classroom_availability"
        ]:
            ai_result["date_expression"] = expression

        return ai_result

    return ai_result



def apply_user_time_rules(ai_result, user_message):

    if ai_result.get("operation") != "check_classroom_availability":
        return ai_result

    time_match = re.search(
        r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
        user_message.lower()
    )

    if time_match is None:
        return ai_result

    hour = int(time_match.group(1))
    minute = int(time_match.group(2) or 0)
    period = time_match.group(3)

    if hour < 1 or hour > 12 or minute > 59:
        return ai_result

    if period == "am" and hour == 12:
        hour = 0
    elif period == "pm" and hour != 12:
        hour += 12

    start_time = datetime.strptime(
        f"{hour:02d}:{minute:02d}",
        "%H:%M"
    )

    end_time = start_time + timedelta(hours=1)

    ai_result["start_time"] = start_time.strftime("%H:%M")
    ai_result["end_time"] = end_time.strftime("%H:%M")
    ai_result = apply_user_time_rules(ai_result, user_message)
    return ai_result


def process_request(user_message):

    try:
        ai_result = understand_request(user_message)
        ai_result = apply_user_date_rules(ai_result, user_message)

    except requests.exceptions.RequestException as error:
        print("\nCould not connect to Ollama:", error)
        return

    except (json.JSONDecodeError, KeyError, TypeError):
        print("\nThe AI returned an invalid response. Please try again.")
        return

    operation = ai_result.get("operation")

    print("\n========== AI UNDERSTANDING ==========")
    print(json.dumps(ai_result, indent=4))

    if operation == "add_leave":
        handle_add_leave(ai_result)

    elif operation == "check_teacher_schedule":
        handle_teacher_schedule(ai_result)

    elif operation == "check_classroom_availability":
        handle_classroom_availability(ai_result)

    elif operation == "cancel_leave":
        handle_cancel_leave(ai_result)

    else:
        print("\nSorry, I could not understand your request.")


if __name__ == "__main__":

    print("======================================")
    print(" UNIVERSITY CLASSROOM AI ASSISTANT")
    print("======================================")

    while True:

        user_message = input("\nEnter your request (or type exit): ")

        if user_message.strip().lower() == "exit":
            print("\nGoodbye!")
            break

        if not user_message.strip():
            print("\nPlease enter a request.")
            continue

        process_request(user_message)
