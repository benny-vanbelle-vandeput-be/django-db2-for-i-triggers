# Parts of this module follow django-pgtrigger 4.17.0 (pgtrigger/core.py):
# the names, arguments and checks of the trigger primitives and of Trigger.
#
# Copyright (c) 2025, Ambition
# All rights reserved.
# Licensed under the BSD 3-Clause License; see NOTICE for the full text.
#
# The SQL is written anew for Db2 for i. Copyright (c) 2026, Benny Van Belle,
# BSD 3-Clause License (LICENSE).
"""Triggers and their parts: when, operation, level, condition, and the CREATE TRIGGER SQL.

The public names and arguments are those of django-pgtrigger, so a model can
declare the same triggers on PostgreSQL and on Db2 for i. What Db2 for i
cannot do, or what is not supported yet, is refused with ``NotSupportedError``
when the trigger is declared, never emulated (CLAUDE.md, section 5).

The SQL is built in one place, :meth:`Trigger.get_sql`, with the backend's
quoting (``connection.ops.quote_name``); it never opens a connection.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from django.db import NotSupportedError, models
from django.db.backends.utils import split_identifier
from django_db2_for_i.fields import SYSTEM_NAME

# The SQL name of an installed trigger is PREFIX + name + "_" + a 5-character hash
# of "<app>.<Model>:<name>", as pgtrigger's "pgtrigger_<name>_<hash>"
# (docs/DECISIONS.md). Db2 for i SQL names have at most 128 characters.
PREFIX = "DJTRG_"
MAX_SQL_NAME_LENGTH = 128
MAX_NAME_LENGTH = MAX_SQL_NAME_LENGTH - len(PREFIX) - len("_12345")

# The SQLSTATE of the error a Protect trigger signals (docs/DECISIONS.md).
PROTECT_SQLSTATE = "75001"

# The correlation names of the old and new row, the same as in PostgreSQL, so a
# raw condition or body written for pgtrigger ("OLD.x", "NEW.x") reads the same.
OLD = "OLD"
NEW = "NEW"

_NAME = re.compile(r"^[a-zA-Z0-9-_]+$")


class _Primitive:
    """Boilerplate for the primitive parts of a trigger."""

    values: tuple[str, ...] = ()

    def __init__(self, name: str):
        assert name in self.values
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.name!r})"

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and other.name == self.name

    def __hash__(self) -> int:
        return hash(self.name)


class Level(_Primitive):
    values = ("ROW", "STATEMENT")


Row = Level("ROW")
"""A row-level trigger (the default): ``FOR EACH ROW``."""

Statement = Level("STATEMENT")
"""A statement-level trigger: ``FOR EACH STATEMENT``. Not supported yet."""


class Referencing:
    """The transition tables of a statement-level trigger (``REFERENCING OLD TABLE ...``)."""

    def __init__(self, *, old: str | None = None, new: str | None = None):
        if not old and not new:
            raise ValueError(
                'Must provide either "old" and/or "new" to the referencing construct of a trigger'
            )
        self.old = old
        self.new = new

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Referencing):
            return False
        return self.old == other.old and self.new == other.new

    def __hash__(self) -> int:
        return hash((self.old, self.new))


class When(_Primitive):
    values = ("BEFORE", "AFTER", "INSTEAD OF")


Before = When("BEFORE")
"""``BEFORE``: the trigger runs before the row changes."""

After = When("AFTER")
"""``AFTER``: the trigger runs after the row changed."""

InsteadOf = When("INSTEAD OF")
"""``INSTEAD OF`` on views. Not supported yet."""


class Operation(_Primitive):
    values = ("UPDATE", "DELETE", "TRUNCATE", "INSERT")

    def __or__(self, other: Operation) -> Operations:
        assert isinstance(other, Operation)
        return Operations(self, other)

    def __contains__(self, other: object) -> bool:
        return self == other

    def __iter__(self):
        return iter([self])

    def render(self, connection: Any) -> str:
        """The trigger event in SQL; column names quoted by the backend."""
        return self.name


class Operations(Operation):
    """Several operations, ``OR``-ed together; the ``|`` operator is the usual spelling."""

    def __init__(self, *operations: Operation):
        for operation in operations:
            assert isinstance(operation, Operation)
        self.operations = operations
        self.name = " OR ".join(str(operation) for operation in operations)

    def __or__(self, other: Operation) -> Operations:
        assert isinstance(other, Operation)
        return Operations(*self.operations, other)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Operations) and other.operations == self.operations

    def __hash__(self) -> int:
        return hash(self.operations)

    def __contains__(self, other: object) -> bool:
        return other in self.operations

    def __iter__(self):
        return iter(self.operations)

    def render(self, connection: Any) -> str:
        return " OR ".join(operation.render(connection) for operation in self.operations)


Update = Operation("UPDATE")
"""``UPDATE`` as the trigger event."""

Delete = Operation("DELETE")
"""``DELETE`` as the trigger event."""

Truncate = Operation("TRUNCATE")
"""``TRUNCATE``: Db2 for i has no truncate trigger event; refused."""

Insert = Operation("INSERT")
"""``INSERT`` as the trigger event."""


class UpdateOf(Operation):
    """``UPDATE OF <columns>`` as the trigger event."""

    def __init__(self, *columns: str):
        if not columns:
            raise ValueError("Must provide at least one column")
        self.columns = columns
        self.name = "UPDATE OF " + ", ".join(columns)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, UpdateOf) and other.columns == self.columns

    def __hash__(self) -> int:
        return hash(self.columns)

    def render(self, connection: Any) -> str:
        quote = connection.ops.quote_name
        return "UPDATE OF " + ", ".join(quote(column) for column in self.columns)


class Timing(_Primitive):
    values = ("IMMEDIATE", "DEFERRED")


Immediate = Timing("IMMEDIATE")
"""Deferrable triggers (PostgreSQL constraint triggers): refused on Db2 for i."""

Deferred = Timing("DEFERRED")
"""Deferrable triggers (PostgreSQL constraint triggers): refused on Db2 for i."""


class Condition:
    """Free-form SQL for the ``WHEN`` of a trigger, on ``OLD`` and ``NEW``."""

    sql: str | None = None

    def __init__(self, sql: str | None = None):
        self.sql = sql or self.sql
        if not self.sql:
            raise ValueError("Must provide SQL to condition")

    def resolve(self, model: type[models.Model]) -> str:
        return self.sql


class Func:
    """A trigger body with ``{meta}``, ``{fields}`` and ``{columns}`` of the model.

    ``Func("SET NEW.{columns.total} = NEW.{columns.price} * 2;")`` renders the
    model's column names into the SQL, as in pgtrigger. The names are not quoted.
    """

    def __init__(self, func: str):
        self.func = func

    def render(self, **kwargs: Any) -> str:
        return self.func.format(**kwargs)


class _AttrDict(dict):
    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _not_supported(what: str, why: str) -> NotSupportedError:
    return NotSupportedError(
        f"{what} are not supported on Db2 for i: {why} (docs/user/Known-Limitations.md)"
    )


class Trigger:
    """A trigger with a free-form SQL body, or the base of the trigger classes.

    The arguments are pgtrigger's, plus ``system_name``: the IBM i system name
    (at most 10 characters) of the trigger program, written as ``PROGRAM NAME``;
    without it, Db2 for i chooses one.
    """

    name: str | None = None
    level: Level = Row
    when: When | None = None
    operation: Operation | None = None
    condition: Condition | None = None
    referencing: Referencing | None = None
    func: Func | str | None = None
    declare: list[tuple[str, str]] | None = None
    timing: Timing | None = None
    system_name: str | None = None

    def __init__(
        self,
        *,
        name: str | None = None,
        level: Level | None = None,
        when: When | None = None,
        operation: Operation | None = None,
        condition: Condition | None = None,
        referencing: Referencing | None = None,
        func: Func | str | None = None,
        declare: list[tuple[str, str]] | None = None,
        timing: Timing | None = None,
        system_name: str | None = None,
    ) -> None:
        self.name = name or self.name
        self.level = level or self.level
        self.when = when or self.when
        self.operation = operation or self.operation
        self.condition = condition or self.condition
        self.referencing = referencing or self.referencing
        self.func = func or self.func
        self.declare = declare or self.declare
        self.timing = timing or self.timing
        self.system_name = system_name or self.system_name

        if not self.level or not isinstance(self.level, Level):
            raise ValueError(f'Invalid "level" attribute: {self.level}')
        if not self.when or not isinstance(self.when, When):
            raise ValueError(f'Invalid "when" attribute: {self.when}')
        if not self.operation or not isinstance(self.operation, Operation):
            raise ValueError(f'Invalid "operation" attribute: {self.operation}')
        if self.timing and not isinstance(self.timing, Timing):
            raise ValueError(f'Invalid "timing" attribute: {self.timing}')
        if self.level == Row and self.referencing:
            raise ValueError('Row-level triggers cannot have a "referencing" attribute')
        if self.timing and self.level != Row:
            raise ValueError('Deferrable triggers must have "level" attribute as "Row"')
        if self.timing and self.when != After:
            raise ValueError('Deferrable triggers must have "when" attribute as "After"')
        if not self.name:
            raise ValueError('Trigger must have "name" attribute')

        self.validate_name()
        if self.system_name:
            self.system_name = self.validate_system_name(self.system_name)
        self.validate_db2()

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name}>"

    # --- Validation ---------------------------------------------------------------

    def validate_name(self) -> None:
        """The name is short enough and has only letters, digits, - and _."""
        if len(self.name) > MAX_NAME_LENGTH:
            raise ValueError(f'Trigger name "{self.name}" > {MAX_NAME_LENGTH} characters.')
        if not _NAME.match(self.name):
            raise ValueError(
                f'Trigger name "{self.name}" has invalid characters.'
                " Only alphanumeric characters, hyphens, and underscores are allowed."
            )

    @staticmethod
    def validate_system_name(system_name: str) -> str:
        """The system name in upper case; ValueError if it is not a valid one."""
        normalized = system_name.strip().upper()
        if not SYSTEM_NAME.fullmatch(normalized):
            raise ValueError(
                f'Trigger system name "{system_name}" is not a valid IBM i system name: at most'
                " 10 characters, letters, digits or _, starting with a letter."
            )
        return normalized

    def validate_db2(self) -> None:
        """Refuse what Db2 for i cannot do, or what is not supported yet."""
        if self.timing:
            raise _not_supported(
                "Deferrable triggers (timing=Immediate/Deferred)",
                "Db2 for i has no constraint triggers deferred to the commit",
            )
        if Truncate in self.operation:
            raise _not_supported("TRUNCATE triggers", "Db2 for i has no truncate trigger event")
        if self.level == Statement:
            raise _not_supported("Statement-level triggers", "not supported yet (planned, phase 4)")
        if self.when == InsteadOf:
            raise _not_supported("INSTEAD OF triggers", "not supported yet (planned, phase 4)")

    # --- Names --------------------------------------------------------------------

    def get_uri(self, model: type[models.Model]) -> str:
        """``<app>.<Model>:<trigger>``, as pgtrigger."""
        return f"{model._meta.app_label}.{model._meta.object_name}:{self.name}"

    def get_db2id(self, model: type[models.Model]) -> str:
        """The trigger's SQL name: PREFIX, the name and a hash of its URI, in upper case."""
        model_hash = hashlib.sha1(self.get_uri(model).encode()).hexdigest()[:5]
        db2id = f"{PREFIX}{self.name}_{model_hash}".upper()
        if len(db2id) > MAX_SQL_NAME_LENGTH:
            raise ValueError(
                f'Trigger identifier "{db2id}" is greater than {MAX_SQL_NAME_LENGTH} chars'
            )
        return db2id

    # --- Parts, as in pgtrigger, overridable by subclasses -----------------------

    def get_condition(self, model: type[models.Model]) -> Condition | None:
        return self.condition

    def get_declare(self, model: type[models.Model]) -> list[tuple[str, str]]:
        """``[(name, type), ...]`` for the ``DECLARE`` statements of the body."""
        return self.declare or []

    def get_func(self, model: type[models.Model]) -> Func | str:
        """The body of the trigger: SQL statements between ``BEGIN ATOMIC`` and ``END``."""
        if not self.func:
            raise ValueError("Must define func attribute or implement get_func")
        return self.func

    def get_func_template_kwargs(self, model: type[models.Model]) -> dict[str, Any]:
        fields = _AttrDict({field.name: field for field in model._meta.fields})
        columns = _AttrDict({field.name: field.column for field in model._meta.fields})
        return {"meta": model._meta, "fields": fields, "columns": columns}

    # --- Rendering ----------------------------------------------------------------

    def render_condition(self, model: type[models.Model], connection: Any = None) -> str:
        condition = self.get_condition(model)
        if condition is None:
            return ""
        if hasattr(condition, "resolve_sql"):
            resolved = condition.resolve_sql(model, connection).strip()
        else:
            resolved = condition.resolve(model).strip()
        if not resolved:
            return ""
        if not resolved.startswith("("):
            resolved = f"({resolved})"
        return f"WHEN {resolved}"

    def render_declare(self, model: type[models.Model]) -> str:
        declare = self.get_declare(model)
        return " ".join(f"DECLARE {name} {type_};" for name, type_ in declare)

    def render_func(self, model: type[models.Model], connection: Any = None) -> str:
        func = self.get_func(model)
        if isinstance(func, Func):
            return func.render(**self.get_func_template_kwargs(model))
        return func

    def render_referencing(self) -> str:
        """Row-level triggers see the old and the new row as OLD and NEW.

        Db2 for i fills OLD with nulls for an insert and NEW with nulls for a
        delete, so both are declared for every event (IBM's CREATE TRIGGER
        documentation; not yet run on IBM i, docs/user/Known-Limitations.md).
        """
        return f"REFERENCING OLD ROW AS {OLD} NEW ROW AS {NEW}"

    def get_sql(self, model: type[models.Model], connection: Any) -> str:
        """The ``CREATE TRIGGER`` statement for the model. Never opens a connection."""
        quote = connection.ops.quote_name
        library, _table = split_identifier(model._meta.db_table)
        name = quote(self.get_db2id(model))
        if library:
            name = f"{quote(library)}.{name}"
        declare = self.render_declare(model)
        body = self.render_func(model, connection).strip()
        lines = [
            f"CREATE TRIGGER {name}",
            f"{self.when} {self.operation.render(connection)} ON {quote(model._meta.db_table)}",
            self.render_referencing(),
            f"FOR EACH {self.level} MODE DB2ROW",
            f"PROGRAM NAME {self.system_name}" if self.system_name else "",
            self.render_condition(model, connection),
            "BEGIN ATOMIC",
            declare,
            body,
            "END",
        ]
        return "\n".join(line for line in lines if line)
