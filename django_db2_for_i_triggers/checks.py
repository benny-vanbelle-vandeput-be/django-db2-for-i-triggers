"""System checks (``manage.py check``) for the triggers declared in ``Meta.triggers``.

- ``django_db2_for_i_triggers.E001``: models declare triggers, but no database
  in ``DATABASES`` uses the django-db2-for-i backend
  (``ENGINE = "django_db2_for_i"``); other engines are not supported.
- ``E002``: ``Meta.triggers`` is not a list of triggers.
- ``E003``: two triggers of one model have the same name.
- ``E004``: two triggers have the same ``system_name``; their programs would
  collide (a library holds one ``*PGM`` object per name).
- ``E005``: the trigger's SQL cannot be built for the model (for example a
  ``ReadOnly`` field that does not exist).

None of them opens a database connection.
"""

from __future__ import annotations

from collections import defaultdict

from django.apps import apps
from django.conf import settings
from django.core import checks
from django.db import connections

from .core import Trigger

ENGINE = "django_db2_for_i"
E001 = "django_db2_for_i_triggers.E001"
E002 = "django_db2_for_i_triggers.E002"
E003 = "django_db2_for_i_triggers.E003"
E004 = "django_db2_for_i_triggers.E004"
E005 = "django_db2_for_i_triggers.E005"


def _db2_aliases() -> list[str]:
    return [alias for alias, config in settings.DATABASES.items() if config.get("ENGINE") == ENGINE]


def _declared(app_configs) -> list[tuple[type, object]]:
    """(model, Meta.triggers) of every model that declares triggers."""
    configs = app_configs or apps.get_app_configs()
    return [
        (model, model._meta.triggers)
        for config in configs
        for model in config.get_models()
        if getattr(model._meta, "triggers", None)
    ]


@checks.register(checks.Tags.models)
def check_triggers(app_configs=None, **kwargs) -> list[checks.CheckMessage]:
    errors: list[checks.CheckMessage] = []
    declared = _declared(app_configs)
    if not declared:
        return errors

    aliases = _db2_aliases()
    if not aliases:
        errors.append(
            checks.Error(
                "Models declare triggers in Meta.triggers, but no database uses the "
                f'django-db2-for-i backend (ENGINE = "{ENGINE}").',
                hint="django_db2_for_i_triggers works only with Db2 for i through "
                "django-db2-for-i.",
                id=E001,
            )
        )
    connection = connections[aliases[0]] if aliases else None

    system_names: dict[str, list[str]] = defaultdict(list)
    for model, triggers in declared:
        if not isinstance(triggers, (list, tuple)) or not all(
            isinstance(trigger, Trigger) for trigger in triggers
        ):
            errors.append(
                checks.Error(
                    "Meta.triggers must be a list of triggers (django_db2_for_i_triggers.Trigger).",
                    obj=model,
                    id=E002,
                )
            )
            continue
        seen: set[str] = set()
        for trigger in triggers:
            if trigger.name in seen:
                errors.append(
                    checks.Error(
                        f"Two triggers of {model._meta.label} are named {trigger.name!r}.",
                        hint="Give each trigger of a model its own name.",
                        obj=model,
                        id=E003,
                    )
                )
            seen.add(trigger.name)
            if trigger.system_name:
                system_names[trigger.system_name].append(trigger.get_uri(model))
            if connection is not None:
                try:
                    trigger.get_sql(model, connection)
                except Exception as exc:
                    errors.append(
                        checks.Error(
                            f"Trigger {trigger.get_uri(model)!r}: {exc}",
                            obj=model,
                            id=E005,
                        )
                    )

    for system_name, uris in sorted(system_names.items()):
        if len(uris) > 1:
            errors.append(
                checks.Error(
                    f"The system name {system_name!r} is used by more than one trigger: "
                    f"{', '.join(uris)}.",
                    hint="Give each trigger its own system_name: its program is an object "
                    "with that name in the library.",
                    id=E004,
                )
            )
    return errors
