"""Tests du calendrier : jours ouvrés et indisponibilités."""

from datetime import date

from app.algorithms.calendar import (
    add_working_days,
    available_days,
    count_working_days,
    is_working_day,
    next_available_day,
    unavailable_dates,
    working_days,
)

LUNDI = date(2026, 11, 16)
VENDREDI = date(2026, 11, 20)
SAMEDI = date(2026, 11, 21)


def test_jours_ouvres() -> None:
    assert is_working_day(LUNDI) and is_working_day(VENDREDI)
    assert not is_working_day(SAMEDI)
    assert count_working_days(LUNDI, VENDREDI) == 5
    assert count_working_days(LUNDI, date(2026, 11, 29)) == 10  # deux semaines
    assert working_days(VENDREDI, date(2026, 11, 23)) == [VENDREDI, date(2026, 11, 23)]
    assert count_working_days(VENDREDI, LUNDI) == 0  # intervalle vide


def test_indisponibilites_en_dates() -> None:
    jours = unavailable_dates([(date(2026, 11, 18), date(2026, 11, 19))])
    assert jours == {date(2026, 11, 18), date(2026, 11, 19)}


def test_jours_disponibles() -> None:
    off = {date(2026, 11, 18)}
    assert available_days(LUNDI, VENDREDI, off) == [
        LUNDI, date(2026, 11, 17), date(2026, 11, 19), VENDREDI,
    ]


def test_date_de_fin_saute_le_week_end() -> None:
    """Commencer un vendredi pour 3 jours : vendredi, lundi, mardi."""
    assert add_working_days(VENDREDI, 3) == date(2026, 11, 24)


def test_date_de_fin_saute_les_indisponibilites() -> None:
    """Même cas, mais indisponible le lundi : vendredi, mardi, mercredi."""
    assert add_working_days(VENDREDI, 3, {date(2026, 11, 23)}) == date(2026, 11, 25)


def test_un_jour_finit_le_jour_meme() -> None:
    assert add_working_days(LUNDI, 1) == LUNDI


def test_prochain_jour_disponible() -> None:
    assert next_available_day(SAMEDI) == date(2026, 11, 23)
    assert next_available_day(SAMEDI, {date(2026, 11, 23)}) == date(2026, 11, 24)
    assert next_available_day(LUNDI) == LUNDI
