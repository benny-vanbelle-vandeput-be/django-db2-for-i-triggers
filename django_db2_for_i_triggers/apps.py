from django.apps import AppConfig


class TriggersConfig(AppConfig):
    """The app: ``INSTALLED_APPS = [..., "django_db2_for_i_triggers"]``.

    The label is the package name (docs/DECISIONS.md, "the names").
    """

    name = "django_db2_for_i_triggers"
    label = "django_db2_for_i_triggers"
    verbose_name = "Db2 for i triggers"

    def ready(self) -> None:
        from . import checks  # noqa: F401  (registers the system checks)
