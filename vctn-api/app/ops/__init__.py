"""Operations monitoring (``/api/v1/ops``).

A module of the single FastAPI monolith — never a separate service. It observes
how the system runs, while ``analytics`` observes what users do and ``audit``
records who changed what.
"""
