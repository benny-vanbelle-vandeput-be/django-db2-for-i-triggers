"""The package skeleton: it imports, the app loads, and offline tests cannot connect."""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from django.apps import apps
from django.db import connection

import django_db2_for_i_triggers
from tests.conftest import OfflineConnectionError

ROOT = Path(__file__).resolve().parents[2]


def test_version_is_pep440():
    assert re.fullmatch(
        r"\d+\.\d+\.\d+((a|b|rc)\d+)?(\.dev\d+)?", django_db2_for_i_triggers.__version__
    )


def test_app_label_is_the_package_name():
    config = apps.get_app_config("django_db2_for_i_triggers")
    assert config.name == "django_db2_for_i_triggers"


def test_settings_use_the_backend():
    assert connection.settings_dict["ENGINE"] == "django_db2_for_i"


def test_pyodbc_connect_is_refused():
    import pyodbc

    with pytest.raises(OfflineConnectionError):
        pyodbc.connect("DRIVER={none}")


def test_changelog_fragments_are_valid():
    result = subprocess.run(
        [sys.executable, "scripts/assemble_changelog.py", "check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
