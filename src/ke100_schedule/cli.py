"""CLI entry point for ke100-schedule."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from ke100_schedule.config import load_credentials
from ke100_schedule.display import format_segment_rules
from ke100_schedule.expand import expand_warm_blocks
from ke100_schedule.hub import connect
from ke100_schedule.read_cmds import read_all_children, read_room_schedule
from ke100_schedule.spec import load_spec
from ke100_schedule.write_cmds import find_child_by_alias, write_schedule


def _cmd_list(args: argparse.Namespace) -> int:
    async def run() -> int:
        creds = load_credentials()
        hub = await connect(creds)
        try:
            if not hub.children:
                print("No child devices on hub.")
                return 0
            for child in hub.children:
                print(f"{child.alias}\t{child.device_id}")
            return 0
        finally:
            await hub.disconnect()

    return asyncio.run(run())


def _cmd_read(args: argparse.Namespace) -> int:
    async def run() -> int:
        creds = load_credentials()
        hub = await connect(creds)
        try:
            if args.room:
                child = find_child_by_alias(hub, args.room)
                data = await read_room_schedule(hub, child.device_id, child.alias)
                dump = {child.alias: data}
            else:
                dump = await read_all_children(hub)

            for alias, room_data in dump.items():
                if "error" in room_data:
                    print(f"=== {alias}: ERROR {room_data['error']}")
                    continue
                info = room_data["info"]
                print(
                    f"=== {alias}: enabled={info.get('enable')} mode={info.get('mode')} "
                    f"device_id={room_data['device_id']}"
                )
                for segment in room_data.get("schedule_list") or []:
                    seg_name = segment.get("id", "").split(":", 1)[-1]
                    print(f"  [{seg_name}]")
                    for line in format_segment_rules(segment.get("rule_list") or []):
                        print(line)

            out_path = Path("schedules.json")
            text = json.dumps(dump, ensure_ascii=False, indent=2) + "\n"
            out_path.write_text(text, encoding="utf-8")

            if args.json:
                print(json.dumps(dump, ensure_ascii=False, indent=2))
            else:
                print(f"\nWrote {out_path}")
            return 0
        finally:
            await hub.disconnect()

    return asyncio.run(run())


def _cmd_write(args: argparse.Namespace) -> int:
    async def run() -> int:
        creds = load_credentials()
        spec = load_spec(args.spec)
        if "room" not in spec:
            sys.exit("SPEC must include \"room\" matching a child alias.")
        try:
            from ke100_schedule.spec import validate_spec

            validate_spec(spec)
        except Exception as exc:
            sys.exit(f"VALIDATION FAILED: {exc}")

        hub = await connect(creds)
        try:
            await write_schedule(hub, spec, apply=args.apply)
            return 0
        finally:
            await hub.disconnect()

    return asyncio.run(run())


def _cmd_expand(args: argparse.Namespace) -> int:
    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    warm = [(str(a), str(b), float(c)) for a, b, c in raw["warm_blocks"]]
    default = float(raw.get("default_temp", args.default_temp))
    blocks = expand_warm_blocks(warm, default)
    print(json.dumps(blocks, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ke100-schedule",
        description="Read/write Tapo KE100 Smart Control schedules via a KH100 hub.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="List KE100 children and device IDs")
    list_p.set_defaults(func=_cmd_list)

    read_p = sub.add_parser("read", help="Read schedule(s) from the hub")
    read_p.add_argument("--room", help="Child alias (default: all rooms)")
    read_p.add_argument("--json", action="store_true", help="Also print JSON to stdout")
    read_p.set_defaults(func=_cmd_read)

    write_p = sub.add_parser("write", help="Validate and optionally apply a schedule spec")
    write_p.add_argument("spec", type=Path, help="Path to schedule JSON spec")
    write_p.add_argument(
        "--apply",
        action="store_true",
        help="Send requests to the hub (default: dry-run only)",
    )
    write_p.set_defaults(func=_cmd_write)

    expand_p = sub.add_parser(
        "expand-warm",
        help="Expand warm-only blocks into a full day",
    )
    expand_p.add_argument("input", type=Path)
    expand_p.add_argument("--default-temp", type=float, default=16.0)
    expand_p.set_defaults(func=_cmd_expand)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
