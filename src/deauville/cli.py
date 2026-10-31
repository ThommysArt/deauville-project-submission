import argparse
import sys
from pathlib import Path

from .errors import FestivalError, InvalidError
from .festival import Festival
from .storage import JsonStorage
from .times import parse_day, parse_moment

DEFAULT_DATA = Path("data/festival.json")


def show_summary(festival: Festival) -> None:
    print(festival.name)
    print(f"From {festival.first_day.isoformat()} to {festival.last_day.isoformat()}")
    print(
        f"{len(festival.venues)} venues, {len(festival.artists)} artists, "
        f"{len(festival.performances)} performances"
    )


def show_venues(festival: Festival) -> None:
    for venue in festival.venues:
        print(f"{venue.slug}: {venue.name}, {venue.capacity} seats")
    print(f"Total: {sum(v.capacity for v in festival.venues)} seats")


def show_programme(festival: Festival, day_text: str) -> None:
    day = parse_day(day_text)
    if day not in festival.days:
        days = ", ".join(d.isoformat() for d in festival.days)
        raise InvalidError(f"No performance on '{day_text}'. Days: {days}")
    print(f"Programme for {day:%A %d %B}:")
    for performance in festival.programme(day):
        print(performance)


def show_artist(festival: Festival, slug: str) -> None:
    artist = festival.artist(slug)
    print(artist.name)
    for performance in festival.performances_of(slug):
        print(
            f"{performance.festival_day:%a %d} {performance.start:%H:%M}-"
            f"{performance.end:%H:%M} | {performance.venue.name} | "
            f"{performance.title} ({performance.role_of(slug)})"
        )


def show_now(festival: Festival, moment_text: str) -> None:
    at = parse_moment(moment_text)
    print(f"On stage at {at:%Y-%m-%d %H:%M}:")
    for performance in festival.on_stage(at):
        print(f"- {performance.title} at {performance.venue.name}, until {performance.end:%H:%M}")
    print("Up next:")
    for performance in festival.up_next(at):
        print(f"- {performance}")


def do_add(festival: Festival) -> None:
    record = {
        "kind": "solo",
        "title": input("Title: ").strip(),
        "artist": input("Artist (slug): ").strip(),
        "venue": input("Venue (slug): ").strip(),
        "start": input("Start (YYYY-MM-DDTHH:MM): ").strip(),
        "duration_minutes": input("Duration (minutes): ").strip(),
    }
    added = festival.add_from_record(record)
    print(f"Added: {added.id}")


def do_cancel(festival: Festival, performance_id: str) -> None:
    print(f"Cancelled: {festival.cancel(performance_id).title}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deauville", description="Deauville Festival du Rire")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("venues")
    sub.add_parser("add")
    p = sub.add_parser("programme")
    p.add_argument("day")
    p = sub.add_parser("artist")
    p.add_argument("slug")
    p = sub.add_parser("now")
    p.add_argument("moment")
    p = sub.add_parser("cancel")
    p.add_argument("id")
    p = sub.add_parser("serve")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--web", type=Path, default=Path("web"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    storage = JsonStorage(args.data)
    try:
        if args.command == "serve":
            import uvicorn

            from .api import create_app

            uvicorn.run(create_app(storage, args.web), host=args.host, port=args.port)
            return 0
        festival = Festival.open(storage)
        if args.command is None:
            show_summary(festival)
        elif args.command == "venues":
            show_venues(festival)
        elif args.command == "programme":
            show_programme(festival, args.day)
        elif args.command == "artist":
            show_artist(festival, args.slug)
        elif args.command == "now":
            show_now(festival, args.moment)
        elif args.command == "add":
            do_add(festival)
        elif args.command == "cancel":
            do_cancel(festival, args.id)
    except FestivalError as error:
        print(f"Error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
