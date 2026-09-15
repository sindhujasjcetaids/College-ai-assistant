"""
tools.py
--------
Simple deterministic "tools" the assistant can call before/instead of
pure document retrieval, for tasks that need computation or structured
lookups rather than free-text answers (classic tool-use pattern in an
agentic RAG system).

Each tool exposes:
    - a `matches(query)` function that returns True if this tool should run
    - a `run(query)` function that returns a plain-text result

The orchestrator (chat.py) tries each tool in order; if one matches,
its result is used alongside (or instead of) retrieval.
"""

import re
from datetime import datetime


# ---------------------------------------------------------------------
# Tool 1: GPA / Grade calculator
# ---------------------------------------------------------------------
GRADE_POINTS = {"O": 10, "A+": 9, "A": 8, "B+": 7, "B": 6, "C": 5, "F": 0}


def gpa_calculator_matches(query: str) -> bool:
    q = query.lower()
    return ("gpa" in q or "cgpa" in q) and (
        "calculate" in q or "compute" in q or bool(re.search(r"\d\s*credit", q))
        or bool(re.search(r"[ob]\+?\s*,|\bgrades?\b.*\d", q))
    )


def gpa_calculator_run(query: str) -> str:
    """Parses patterns like: 'A(4), B+(3), O(3)' or 'grade A 4 credits, grade B+ 3 credits'."""
    pairs = re.findall(r"([OABC]\+?)\s*[\(:,]?\s*(\d+(?:\.\d+)?)\s*(?:credits?)?", query, re.IGNORECASE)
    if not pairs:
        return (
            "To calculate your GPA, tell me your grades and credits like this: "
            "'Calculate my GPA: A+ 4 credits, A 3 credits, B+ 4 credits, O 2 credits'."
        )

    total_points = 0.0
    total_credits = 0.0
    breakdown = []
    for grade, credit in pairs:
        grade_norm = grade.upper()
        credit_val = float(credit)
        points = GRADE_POINTS.get(grade_norm)
        if points is None:
            continue
        total_points += points * credit_val
        total_credits += credit_val
        breakdown.append(f"  - Grade {grade_norm} × {credit_val} credits = {points * credit_val:.1f} points")

    if total_credits == 0:
        return "I couldn't parse valid grade/credit pairs. Try: 'A+ 4 credits, B 3 credits'."

    gpa = total_points / total_credits
    result = "Here's your GPA calculation:\n" + "\n".join(breakdown)
    result += f"\n\nTotal Grade Points: {total_points:.1f}\nTotal Credits: {total_credits:.1f}"
    result += f"\n\n**Calculated GPA: {gpa:.2f} / 10**"
    if gpa < 5.0:
        result += "\n\nNote: As per Section 2 of the Regulations Handbook, a CGPA below 5.0 may lead to academic probation."
    return result


# ---------------------------------------------------------------------
# Tool 2: Attendance eligibility calculator
# ---------------------------------------------------------------------
def attendance_calculator_matches(query: str) -> bool:
    q = query.lower()
    has_keyword = "attendance" in q or "attended" in q
    has_numbers = bool(re.search(r"\d+\s*(%|percent|classes|out of)", q)) or bool(re.search(r"\d+\s*(?:out of|/)\s*\d+", q))
    return has_keyword and has_numbers


def attendance_calculator_run(query: str) -> str:
    q = query.lower()

    # Pattern: "attended 60 out of 80 classes"
    m = re.search(r"(\d+)\s*(?:out of|/)\s*(\d+)", q)
    if m:
        attended, total = int(m.group(1)), int(m.group(2))
        if total == 0:
            return "Total number of classes can't be zero."
        pct = (attended / total) * 100
        return _attendance_verdict(pct, detail=f"{attended} out of {total} classes ({pct:.1f}%)")

    # Pattern: "75%" or "75 percent"
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", q)
    if m:
        pct = float(m.group(1))
        return _attendance_verdict(pct, detail=f"{pct:.1f}% attendance")

    return "Please share your attendance like '60 out of 80 classes' or '78%' and I'll check your eligibility."


def _attendance_verdict(pct: float, detail: str) -> str:
    if pct >= 75:
        verdict = "✅ You meet the minimum 75% attendance requirement and are eligible to sit for exams."
    elif pct >= 65:
        verdict = (
            "⚠️ You're between 65-75%. Per Section 1 of the Regulations, you may still be eligible "
            "for the exam if your Head of Department approves condonation on medical/genuine grounds "
            "(documentation must be submitted within 7 days)."
        )
    else:
        verdict = (
            "❌ Below 65% attendance. Per Section 1 of the Regulations, you will not be permitted to "
            "sit for the semester exam and will need to repeat the course."
        )
    return f"Attendance check: {detail}\n\n{verdict}"


# ---------------------------------------------------------------------
# Tool 3: "Today's date / days until" utility (useful for deadlines)
# ---------------------------------------------------------------------
def date_tool_matches(query: str) -> bool:
    q = query.lower()
    return "today" in q and ("date" in q or "day" in q)


def date_tool_run(query: str) -> str:
    now = datetime.now()
    return f"Today's date is {now.strftime('%A, %B %d, %Y')}."


# ---------------------------------------------------------------------
# Tool registry - order matters (first match wins)
# ---------------------------------------------------------------------
TOOLS = [
    {"name": "gpa_calculator", "matches": gpa_calculator_matches, "run": gpa_calculator_run},
    {"name": "attendance_calculator", "matches": attendance_calculator_matches, "run": attendance_calculator_run},
    {"name": "date_tool", "matches": date_tool_matches, "run": date_tool_run},
]


def try_tools(query: str):
    """Return (tool_name, result_text) if a tool matched, else (None, None)."""
    for tool in TOOLS:
        try:
            if tool["matches"](query):
                return tool["name"], tool["run"](query)
        except Exception:
            continue
    return None, None
