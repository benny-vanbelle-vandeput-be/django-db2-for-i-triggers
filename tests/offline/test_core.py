# Test cases ported from django-pgtrigger 4.17.0 (pgtrigger/tests/test_core.py
# and test_contrib.py): the argument checks, the operations, the names and the
# DECLARE rendering, adapted to Db2 for i. The tests that need PostgreSQL are
# not ported; they return as IBM i tests when an IBM i allows CREATE TRIGGER.
#
# Copyright (c) 2025, Ambition
# All rights reserved.
# Licensed under the BSD 3-Clause License; see NOTICE for the full text.
#
# Db2 for i adaptations: Copyright (c) 2026, Benny Van Belle, BSD 3-Clause
# License (LICENSE).
"""The trigger primitives and Trigger, Protect and ReadOnly without a database."""

import pytest
from django.core.exceptions import FieldDoesNotExist
from django.db import NotSupportedError, connection

import django_db2_for_i_triggers as triggers
from django_db2_for_i_triggers import core
from tests.testapp.models import Ledger, Order


def test_declaration_rendering():
    """Triggers with a DECLARE are rendered as Db2 for i DECLARE statements."""

    class DeclaredTrigger(triggers.Trigger):
        def get_declare(self, model):
            return [("var_name", "INTEGER")]

    rendered = DeclaredTrigger(
        name="test", when=triggers.Before, operation=triggers.Insert
    ).render_declare(None)
    assert rendered == "DECLARE var_name INTEGER;"

    class DeclaredTriggerMultiple(triggers.Trigger):
        def get_declare(self, model):
            return [("var_name", "INTEGER"), ("var2_name", "VARCHAR(10)")]

    rendered = DeclaredTriggerMultiple(
        name="test", when=triggers.Before, operation=triggers.Insert
    ).render_declare(None)
    assert rendered == "DECLARE var_name INTEGER; DECLARE var2_name VARCHAR(10);"


def test_max_name_length():
    """A name of exactly MAX_NAME_LENGTH works; one more character is refused."""
    trigger = triggers.Protect(name="t" * core.MAX_NAME_LENGTH, operation=triggers.Update)
    assert len(trigger.get_db2id(Order)) == core.MAX_SQL_NAME_LENGTH

    with pytest.raises(ValueError, match=f"> {core.MAX_NAME_LENGTH}"):
        triggers.Protect(name="a" * (core.MAX_NAME_LENGTH + 1), operation=triggers.Update)


def test_invalid_name_characters():
    """Names contain only letters, digits, hyphens and underscores."""
    triggers.Protect(name="hello_world-111", operation=triggers.Update)
    with pytest.raises(ValueError, match="alphanumeric"):
        triggers.Protect(name="hello.world", operation=triggers.Update)


def test_arg_checks():
    """The argument checks of the trigger module."""
    with pytest.raises(ValueError, match='Must provide either "old" and/or "new"'):
        triggers.Referencing()

    with pytest.raises(ValueError, match="Must provide SQL"):
        triggers.Condition()

    with pytest.raises(ValueError, match="Must provide at least one"):
        triggers.UpdateOf()

    with pytest.raises(ValueError, match='must have "name"'):
        triggers.Trigger(when=triggers.Before, operation=triggers.Update)

    with pytest.raises(ValueError, match='Invalid "level"'):
        triggers.Trigger(level="invalid")

    with pytest.raises(ValueError, match='Invalid "when"'):
        triggers.Trigger(when="invalid")

    with pytest.raises(ValueError, match='Invalid "operation"'):
        triggers.Trigger(when=triggers.Before, operation="invalid")

    with pytest.raises(ValueError, match='Invalid "timing"'):
        triggers.Trigger(when=triggers.Before, operation=triggers.Update, timing="timing")

    with pytest.raises(ValueError, match="Row-level triggers cannot have"):
        triggers.Trigger(
            when=triggers.Before,
            operation=triggers.Update,
            referencing=triggers.Referencing(old="old_table"),
        )

    with pytest.raises(ValueError, match='must have "level" attribute'):
        triggers.Trigger(
            level=triggers.Statement,
            when=triggers.After,
            operation=triggers.Update,
            timing=triggers.Immediate,
        )

    with pytest.raises(ValueError, match='must have "when" attribute'):
        triggers.Trigger(
            level=triggers.Row,
            when=triggers.Before,
            operation=triggers.Update,
            timing=triggers.Immediate,
        )

    with pytest.raises(ValueError, match="Must define func"):
        triggers.Trigger(name="test", when=triggers.Before, operation=triggers.Update).get_func(
            None
        )


def test_operations():
    """Operations and OR-ing them together; UPDATE OF quotes with the backend."""
    assert str(triggers.Update) == "UPDATE"
    assert triggers.UpdateOf("col1").render(connection) == 'UPDATE OF "COL1"'
    assert triggers.UpdateOf("c1", "c2").render(connection) == 'UPDATE OF "C1", "C2"'

    assert str(triggers.Update | triggers.Delete) == "UPDATE OR DELETE"
    assert str(triggers.Update | triggers.Delete | triggers.Insert) == "UPDATE OR DELETE OR INSERT"
    assert str(triggers.Delete | triggers.Update) == "DELETE OR UPDATE"
    assert triggers.Delete in (triggers.Update | triggers.Delete)


def test_read_only_args():
    """ReadOnly takes fields or exclude, not both (pgtrigger's test_read_only)."""
    with pytest.raises(ValueError, match="only one of"):
        triggers.ReadOnly(name="value", fields=["level"], exclude=["hello"])


def test_read_only_unknown_field():
    with pytest.raises(FieldDoesNotExist):
        triggers.ReadOnly(name="value", fields=["missing"]).get_sql(Order, connection)
    with pytest.raises(FieldDoesNotExist):
        triggers.ReadOnly(name="value", exclude=["missing"]).get_sql(Order, connection)


# --- Db2 for i specifics -------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"operation": triggers.Truncate}, "TRUNCATE triggers"),
        ({"operation": triggers.Delete | triggers.Truncate}, "TRUNCATE triggers"),
        ({"operation": triggers.Delete, "level": triggers.Statement}, "Statement-level"),
        (
            {"operation": triggers.Update, "when": triggers.After, "timing": triggers.Deferred},
            "Deferrable",
        ),
    ],
)
def test_not_supported(kwargs, match):
    """What Db2 for i cannot do, or what is not supported yet, is refused when declared."""
    kwargs = {"when": triggers.Before, **kwargs}
    with pytest.raises(NotSupportedError, match=match):
        triggers.Trigger(name="test", func="x", **kwargs)


def test_instead_of_not_supported_yet():
    with pytest.raises(NotSupportedError, match="INSTEAD OF"):
        triggers.Trigger(name="t", when=triggers.InsteadOf, operation=triggers.Insert, func="x")


@pytest.mark.parametrize("system_name", ["ORDPROT", "ordprot", " OrdProt ", "A_1234567"])
def test_system_name_is_normalized(system_name):
    trigger = triggers.Protect(name="t", operation=triggers.Delete, system_name=system_name)
    assert trigger.system_name == system_name.strip().upper()
    assert f"PROGRAM NAME {trigger.system_name}\n" in trigger.get_sql(Order, connection)


@pytest.mark.parametrize("system_name", ["1ORDER", "ORDER-PROT", "ABCDEFGHIJK", "ORD#1"])
def test_invalid_system_name(system_name):
    with pytest.raises(ValueError, match="not a valid IBM i system name"):
        triggers.Protect(name="t", operation=triggers.Delete, system_name=system_name)


def test_no_program_name_without_system_name():
    assert "PROGRAM NAME" not in triggers.Protect(name="t", operation=triggers.Delete).get_sql(
        Order, connection
    )


def test_db2id_is_stable_and_per_model():
    trigger = triggers.Protect(name="protect", operation=triggers.Delete)
    assert trigger.get_db2id(Order) == trigger.get_db2id(Order)
    assert trigger.get_db2id(Order) != trigger.get_db2id(Ledger)
    assert trigger.get_db2id(Order).startswith("DJTRG_PROTECT_")


def test_trigger_in_another_library_is_qualified():
    sql = triggers.Protect(name="t", operation=triggers.Delete).get_sql(Ledger, connection)
    assert sql.startswith('CREATE TRIGGER "SALES"."DJTRG_T_')
    assert ' ON "SALES"."LEDGER"\n' in sql


def test_protect_message_quotes_are_doubled():
    class Quoted(triggers.Protect):
        def get_message(self, model):
            return "it's protected"

    sql = Quoted(name="t", operation=triggers.Delete).get_sql(Order, connection)
    assert "MESSAGE_TEXT = 'it''s protected';" in sql
