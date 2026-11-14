"""Can the PUB400 user create SQL triggers on a table in QTEMP (CLAUDE.md, phase 0.1)?

The backend found that ``CREATE TRIGGER`` is refused for the PUB400 user in
the user library (SQL0552, backend docs/IBMI_NOTES.md, lib_column_copy,
2026-11-13). This probe tries it in QTEMP, the one place a qtemp_ probe may
write, and records what happens:

1. The session: user, job, release (read-only).
2. The authority that matters, as far as the user may read it (read-only): the
   user's special authorities and group profile (``QSYS2.USER_INFO``) and the
   authorities on the trigger commands ``QSYS/ADDPFTRG``, ``RMVPFTRG`` and
   ``CHGPFTRG`` (``QSYS2.OBJECT_PRIVILEGES``).
3. Two tables in QTEMP: ``DJT_ORDER`` (the trigger table) and ``DJT_LOG`` (what
   an AFTER trigger writes).
4. ``CREATE TRIGGER`` in QTEMP, from the simplest form to the forms the library
   needs; each one is tried even when an earlier one failed, so a refusal can be
   told apart from a syntax error:
   - ``minimal``: AFTER INSERT, FOR EACH ROW, one INSERT, no REFERENCING, no WHEN;
   - ``after_insert``: AFTER INSERT, REFERENCING NEW AS N, writes N.ID to DJT_LOG;
   - ``read_only``: BEFORE UPDATE, REFERENCING OLD AS O NEW AS N, WHEN
     (O.STATUS <> N.STATUS), SIGNAL SQLSTATE '75001' (as ReadOnly);
   - ``protect_delete``: BEFORE DELETE, SIGNAL SQLSTATE '75002' (as Protect).
   After every failed statement the new job log messages are read
   (``QSYS2.JOBLOG_INFO``): SQL0552's second-level text names what is missing.
5. If triggers exist: fire them (insert, an allowed update, a refused update, a
   refused delete) and record the SQLSTATE, the native error and the message
   that reach the client; where the trigger programs are (``OBJECT_STATISTICS``
   on QTEMP) and what the catalog shows (``QSYS2.SYSTRIGGERS``).
6. The tables are dropped; QTEMP goes away with the job anyway.

Nothing is created or changed outside QTEMP. One connection, no retries,
commit mode *NONE (QTEMP tables are not journaled).

Usage (from the host, through the PUB400 lock):
    bin/probe qtemp_create_trigger
    bin/probe qtemp_create_trigger -- --dry-run     (print the SQL, no connection)

Findings go to docs/IBMI_NOTES.md; the result is published with
``bin/probe --publish`` as probes/results/qtemp_create_trigger.json.
"""

from __future__ import annotations

import argparse
import contextlib
import re
import sys
from typing import Any

from _common import (
    ProbeError,
    Settings,
    connect,
    print_query,
    run_query,
    run_statement,
    write_result,
)

NAME = "qtemp_create_trigger"

SESSION = (
    "SELECT CURRENT USER AS CURRENT_USER, QSYS2.JOB_NAME AS JOB_NAME, "
    "OS_VERSION, OS_RELEASE FROM SYSIBMADM.ENV_SYS_INFO"
)
USER_INFO = (
    "SELECT AUTHORIZATION_NAME, USER_CLASS_NAME, SPECIAL_AUTHORITIES, "
    "GROUP_PROFILE_NAME, SUPPLEMENTAL_GROUP_LIST "
    "FROM QSYS2.USER_INFO WHERE AUTHORIZATION_NAME = CURRENT USER"
)
COMMAND_PRIVILEGES = (
    "SELECT SYSTEM_OBJECT_NAME, AUTHORIZATION_NAME, OBJECT_AUTHORITY "
    "FROM QSYS2.OBJECT_PRIVILEGES "
    "WHERE SYSTEM_OBJECT_SCHEMA = 'QSYS' AND OBJECT_TYPE = '*CMD' "
    "AND SYSTEM_OBJECT_NAME IN ('ADDPFTRG', 'RMVPFTRG', 'CHGPFTRG') "
    "ORDER BY SYSTEM_OBJECT_NAME, AUTHORIZATION_NAME"
)
JOBLOG_LAST = "SELECT MAX(ORDINAL_POSITION) AS LAST FROM TABLE(QSYS2.JOBLOG_INFO('*')) X"
JOBLOG_SINCE = (
    "SELECT ORDINAL_POSITION, MESSAGE_ID, MESSAGE_TYPE, SEVERITY, MESSAGE_TEXT, "
    "MESSAGE_SECOND_LEVEL_TEXT FROM TABLE(QSYS2.JOBLOG_INFO('*')) X "
    "WHERE ORDINAL_POSITION > ? ORDER BY ORDINAL_POSITION"
)

TABLES = [
    (
        "create DJT_ORDER",
        "CREATE TABLE QTEMP.DJT_ORDER (ID INTEGER NOT NULL PRIMARY KEY, "
        "STATUS VARCHAR(10) NOT NULL, N INTEGER NOT NULL DEFAULT 0)",
    ),
    (
        "create DJT_LOG",
        "CREATE TABLE QTEMP.DJT_LOG (ID INTEGER NOT NULL, ACTION VARCHAR(10) NOT NULL)",
    ),
]

TRIGGERS = {
    "minimal": (
        "CREATE TRIGGER QTEMP.DJT_MIN AFTER INSERT ON QTEMP.DJT_ORDER "
        "FOR EACH ROW MODE DB2ROW "
        "INSERT INTO QTEMP.DJT_LOG VALUES (0, 'minimal')"
    ),
    "after_insert": (
        "CREATE TRIGGER QTEMP.DJT_AINS AFTER INSERT ON QTEMP.DJT_ORDER "
        "REFERENCING NEW AS N FOR EACH ROW MODE DB2ROW "
        "BEGIN ATOMIC INSERT INTO QTEMP.DJT_LOG VALUES (N.ID, 'insert'); END"
    ),
    "read_only": (
        "CREATE TRIGGER QTEMP.DJT_RO BEFORE UPDATE ON QTEMP.DJT_ORDER "
        "REFERENCING OLD AS O NEW AS N FOR EACH ROW MODE DB2ROW "
        "WHEN (O.STATUS <> N.STATUS) "
        "BEGIN ATOMIC SIGNAL SQLSTATE '75001' SET MESSAGE_TEXT = 'DJT: status is read-only'; END"
    ),
    "protect_delete": (
        "CREATE TRIGGER QTEMP.DJT_PDEL BEFORE DELETE ON QTEMP.DJT_ORDER "
        "FOR EACH ROW MODE DB2ROW "
        "BEGIN ATOMIC SIGNAL SQLSTATE '75002' SET MESSAGE_TEXT = 'DJT: delete is protected'; END"
    ),
}

# (label, statement, the trigger it exercises or None, what is expected when that trigger exists)
FIRES = [
    ("insert a row", "INSERT INTO QTEMP.DJT_ORDER (ID, STATUS) VALUES (1, 'new')", None, "ok"),
    (
        "update N (status unchanged)",
        "UPDATE QTEMP.DJT_ORDER SET N = 1 WHERE ID = 1",
        "read_only",
        "ok",
    ),
    (
        "update STATUS",
        "UPDATE QTEMP.DJT_ORDER SET STATUS = 'paid' WHERE ID = 1",
        "read_only",
        "75001",
    ),
    ("delete the row", "DELETE FROM QTEMP.DJT_ORDER WHERE ID = 1", "protect_delete", "75002"),
]
AFTER_FIRES = [
    ("rows in DJT_ORDER", "SELECT ID, STATUS, N FROM QTEMP.DJT_ORDER ORDER BY ID"),
    ("rows in DJT_LOG", "SELECT ID, ACTION FROM QTEMP.DJT_LOG ORDER BY ID, ACTION"),
    (
        "trigger programs in QTEMP (OBJECT_STATISTICS)",
        "SELECT OBJNAME, OBJTYPE, OBJATTRIBUTE, OBJTEXT "
        "FROM TABLE(QSYS2.OBJECT_STATISTICS('QTEMP', '*PGM')) X ORDER BY OBJNAME",
    ),
    (
        "catalog (QSYS2.SYSTRIGGERS)",
        "SELECT * FROM QSYS2.SYSTRIGGERS WHERE EVENT_OBJECT_SCHEMA = 'QTEMP' "
        "ORDER BY TRIGGER_NAME FETCH FIRST 10 ROWS ONLY",
    ),
]
DROPS = [
    ("drop DJT_ORDER", "DROP TABLE QTEMP.DJT_ORDER"),
    ("drop DJT_LOG", "DROP TABLE QTEMP.DJT_LOG"),
]

_SQLCODE = re.compile(r"\b(SQL\d{4})\b")


def sqlcode(result: dict[str, Any]) -> str | None:
    """The SQLxxxx message id in a failed statement's driver message, if any."""
    match = _SQLCODE.search(result.get("message", ""))
    return match.group(1) if match else None


def _joblog_last(conn) -> int | None:
    result = run_query(conn, "job log position", JOBLOG_LAST)
    return result["rows"][0]["LAST"] if result["ok"] and result["rows"] else None


def statement(conn, label: str, sql: str) -> dict[str, Any]:
    """Run one statement; when it fails, add the job log messages it produced."""
    before = _joblog_last(conn)
    result = run_statement(conn, label, sql)
    if not result["ok"]:
        result["sqlcode"] = sqlcode(result)
        if before is not None:
            log = run_query(conn, f"job log after: {label}", JOBLOG_SINCE, (before,))
            result["joblog"] = log["rows"] if log["ok"] else {"error": log["message"]}
            if log["ok"]:
                for row in log["rows"]:
                    print(f"  joblog {row['MESSAGE_ID']}: {row['MESSAGE_TEXT']}")
    return result


def run(settings: Settings) -> dict[str, Any]:
    results: dict[str, Any] = {
        "scope": "QTEMP only (two tables, up to four triggers); reads catalogs"
    }
    conn = connect(settings)
    try:
        for key, label, sql in (
            ("session", "session", SESSION),
            ("user_info", "user (QSYS2.USER_INFO)", USER_INFO),
            (
                "command_privileges",
                "trigger commands (QSYS2.OBJECT_PRIVILEGES)",
                COMMAND_PRIVILEGES,
            ),
        ):
            results[key] = run_query(conn, label, sql)
            print_query(results[key])

        results["tables"] = [statement(conn, label, sql) for label, sql in TABLES]
        if not all(step["ok"] for step in results["tables"]):
            results["conclusion"] = "the QTEMP tables could not be created; no trigger was tried"
            return results

        results["triggers"] = {name: statement(conn, name, sql) for name, sql in TRIGGERS.items()}
        created = {name for name, step in results["triggers"].items() if step["ok"]}
        results["created"] = sorted(created)

        fires = []
        for label, sql, trigger, expected in FIRES:
            step = statement(conn, label, sql)
            step["trigger"] = trigger
            step["expected"] = expected if (trigger is None or trigger in created) else "ok"
            got = "ok" if step["ok"] else step.get("sqlstate", "")
            step["as_expected"] = got == step["expected"]
            fires.append(step)
        results["fires"] = fires
        results["after"] = []
        for label, sql in AFTER_FIRES:
            query = run_query(conn, label, sql)
            print_query(query)
            results["after"].append(query)

        refused = {
            name: step.get("sqlcode")
            for name, step in results["triggers"].items()
            if not step["ok"]
        }
        results["conclusion"] = (
            "all trigger forms were created in QTEMP"
            if not refused
            else f"refused: {refused}" + (f"; created: {sorted(created)}" if created else "")
        )
    finally:
        for label, sql in DROPS:
            with contextlib.suppress(Exception):
                run_statement(conn, label, sql)
        with contextlib.suppress(Exception):
            conn.close()
    return results


def dry_run() -> None:
    print("-- qtemp_create_trigger: the statements, in order (no connection)\n")
    for label, sql in [
        ("session", SESSION),
        ("user", USER_INFO),
        ("trigger commands", COMMAND_PRIVILEGES),
        *TABLES,
        *TRIGGERS.items(),
        *[(label, sql) for label, sql, _, _ in FIRES],
        *AFTER_FIRES,
        *DROPS,
    ]:
        print(f"-- {label}\n{sql};\n")
    print(f"-- after each failed statement:\n{JOBLOG_SINCE};")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog=NAME, description=__doc__.split("\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="print the SQL; no connection")
    args = parser.parse_args(argv)
    if args.dry_run:
        dry_run()
        return 0
    try:
        settings = Settings.from_env(need_credentials=True)
        result = run(settings)
        print(f"\n{result['conclusion']}")
        print(f"result saved to {write_result(NAME, result, settings)}")
    except ProbeError as exc:
        print(f"\nPROBE FAILED [{exc.category}]: {exc}", file=sys.stderr)
        return exc.exit_code
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
