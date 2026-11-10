"""Calendrier : jours ouvrés et indisponibilités des freelances.

Conventions utilisées dans tout le projet :
- un jour ouvré est un jour du lundi au vendredi (les jours fériés ne sont pas gérés) ;
- une tâche de durée d jours occupe d jours ouvrés OÙ LE FREELANCE EST DISPONIBLE ;
  si un congé tombe au milieu, la tâche est simplement mise en pause ce jour-là ;
- la date de fin d'une tâche est son DERNIER jour de travail (inclus) ;
  une tâche qui en suit une autre commence au plus tôt le jour disponible suivant.
"""

from collections.abc import Iterable
from datetime import date, timedelta

ONE_DAY = timedelta(days=1)


def next_monday(today: date) -> date:
    """Le lundi qui suit `today` (ou `today` lui-même si c'est un lundi) : date de début d'un projet."""
    return today + timedelta(days=(7 - today.weekday()) % 7)


def is_working_day(d: date) -> bool:
    return d.weekday() < 5  # 0 = lundi … 4 = vendredi


def working_days(start: date, end: date) -> list[date]:
    """Jours ouvrés entre `start` et `end` inclus (liste vide si end < start)."""
    days = []
    d = start
    while d <= end:
        if is_working_day(d):
            days.append(d)
        d += ONE_DAY
    return days


def count_working_days(start: date, end: date) -> int:
    return len(working_days(start, end))


def unavailable_dates(periods: Iterable[tuple[date, date]]) -> set[date]:
    """Transforme des périodes (début, fin incluses) en ensemble de dates."""
    days: set[date] = set()
    for first, last in periods:
        d = first
        while d <= last:
            days.add(d)
            d += ONE_DAY
    return days


def is_available(d: date, unavailable: set[date] | frozenset[date] = frozenset()) -> bool:
    return is_working_day(d) and d not in unavailable


def available_days(start: date, end: date, unavailable: set[date] | frozenset[date] = frozenset()) -> list[date]:
    """Jours ouvrés où le freelance est disponible, entre `start` et `end` inclus."""
    return [d for d in working_days(start, end) if d not in unavailable]


def next_available_day(d: date, unavailable: set[date] | frozenset[date] = frozenset()) -> date:
    """Premier jour disponible à partir de `d` (inclus)."""
    while not is_available(d, unavailable):
        d += ONE_DAY
    return d


def add_working_days(start: date, duration: int, unavailable: set[date] | frozenset[date] = frozenset()) -> date:
    """Date de fin (dernier jour de travail) d'une tâche de `duration` jours commencée le `start`.

    Exemple : début vendredi, 3 jours → vendredi, lundi, mardi : fin = mardi.
    """
    if duration < 1:
        raise ValueError("Une tâche dure au moins un jour.")
    d = next_available_day(start, unavailable)
    remaining = duration - 1
    while remaining > 0:
        d = next_available_day(d + ONE_DAY, unavailable)
        remaining -= 1
    return d
