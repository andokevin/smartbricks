"""Mise en forme des nombres pour les messages en français."""


def format_ar(amount: int | float) -> str:
    """1234567 → « 1 234 567 Ar » (séparateur de milliers : espace)."""
    return f"{int(round(amount)):,}".replace(",", " ") + " Ar"


def format_pct(ratio: float) -> str:
    """0.1 → « 10 % »."""
    return f"{round(ratio * 100):d} %"
