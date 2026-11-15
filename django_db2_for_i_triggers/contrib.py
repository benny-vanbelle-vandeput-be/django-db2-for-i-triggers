# Protect and ReadOnly follow django-pgtrigger 4.17.0 (pgtrigger/contrib.py):
# their names, arguments and checks.
#
# Copyright (c) 2025, Ambition
# All rights reserved.
# Licensed under the BSD 3-Clause License; see NOTICE for the full text.
#
# The SQL is written anew for Db2 for i. Copyright (c) 2026, Benny Van Belle,
# BSD 3-Clause License (LICENSE).
"""The ready-made trigger classes: Protect and ReadOnly (more in later phases)."""

from __future__ import annotations

from typing import Any

from django.db import models

from . import core


def _column(model: type[models.Model], field: models.Field | str) -> str:
    field = field if isinstance(field, models.Field) else model._meta.get_field(field)
    if not field.column:
        raise ValueError(f"Field {field.name} does not reference a database column.")
    return field.column


def _sql_string(text: str) -> str:
    """A string constant: in single quotes, single quotes doubled."""
    return "'" + text.replace("'", "''") + "'"


class Protect(core.Trigger):
    """A trigger that refuses the operation with an error (``SIGNAL SQLSTATE``)."""

    when: core.When = core.Before

    def get_message(self, model: type[models.Model]) -> str:
        _library, table = core.split_identifier(model._meta.db_table)
        return (
            f"django_db2_for_i_triggers: Cannot {str(self.operation).lower()} rows from "
            f"{table} table"
        )

    def get_func(self, model: type[models.Model]) -> str:
        message = _sql_string(self.get_message(model))
        return f"SIGNAL SQLSTATE '{core.PROTECT_SQLSTATE}' SET MESSAGE_TEXT = {message};"


class _ChangeCondition(core.Condition):
    """``OLD.c1 IS DISTINCT FROM NEW.c1 OR ...`` over the columns of some fields.

    Built with the backend's quoting, so it needs the connection
    (:meth:`resolve_sql`); :meth:`resolve` alone is not enough.
    """

    def __init__(self, fields: list[str]):
        self.fields = fields
        self.sql = "<resolved per model>"

    def resolve(self, model: type[models.Model]) -> str:
        raise ValueError("this condition is resolved with the connection (resolve_sql)")

    def resolve_sql(self, model: type[models.Model], connection: Any) -> str:
        quote = connection.ops.quote_name
        return " OR ".join(
            f"{core.OLD}.{quote(column)} IS DISTINCT FROM {core.NEW}.{quote(column)}"
            for column in (_column(model, field) for field in self.fields)
        )


class ReadOnly(Protect):
    """A trigger that refuses changes to fields.

    With ``fields``, only those fields are protected; with ``exclude``, every
    field except those; with neither, every field.
    """

    fields: list[str] | None = None
    exclude: list[str] | None = None
    operation: core.Operation = core.Update

    def __init__(
        self,
        *,
        fields: list[str] | None = None,
        exclude: list[str] | None = None,
        **kwargs: Any,
    ):
        self.fields = fields or self.fields
        self.exclude = exclude or self.exclude
        if self.fields and self.exclude:
            raise ValueError('Must provide only one of "fields" or "exclude" to ReadOnly trigger')
        super().__init__(**kwargs)

    def get_condition(self, model: type[models.Model]) -> core.Condition:
        if self.exclude:
            for field in self.exclude:
                model._meta.get_field(field)  # FieldDoesNotExist for a wrong name
            fields = [
                field.name
                for field in model._meta.concrete_fields
                if field.name not in self.exclude
            ]
        elif self.fields:
            fields = [model._meta.get_field(field).name for field in self.fields]
        else:
            fields = [field.name for field in model._meta.concrete_fields]
        return _ChangeCondition(fields)
