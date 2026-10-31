import json
import sys
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

FESTIVAL_DAY_CHANGE = timedelta(hours=6)
GAP = timedelta(minutes=30)
DATA_PATH = Path("data/festival.json")


def to_slug(name: str) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = "".join(c if c.isalnum() or c.isspace() else " " for c in text)
    return "-".join(text.split())


def start_of(perf: dict) -> datetime:
    return datetime.fromisoformat(perf["start"])


def end_of(perf: dict) -> datetime:
    return start_of(perf) + timedelta(minutes=perf["duration_minutes"])


def festival_day(perf: dict) -> date:
    return (start_of(perf) - FESTIVAL_DAY_CHANGE).date()


def too_close(
    start1: datetime, end1: datetime, start2: datetime, end2: datetime
) -> bool:
    return start1 < end2 + GAP and start2 < end1 + GAP


def role_of(perf: dict, artist_slug: str) -> str:
    if perf["kind"] == "solo" and to_slug(perf.get("artist", "")) == artist_slug:
        return "solo"
    if to_slug(perf.get("host", "")) == artist_slug:
        return "host"
    if to_slug(perf.get("teacher", "")) == artist_slug:
        return "teacher"
    if artist_slug in [to_slug(act) for act in perf.get("acts", [])]:
        return "act"
    return ""


def parse_day(text: str) -> date:
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        raise ValueError(f"'{text.strip()}' is not a day, use YYYY-MM-DD.") from None


def parse_moment(text: str) -> datetime:
    try:
        return datetime.fromisoformat(text.strip())
    except ValueError:
        raise ValueError(
            f"'{text.strip()}' is not a moment, use YYYY-MM-DDTHH:MM."
        ) from None


def parse_minutes(text: str) -> int:
    try:
        minutes = int(text.strip())
    except ValueError:
        raise ValueError(f"'{text.strip()}' is not a number of minutes.") from None
    if not 1 <= minutes <= 360:
        raise ValueError(f"'{text.strip()}' is not between 1 and 360 minutes.")
    return minutes


def load_data() -> dict:
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"Data file not found: {DATA_PATH}.") from None
    except json.JSONDecodeError as error:
        raise ValueError(f"Data file is damaged: {error}.") from None


def save_data(data: dict) -> None:
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def venue_names(data: dict) -> dict[str, str]:
    return {to_slug(v["name"]): v["name"] for v in data["venues"]}


def artist_name(slug: str, data: dict) -> str:
    for artist in data["artists"]:
        if to_slug(artist["name"]) == slug:
            return artist["name"]
    return " ".join(word.capitalize() for word in slug.split("-"))


def perf_id(perf: dict) -> str:
    return f"{perf['venue']}-{start_of(perf):%Y-%m-%d-%H%M}"


def find_performance(data: dict, wanted: str) -> dict | None:
    for perf in data["performances"]:
        if perf_id(perf) == wanted:
            return perf
    return None


def check_performance(
    data: dict,
    artist_slug: str,
    venue_slug: str,
    start: datetime,
    minutes: int,
) -> str:
    names = venue_names(data)
    if venue_slug not in names:
        raise ValueError(f"Unknown venue '{venue_slug}'.")
    artist = None
    for candidate in data["artists"]:
        if to_slug(candidate["name"]) == artist_slug:
            artist = candidate["name"]
            break
    if artist is None:
        raise ValueError(f"Unknown artist '{artist_slug}'.")
    first = date.fromisoformat(data["first_day"])
    last = date.fromisoformat(data["last_day"])
    if not first <= start.date() <= last:
        raise ValueError(f"{start.date().isoformat()} is not a day of the festival.")
    end = start + timedelta(minutes=minutes)
    for perf in data["performances"]:
        if perf["venue"] == venue_slug and too_close(
            start, end, start_of(perf), end_of(perf)
        ):
            raise ValueError(
                f"{names[venue_slug]} is busy with {perf['title']}"
                f" ({start_of(perf):%Y-%m-%d %H:%M}-{end_of(perf):%H:%M})."
            )
    for perf in data["performances"]:
        if role_of(perf, artist_slug) and too_close(
            start, end, start_of(perf), end_of(perf)
        ):
            raise ValueError(f"{artist} is on stage in {perf['title']}.")
    return artist


def show_summary(data: dict) -> None:
    print(data["name"])
    print(f"From {data['first_day']} to {data['last_day']}")
    print(
        f"{len(data['venues'])} venues, "
        f"{len(data['artists'])} artists, "
        f"{len(data['performances'])} performances"
    )


def show_venues(data: dict) -> None:
    total = 0
    for venue in data["venues"]:
        print(f"{to_slug(venue['name'])}: {venue['name']}, {venue['capacity']} seats")
        total += venue["capacity"]
    print(f"Total: {total} seats")


def show_programme(data: dict, day_text: str) -> None:
    wanted = parse_day(day_text)
    names = venue_names(data)
    shows = [p for p in data["performances"] if festival_day(p) == wanted]
    if not shows:
        days = sorted({festival_day(p).isoformat() for p in data["performances"]})
        print(f"No performances on: '{day_text}'. Days: {', '.join(days)}")
        return
    print(f"Programme for {wanted:%A %d %B}:")
    for perf in sorted(shows, key=start_of):
        venue = names.get(perf["venue"], perf["venue"])
        print(
            f"{start_of(perf):%H:%M}-{end_of(perf):%H:%M}"
            f" | {venue} | {perf['title']} ({perf['kind']})"
        )


def show_artist(data: dict, artist_slug: str) -> None:
    shows = [p for p in data["performances"] if role_of(p, artist_slug)]
    if not shows:
        print(f"No artist '{artist_slug}'.")
        return
    names = venue_names(data)
    print(artist_name(artist_slug, data))
    for perf in shows:
        venue = names.get(perf["venue"], perf["venue"])
        print(
            f"{festival_day(perf):%a %d} {start_of(perf):%H:%M}-{end_of(perf):%H:%M}"
            f" | {venue} | {perf['title']} ({role_of(perf, artist_slug)})"
        )


def show_now(data: dict, moment_text: str) -> None:
    at = parse_moment(moment_text)
    names = venue_names(data)
    print(f"On stage at {at:%Y-%m-%d %H:%M}:")
    for perf in sorted(
        [p for p in data["performances"] if start_of(p) <= at < end_of(p)],
        key=start_of,
    ):
        venue = names.get(perf["venue"], perf["venue"])
        print(f"- {perf['title']} at {venue}, until {end_of(perf):%H:%M}")
    print("Up next:")
    for perf in sorted(
        [p for p in data["performances"] if start_of(p) > at], key=start_of
    )[:3]:
        venue = names.get(perf["venue"], perf["venue"])
        print(
            f"- {start_of(perf):%H:%M}-{end_of(perf):%H:%M}"
            f" | {venue} | {perf['title']} ({perf['kind']})"
        )


def show_add(data: dict) -> None:
    title = input("Title: ")
    artist_slug = input("Artist (slug): ").strip()
    venue_slug = input("Venue (slug): ").strip()
    start = parse_moment(input("Start (YYYY-MM-DDTHH:MM): "))
    minutes = parse_minutes(input("Duration (minutes): "))
    check_performance(data, artist_slug, venue_slug, start, minutes)
    perf = {
        "kind": "solo",
        "title": title,
        "venue": venue_slug,
        "start": f"{start:%Y-%m-%dT%H:%M}",
        "duration_minutes": minutes,
        "artist": artist_slug,
        "min_age": 0,
        "description": "",
    }
    data["performances"].append(perf)
    save_data(data)
    print(f"Added: {perf_id(perf)}")


def show_cancel(data: dict, wanted: str) -> None:
    perf = find_performance(data, wanted.strip())
    if perf is None:
        raise ValueError(f"No performance '{wanted.strip()}'.")
    data["performances"].remove(perf)
    save_data(data)
    print(f"Cancelled: {perf['title']}")


def show_usage() -> None:
    print("Usage:")
    print("  main.py")
    print("  main.py venues")
    print("  main.py programme YYYY-MM-DD")
    print("  main.py artist SLUG")
    print("  main.py now YYYY-MM-DDTHH:MM")
    print("  main.py add")
    print("  main.py cancel ID")


def main() -> None:
    try:
        data = load_data()
        if len(sys.argv) < 2:
            show_summary(data)
        elif sys.argv[1] == "venues":
            show_venues(data)
        elif sys.argv[1] == "programme":
            if len(sys.argv) < 3:
                show_usage()
            else:
                show_programme(data, sys.argv[2])
        elif sys.argv[1] == "artist":
            if len(sys.argv) < 3:
                show_usage()
            else:
                show_artist(data, sys.argv[2])
        elif sys.argv[1] == "now":
            if len(sys.argv) < 3:
                show_usage()
            else:
                show_now(data, sys.argv[2])
        elif sys.argv[1] == "add":
            show_add(data)
        elif sys.argv[1] == "cancel":
            if len(sys.argv) < 3:
                show_usage()
            else:
                show_cancel(data, sys.argv[2])
        else:
            show_usage()
    except ValueError as error:
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
