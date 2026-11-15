"""Database triggers for Django models on Db2 for IBM i, in the style of django-pgtrigger.

Requires the django-db2-for-i backend (``ENGINE = "django_db2_for_i"``). The
public API (``Trigger``, ``Protect``, ``ReadOnly``, ...) arrives in phase 1;
see CLAUDE.md and docs/pgtrigger-mapping.md.
"""

__version__ = "0.1.0.dev0"
