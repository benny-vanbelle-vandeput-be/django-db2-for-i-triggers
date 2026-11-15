# Installation

> **Status:** phase 1, pre-alpha. Triggers can be declared and their SQL is
> built and checked, but they are **not installed yet** (installation and
> migrations come in the next phases), and the SQL has not run on an IBM i yet
> ([Known limitations](Known-Limitations.md)).

## Requirements

- The [django-db2-for-i](https://github.com/benny-vanbelle-vandeput-be/django-db2-for-i)
  database backend, which this package installs from its git tag. Every
  database the triggers are meant for uses `ENGINE = "django_db2_for_i"`.
- Django 5.2, 6.0 or 6.1; Python 3.12 to 3.14 (3.15 with Django 6.1).
- IBM i 7.5 or later.

## Install

Until the first release, from GitHub:

```sh
pip install "django-db2-for-i-triggers @ git+https://github.com/benny-vanbelle-vandeput-be/django-db2-for-i-triggers"
```

Add the app to `INSTALLED_APPS`, next to the backend's app:

```python
INSTALLED_APPS = [
    # ...
    "django_db2_for_i",
    "django_db2_for_i_triggers",
    # your apps
]
```

Its place in the list does not matter: the app adds `triggers` to the options
Django accepts in a model's `Meta` before any model is loaded.

## Authority on IBM i

Creating an SQL trigger needs, for the user Django connects with:

- `*USE` on the command `QSYS/ADDPFTRG` (Add Physical File Trigger). Without
  it, `CREATE TRIGGER` fails with `SQL0552 - Not authorized to CREATE TRIGGER`,
  in every library;
- the authority to change the table (`*ALTER`) and to create the trigger
  program in its library.

On PUB400 `ADDPFTRG` is `*PUBLIC *EXCLUDE`, secured by the authorization list
`TRIGGER`; a user who is not on that list cannot create triggers
([IBM i notes](../IBMI_NOTES.md)). Triggers cannot be created in `QTEMP`
(IBM's `CREATE TRIGGER` documentation).

## Check

```sh
python manage.py check
```

runs the system checks of the triggers declared in `Meta.triggers`
([Usage](Usage.md#system-checks)) without connecting to the database.
