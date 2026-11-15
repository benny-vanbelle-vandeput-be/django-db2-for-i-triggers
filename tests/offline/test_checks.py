"""The system checks of Meta.triggers, on isolated models; no connection."""

import pytest
from django.db import models
from django.test.utils import isolate_apps

import django_db2_for_i_triggers as triggers
from django_db2_for_i_triggers import checks


def _run(*models_):
    from django.apps import apps

    config = apps.get_app_config("testapp")
    original = config.get_models
    config.get_models = lambda *a, **k: list(models_)
    try:
        return checks.check_triggers([config])
    finally:
        config.get_models = original


def _ids(errors):
    return [error.id for error in errors]


def test_the_test_models_pass():
    assert checks.check_triggers() == []


@isolate_apps("tests.testapp")
def test_e001_no_db2_database(monkeypatch):
    class Model(models.Model):
        class Meta:
            app_label = "testapp"
            triggers = [triggers.Protect(name="p", operation=triggers.Delete)]

    # As if no alias of DATABASES had ENGINE = "django_db2_for_i".
    monkeypatch.setattr(checks, "_db2_aliases", lambda: [])
    assert _ids(_run(Model)) == [checks.E001]


@isolate_apps("tests.testapp")
@pytest.mark.parametrize("value", ["not a list", ["not a trigger"]])
def test_e002_not_a_list_of_triggers(value):
    class Model(models.Model):
        class Meta:
            app_label = "testapp"
            triggers = value

    assert _ids(_run(Model)) == [checks.E002]


@isolate_apps("tests.testapp")
def test_e003_duplicate_names():
    class Model(models.Model):
        class Meta:
            app_label = "testapp"
            triggers = [
                triggers.Protect(name="p", operation=triggers.Delete),
                triggers.Protect(name="p", operation=triggers.Update),
            ]

    assert _ids(_run(Model)) == [checks.E003]


@isolate_apps("tests.testapp")
def test_e004_duplicate_system_names():
    class First(models.Model):
        class Meta:
            app_label = "testapp"
            triggers = [triggers.Protect(name="p", operation=triggers.Delete, system_name="PROT")]

    class Second(models.Model):
        class Meta:
            app_label = "testapp"
            triggers = [triggers.Protect(name="q", operation=triggers.Delete, system_name="prot")]

    assert _ids(_run(First, Second)) == [checks.E004]


@isolate_apps("tests.testapp")
def test_e005_sql_cannot_be_built():
    class Model(models.Model):
        status = models.CharField(max_length=10)

        class Meta:
            app_label = "testapp"
            triggers = [triggers.ReadOnly(name="r", fields=["missing"])]

    errors = _run(Model)
    assert _ids(errors) == [checks.E005]
    assert "missing" in errors[0].msg
