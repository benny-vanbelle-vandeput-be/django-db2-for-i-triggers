"""nox sessions.

Run inside the container:  docker compose run --rm tests nox -s <session>

lint and the offline tests (every Python x Django combination), and the probe
sessions. No IBM i test session yet: PUB400 does not allow CREATE TRIGGER
(docs/IBMI_NOTES.md). Adapted from django-db2-for-i (noxfile.py).
"""

import pathlib
import re

import nox

nox.options.default_venv_backend = "uv"
nox.options.error_on_missing_interpreters = True
nox.options.sessions = ["lint", "offline"]

# Python versions supported by each Django version, oldest first (the
# backend's docs/DJANGO_VERSIONS.md).
DJANGO_PYTHONS = {
    "5.2": ["3.12", "3.13", "3.14"],
    "6.0": ["3.12", "3.13", "3.14"],
    "6.1": ["3.12", "3.13", "3.14", "3.15"],
}
NEWEST_DJANGO = "6.1"
NEWEST_PYTHON = DJANGO_PYTHONS[NEWEST_DJANGO][-1]

OFFLINE_MATRIX = [
    (python, django) for django, pythons in DJANGO_PYTHONS.items() for python in pythons
]

# The probes talk to the driver directly; they need nothing else.
PROBE_REQUIREMENTS = ["pyodbc>=5.3"]


def install_groups(session: nox.Session, *groups: str) -> None:
    """Dependency groups (the dev and test tooling) at the versions pinned in
    uv.lock. --locked fails when pyproject.toml changed without `uv lock`.
    Django is not taken from the lock: the sessions install the newest
    release of each supported version, the one users get."""
    requirements = f"{session.virtualenv.location}/requirements-{'-'.join(groups)}.txt"
    only = [option for group in groups for option in ("--only-group", group)]
    session.run(
        "uv", "export", "--locked", "--no-emit-project", "--no-hashes", "--quiet",
        *only, "--output-file", requirements,
        external=True,
    )  # fmt: skip
    session.install("-r", requirements)


@nox.session(python=NEWEST_PYTHON)
def lint(session: nox.Session) -> None:
    """Static checks: ruff lint and format check."""
    install_groups(session, "lint")
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")


@nox.session
@nox.parametrize(
    "python,django",
    OFFLINE_MATRIX,
    ids=[f"{python}-django{django}" for python, django in OFFLINE_MATRIX],
)
def offline(session: nox.Session, django: str) -> None:
    """The offline tests: no IBM i. Every Python x every Django version."""
    install_groups(session, "test")
    session.install("-e", ".", f"Django~={django}.0")
    session.run("pytest", "-m", "offline", *session.posargs)


def _probe(session: nox.Session, prefix: str) -> tuple[str, list[str]]:
    """The probe named in the first argument (probes/<prefix>_<topic>.py) and the rest."""
    args = list(session.posargs)
    name = args.pop(0) if args else ""
    if (
        not re.fullmatch(rf"{prefix}_[a-z0-9_]+", name)
        or not pathlib.Path(f"probes/{name}.py").is_file()
    ):
        session.error(f"not a {prefix}_ probe: {name!r} (bin/probe --list)")
    return name, args


@nox.session(python=NEWEST_PYTHON)
def probe_qtemp(session: nox.Session) -> None:
    """One qtemp_ probe (read-only, or writes only in QTEMP):
    bin/probe qtemp_<topic> [-- <options>]."""
    name, args = _probe(session, "qtemp")
    session.install(*PROBE_REQUIREMENTS)
    session.run("python", f"probes/{name}.py", *args)


@nox.session(python=NEWEST_PYTHON)
def probe_lib(session: nox.Session) -> None:
    """CHANGES THE IBM i outside QTEMP: one lib_ probe, started only by
    bin/probe --approved <link> (CLAUDE.md). Dry run unless --execute."""
    name, args = _probe(session, "lib")
    env = {}
    for option, variable in (
        ("--approved", "DB2I_PROBE_APPROVED"),
        ("--approved-by", "DB2I_PROBE_APPROVED_BY"),
    ):
        if option not in args or args.index(option) + 1 >= len(args):
            session.error(f"{name} needs {option}: run it through bin/probe --approved <link>")
        index = args.index(option)
        env[variable] = args[index + 1]
        del args[index : index + 2]
    session.install(*PROBE_REQUIREMENTS)
    session.run("python", f"probes/{name}.py", *args, env=env)
