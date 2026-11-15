from django.apps import AppConfig
from django.db.models import options

# Allow ``Meta.triggers`` on models, as pgtrigger does. Django imports the app
# modules of every installed app before it loads any model, so the place of the
# app in INSTALLED_APPS does not matter. The backend extends Meta the same way
# (django_db2_for_i/apps.py).
if "triggers" not in options.DEFAULT_NAMES:
    options.DEFAULT_NAMES = (*options.DEFAULT_NAMES, "triggers")


class TriggersConfig(AppConfig):
    """The app: ``INSTALLED_APPS = [..., "django_db2_for_i_triggers"]``.

    The label is the package name (docs/DECISIONS.md, "the names").
    """

    name = "django_db2_for_i_triggers"
    label = "django_db2_for_i_triggers"
    verbose_name = "Db2 for i triggers"

    def ready(self) -> None:
        from . import checks  # noqa: F401  (registers the system checks)
