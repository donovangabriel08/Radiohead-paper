from __future__ import annotations
import argparse
import sys

# Paper constants. See module docstring for the derivation.
CHILD_WINDOW_YEARS = 15.0
COHAB_END_AGE_THOM = 18.0
ANDREW_OFFSET_YEARS = 3.0
LIFESPAN_YEARS = 90.0
SHARE_BY_18 = 0.90

CHILDHOOD_HOURS = 13700.0
LIFETIME_HOURS = 15200.0
RHO_CHILD = CHILDHOOD_HOURS / CHILD_WINDOW_YEARS  # hours / year of Andrew's age
RHO_ADULT = (LIFETIME_HOURS - CHILDHOOD_HOURS) / (LIFESPAN_YEARS - COHAB_END_AGE_THOM)

HOURS_PER_YEAR = 365.25 * 24.0
HOURS_PER_MONTH = HOURS_PER_YEAR / 12.0
HOURS_PER_DAY = 24.0


def aggregate_hours(andrew_age: float) -> float:
    """Hours Thom has spent with Andrew by the time Andrew is `andrew_age`."""
    if andrew_age < 0:
        raise ValueError("Andrew's age cannot be negative.")
    thom_age = andrew_age + ANDREW_OFFSET_YEARS
    if thom_age < COHAB_END_AGE_THOM:
        return RHO_CHILD * andrew_age
    return CHILDHOOD_HOURS + RHO_ADULT * (thom_age - COHAB_END_AGE_THOM)


def andrew_age_from_hours(listening_hours: float) -> float:
    """Invert the piecewise aggregate-time function.

    Returns Andrew's age in years at the moment cumulative sibling time
    equals `listening_hours`. Raises ValueError if the input is outside
    the model's domain (negative, or past the assumed 90-year lifetime).
    """
    if listening_hours < 0:
        raise ValueError("Listening time cannot be negative.")
    if listening_hours == 0:
        return 0.0
    if listening_hours <= CHILDHOOD_HOURS:
        return listening_hours / RHO_CHILD
    if listening_hours > LIFETIME_HOURS:
        raise ValueError(
            f"{listening_hours:,.1f} hours is past the model's lifetime total "
            f"of {LIFETIME_HOURS:,.0f} hours (Thom age {LIFESPAN_YEARS:.0f})."
        )
    adult_hours = listening_hours - CHILDHOOD_HOURS
    thom_age = COHAB_END_AGE_THOM + adult_hours / RHO_ADULT
    return thom_age - ANDREW_OFFSET_YEARS


def format_age(years: float) -> str:
    """Render a fractional year as years, months, and days."""
    if years < 0:
        raise ValueError("Age cannot be negative.")
    total_days = years * 365.25
    whole_years = int(years)
    rem_years = years - whole_years
    months = int(rem_years * 12)
    rem_months = rem_years * 12 - months
    days = int(round(rem_months * (365.25 / 12)))
    if days >= 30:
        months += 1
        days = 0
    if months >= 12:
        whole_years += 1
        months = 0

    parts: list[str] = []
    if whole_years:
        parts.append(f"{whole_years} year{'s' if whole_years != 1 else ''}")
    if months:
        parts.append(f"{months} month{'s' if months != 1 else ''}")
    if days or not parts:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    pretty = ", ".join(parts)
    return f"{pretty} ({years:.3f} years, about {total_days:,.0f} days)"


def parse_listening_time(raw: str) -> float:
    """Accept '670', '670h', '40113m', '40113 min', '40,113 minutes'."""
    text = raw.strip().lower().replace(",", "")
    if not text:
        raise ValueError("Enter a listening time.")
    unit = "hours"
    for suffix, name in (
        ("minutes", "minutes"),
        ("minute", "minutes"),
        ("mins", "minutes"),
        ("min", "minutes"),
        ("hours", "hours"),
        ("hour", "hours"),
        ("hrs", "hours"),
        ("hr", "hours"),
        ("m", "minutes"),
        ("h", "hours"),
    ):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
            unit = name
            break
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError(
            "Could not parse that. Try `670`, `670h`, or `40113m`."
        ) from exc
    if unit == "minutes":
        return value / 60.0
    return value


def report(listening_hours: float) -> str:
    """Build the human-readable comparison."""
    lines = [
        f"Radiohead listening time: {listening_hours:,.2f} hours "
        f"({listening_hours * 60:,.0f} minutes).",
    ]
    try:
        age = andrew_age_from_hours(listening_hours)
    except ValueError as exc:
        lines.append(str(exc))
        lines.append(
            "Under this model, lifetime time with Andrew tops out near "
            f"{LIFETIME_HOURS:,.0f} hours. You are past the elitist event horizon."
        )
        return "\n".join(lines)

    thom_age = age + ANDREW_OFFSET_YEARS
    phase = "co-habitation" if thom_age < COHAB_END_AGE_THOM else "adult, post-move-out"
    lines.append(f"Equivalent Andrew age: {format_age(age)}.")
    lines.append(
        f"That is Thom at about {thom_age:.3f} years old, in the {phase} phase "
        f"of the model ({aggregate_hours(age):,.1f} hours together)."
    )
    if listening_hours <= CHILDHOOD_HOURS:
        lines.append(
            "Childhood rate used here: "
            f"{RHO_CHILD:,.1f} hours/year, from {CHILDHOOD_HOURS:,.0f} hours "
            f"over {CHILD_WINDOW_YEARS:.0f} years at ~2.5 hours/day."
        )
    else:
        lines.append(
            "This listener has cleared the entire childhood total "
            f"({CHILDHOOD_HOURS:,.0f} hours). Remaining time is accrued at "
            f"{RHO_ADULT:.1f} hours/year."
        )
    lines.append(
        "Paper benchmark: 40,113 minutes (~670 hours) maps to Andrew at "
        f"{format_age(andrew_age_from_hours(670))}."
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert Radiohead listening time into an equivalent Andrew Yorke age, "
            "using the model from Donovan Gabriel's October 2026 note."
        )
    )
    parser.add_argument(
        "time",
        nargs="?",
        help="Listening time. Bare numbers are hours. Suffix m/min or h/hr to force a unit.",
    )
    parser.add_argument(
        "--minutes",
        action="store_true",
        help="Treat a bare number as minutes instead of hours.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.time is None:
        try:
            raw = input(
                "Total Radiohead listening time "
                "(hours, or suffix m for minutes; e.g. 670 or 40113m): "
            )
        except EOFError:
            print("No listening time provided.", file=sys.stderr)
            return 1
    else:
        raw = args.time
        if args.minutes and not raw[-1].isalpha():
            raw = f"{raw}m"
    try:
        hours = parse_listening_time(raw)
        print(report(hours))
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
