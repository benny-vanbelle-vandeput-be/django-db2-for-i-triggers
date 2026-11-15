"""Database triggers for Django models on Db2 for IBM i, in the style of django-pgtrigger.

Requires the django-db2-for-i backend (``ENGINE = "django_db2_for_i"``)::

    import django_db2_for_i_triggers as triggers

    class Order(models.Model):
        status = models.CharField(max_length=10)

        class Meta:
            triggers = [
                triggers.Protect(name="protect_deletes", operation=triggers.Delete),
                triggers.ReadOnly(name="status_read_only", fields=["status"]),
            ]

The names and arguments are django-pgtrigger's (docs/user/Usage.md).
"""

from .contrib import Protect, ReadOnly
from .core import (
    After,
    Before,
    Condition,
    Deferred,
    Delete,
    Func,
    Immediate,
    Insert,
    InsteadOf,
    Level,
    Operation,
    Operations,
    Referencing,
    Row,
    Statement,
    Timing,
    Trigger,
    Truncate,
    Update,
    UpdateOf,
    When,
)

__version__ = "0.1.0.dev0"

__all__ = [
    "After",
    "Before",
    "Condition",
    "Deferred",
    "Delete",
    "Func",
    "Immediate",
    "Insert",
    "InsteadOf",
    "Level",
    "Operation",
    "Operations",
    "Protect",
    "ReadOnly",
    "Referencing",
    "Row",
    "Statement",
    "Timing",
    "Trigger",
    "Truncate",
    "Update",
    "UpdateOf",
    "When",
]
