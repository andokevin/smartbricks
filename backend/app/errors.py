"""Erreur métier unique : les services la lèvent, main.py la transforme en réponse HTTP.

Ainsi les services ne dépendent pas de FastAPI et leurs messages restent en français clair.
"""


class AppError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def not_found(what: str) -> AppError:
    return AppError(404, f"{what} introuvable.")


def conflict(detail: str) -> AppError:
    return AppError(409, detail)
