"""The CREATE TRIGGER SQL of every trigger of the test models, against golden files.

Each golden file, ``tests/offline/golden/<Model>__<trigger>.sql``, starts with
a verification stamp: ``-- verified: <date> <system>`` once the SQL ran on an
IBM i, ``-- verified: no (<reason>)`` until then. ``--update-goldens`` rewrites
the SQL and keeps the stamp; a new file gets UNVERIFIED. Never in CI.
"""

from pathlib import Path

import pytest
from django.apps import apps
from django.db import connection

GOLDEN_DIR = Path(__file__).parent / "golden"
UNVERIFIED = "-- verified: no (no IBM i system allows CREATE TRIGGER yet, docs/IBMI_NOTES.md)"
STAMP_PREFIX = "-- verified: "


def _cases() -> list:
    return [
        pytest.param(model, trigger, id=f"{model.__name__}__{trigger.name}")
        for model in apps.get_app_config("testapp").get_models()
        for trigger in getattr(model._meta, "triggers", [])
    ]


def _split(text: str) -> tuple[str, str]:
    stamp, _, sql = text.partition("\n")
    assert stamp.startswith(STAMP_PREFIX), "a golden file starts with its verification stamp"
    return stamp, sql.rstrip("\n")


@pytest.mark.parametrize(("model", "trigger"), _cases())
def test_golden(model, trigger, request):
    path = GOLDEN_DIR / f"{model.__name__}__{trigger.name}.sql"
    sql = trigger.get_sql(model, connection)
    if request.config.getoption("--update-goldens"):
        stamp = _split(path.read_text())[0] if path.exists() else UNVERIFIED
        if not path.exists() or _split(path.read_text())[1] != sql:
            path.write_text(f"{stamp}\n{sql}\n")
    assert path.exists(), f"no golden file {path.name}: run with --update-goldens"
    assert _split(path.read_text())[1] == sql


def test_every_golden_has_a_trigger():
    expected = {
        f"{model.__name__}__{trigger.name}.sql"
        for model in apps.get_app_config("testapp").get_models()
        for trigger in getattr(model._meta, "triggers", [])
    }
    assert {path.name for path in GOLDEN_DIR.glob("*.sql")} == expected
