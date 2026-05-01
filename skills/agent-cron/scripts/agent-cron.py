#!/usr/bin/env python3
"""agent-cron — persistent reminders via systemd --user timers.

Subcomandos:
  add     create a one-shot or recurring timer
  list    show all agent-cron timers
  rm      remove a timer

Why this and not CronCreate? CronCreate from the harness is session-only in
many setups (the durable=true flag is silently ignored). systemd --user
timers survive restarts, reboots, and don't depend on the agent being alive.

Stdlib only. No external deps.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import uuid

UNIT_DIR = pathlib.Path.home() / ".config/systemd/user"
PREFIX = "agent-cron-"


def _slug(name: str) -> str:
    """Sanitize name for use in unit file name."""
    safe = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    return safe or uuid.uuid4().hex[:8]


def _validate_oncalendar(spec: str) -> None:
    """Basic sanity check. systemd-analyze does the real validation."""
    if not spec or len(spec) > 200:
        raise ValueError(f"invalid OnCalendar: {spec!r}")


def _systemd_analyze(spec: str) -> str:
    """Use systemd-analyze calendar to validate and show next fire time."""
    try:
        proc = subprocess.run(
            ["systemd-analyze", "calendar", spec],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            raise ValueError(
                f"systemd-analyze rejected OnCalendar={spec!r}:\n{proc.stderr}"
            )
        return proc.stdout
    except FileNotFoundError:
        return "(systemd-analyze not available — skipping validation)"


def cmd_add(args: argparse.Namespace) -> int:
    """Create a one-shot or recurring timer."""
    if not args.at and not args.on_calendar:
        sys.stderr.write("ERROR: provide --at or --on-calendar\n")
        return 2

    if args.at and args.on_calendar:
        sys.stderr.write("ERROR: --at and --on-calendar are mutually exclusive\n")
        return 2

    name = _slug(args.name or f"{int(dt.datetime.now().timestamp())}")
    unit_name = f"{PREFIX}{name}"

    if args.at:
        # parse "YYYY-MM-DD HH:MM" or "HH:MM today" etc. Keep simple: ISO-8601 only.
        try:
            target = dt.datetime.fromisoformat(args.at)
        except ValueError:
            sys.stderr.write(
                f"ERROR: --at must be ISO-8601 (e.g. '2026-04-30 21:00'). got: {args.at!r}\n"
            )
            return 2
        on_calendar = target.strftime("%Y-%m-%d %H:%M:%S")
        recurring = False
    else:
        on_calendar = args.on_calendar
        recurring = True

    _validate_oncalendar(on_calendar)
    next_fire = _systemd_analyze(on_calendar)

    # Service unit
    env_file_line = ""
    if args.env_file:
        env_path = pathlib.Path(args.env_file).expanduser().resolve()
        if not env_path.exists():
            sys.stderr.write(f"ERROR: --env-file does not exist: {env_path}\n")
            return 2
        env_file_line = f"EnvironmentFile={env_path}\n"

    service = f"""[Unit]
Description=agent-cron task: {name}
After=network-online.target

[Service]
Type=oneshot
{env_file_line}ExecStart=/bin/bash -c {_shell_quote(args.command)}
"""
    if not recurring:
        # auto-cleanup after firing: stop+disable timer, remove unit files, reload daemon to purge cache
        service += f"ExecStartPost=/bin/bash -c 'systemctl --user disable --now {unit_name}.timer 2>/dev/null; rm -f {UNIT_DIR}/{unit_name}.timer {UNIT_DIR}/{unit_name}.service; systemctl --user daemon-reload'\n"

    # Timer unit
    timer = f"""[Unit]
Description=agent-cron timer: {name}

[Timer]
OnCalendar={on_calendar}
Persistent={'true' if recurring else 'false'}
{'AccuracySec=1s' if not recurring else 'AccuracySec=1min'}
Unit={unit_name}.service

[Install]
WantedBy=timers.target
"""

    UNIT_DIR.mkdir(parents=True, exist_ok=True)
    service_path = UNIT_DIR / f"{unit_name}.service"
    timer_path = UNIT_DIR / f"{unit_name}.timer"
    service_path.write_text(service)
    timer_path.write_text(timer)

    # daemon-reload + enable + start
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(
        ["systemctl", "--user", "enable", "--now", f"{unit_name}.timer"],
        check=True,
        capture_output=True,
    )

    print(json.dumps({
        "id": name,
        "unit": f"{unit_name}.timer",
        "on_calendar": on_calendar,
        "recurring": recurring,
        "command": args.command,
        "next_fire": next_fire.strip(),
    }, indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List all agent-cron timers."""
    if not UNIT_DIR.exists():
        return 0

    timers = sorted(UNIT_DIR.glob(f"{PREFIX}*.timer"))
    if not timers:
        return 0

    for timer_path in timers:
        unit_name = timer_path.stem
        # parse OnCalendar from file
        on_calendar = ""
        for line in timer_path.read_text().splitlines():
            if line.startswith("OnCalendar="):
                on_calendar = line.split("=", 1)[1]
                break
        # parse command from .service
        service_path = UNIT_DIR / f"{unit_name}.service"
        command = ""
        if service_path.exists():
            for line in service_path.read_text().splitlines():
                if line.startswith("ExecStart="):
                    command = line.split("=", 1)[1]
                    break
        # active state
        proc = subprocess.run(
            ["systemctl", "--user", "is-active", f"{unit_name}.timer"],
            capture_output=True,
            text=True,
        )
        state = proc.stdout.strip()
        # next fire
        proc = subprocess.run(
            ["systemctl", "--user", "list-timers", f"{unit_name}.timer", "--no-pager"],
            capture_output=True,
            text=True,
        )
        next_fire_lines = [l for l in proc.stdout.splitlines() if unit_name in l]
        next_fire = next_fire_lines[0] if next_fire_lines else ""

        name = unit_name[len(PREFIX):]
        print(f"{name}  [{state}]  {on_calendar}")
        if next_fire:
            print(f"  next: {next_fire.strip()}")
        if command and not args.short:
            print(f"  cmd:  {command}")
    return 0


def cmd_rm(args: argparse.Namespace) -> int:
    """Remove a timer."""
    name = _slug(args.name)
    unit_name = f"{PREFIX}{name}"
    timer_path = UNIT_DIR / f"{unit_name}.timer"
    service_path = UNIT_DIR / f"{unit_name}.service"

    if not timer_path.exists() and not service_path.exists():
        sys.stderr.write(f"ERROR: no agent-cron timer named {name!r}\n")
        return 2

    subprocess.run(
        ["systemctl", "--user", "disable", "--now", f"{unit_name}.timer"],
        capture_output=True,
    )
    timer_path.unlink(missing_ok=True)
    service_path.unlink(missing_ok=True)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    print(f"removed: {name}")
    return 0


def _shell_quote(s: str) -> str:
    """Wrap arg in single quotes, escape single quotes inside."""
    return "'" + s.replace("'", "'\\''") + "'"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Persistent reminders via systemd --user timers.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="create a timer")
    add.add_argument("--at", help="one-shot ISO datetime, e.g. '2026-04-30 21:00'")
    add.add_argument("--on-calendar", help="recurring systemd OnCalendar spec, e.g. 'Mon..Fri 09:00'")
    add.add_argument("--command", required=True, help="shell command to run")
    add.add_argument("--name", help="optional human name; auto-generated if omitted")
    add.add_argument(
        "--env-file",
        help="optional path to env file (e.g. ~/.env.global) injected as EnvironmentFile=",
    )
    add.set_defaults(func=cmd_add)

    lst = sub.add_parser("list", help="list timers")
    lst.add_argument("--short", action="store_true", help="omit command line")
    lst.set_defaults(func=cmd_list)

    rm = sub.add_parser("rm", help="remove a timer")
    rm.add_argument("name", help="timer name (slug, no prefix)")
    rm.set_defaults(func=cmd_rm)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
