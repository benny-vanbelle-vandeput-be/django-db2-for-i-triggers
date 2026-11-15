"""Models for the offline tests. They are never migrated: their triggers are rendered only."""

from django.db import models

import django_db2_for_i_triggers as triggers


class Order(models.Model):
    """The example of the README: a protected delete and a read-only field."""

    status = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    note = models.CharField(max_length=100, blank=True, db_column="ORDER_NOTE")

    class Meta:
        app_label = "testapp"
        triggers = [
            triggers.Protect(name="protect_deletes", operation=triggers.Delete),
            triggers.ReadOnly(name="status_read_only", fields=["status"]),
            triggers.ReadOnly(name="all_but_note", exclude=["note"], system_name="ordronly"),
        ]


class Ledger(models.Model):
    """A free-form trigger with a condition, DECLARE and a templated body, in a library."""

    amount = models.DecimalField(max_digits=9, decimal_places=2)
    total = models.DecimalField(max_digits=11, decimal_places=2, default=0)

    class Meta:
        app_label = "testapp"
        db_table = 'SALES"."LEDGER'
        triggers = [
            triggers.Trigger(
                name="double_total",
                when=triggers.Before,
                operation=triggers.Insert | triggers.UpdateOf("amount"),
                condition=triggers.Condition("NEW.AMOUNT > 0"),
                declare=[("factor", "INTEGER")],
                func=triggers.Func(
                    "SET factor = 2; SET NEW.{columns.total} = NEW.{columns.amount} * factor;"
                ),
                system_name="LEDGDBL",
            ),
            triggers.Protect(
                name="protect_changes",
                operation=triggers.Update | triggers.Delete,
            ),
        ]
