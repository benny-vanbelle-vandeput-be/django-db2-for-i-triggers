"""Settings for the offline tests: no IBM i, the backend's capabilities from a profile.

The connection must never be opened with these settings: HOST is a reserved,
unresolvable name and the conftest guard refuses ``pyodbc.connect``.
"""

SECRET_KEY = "offline-tests-not-secret"
USE_TZ = True
TIME_ZONE = "UTC"
INSTALLED_APPS = ["django_db2_for_i", "django_db2_for_i_triggers", "tests.testapp"]
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

DATABASES = {
    "default": {
        "ENGINE": "django_db2_for_i",
        "NAME": "DJTEST",
        "HOST": "offline.invalid",
        "USER": "DJUSER",
        "PASSWORD": "offline-not-a-password",
        "OPTIONS": {"capabilities": "7.5"},
    }
}
