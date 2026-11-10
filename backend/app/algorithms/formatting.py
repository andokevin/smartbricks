"""Mise en forme des nombres et des dates pour les messages en français."""

from datetime import date


def format_ar(amount: int | float) -> str:
    """1234567 → « 1 234 567 Ar » (séparateur de milliers : espace)."""
    return f"{int(round(amount)):,}".replace(",", " ") + " Ar"


MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
          "novembre", "décembre"]


def format_date_fr(value: date | str | None) -> str:
    """date(2027, 1, 8) ou « 2027-01-08 » → « 8 janvier 2027 »."""
    if value is None:
        return "?"
    d = date.fromisoformat(value) if isinstance(value, str) else value
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def format_pct(ratio: float) -> str:
    """0.1 → « 10 % »."""
    return f"{round(ratio * 100):d} %"
