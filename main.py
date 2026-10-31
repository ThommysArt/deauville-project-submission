import json

with open("data/festival.json", encoding="utf-8") as f:
    festival = json.load(f)

print(festival["name"])
print(f"From {festival['first_day']} to {festival['last_day']}")
print(
    f"{len(festival['venues'])} venues, "
    f"{len(festival['artists'])} artists, "
    f"{len(festival['performances'])} performances"
)

print("\nVenues:")
total_seats = 0
for venue in festival["venues"]:
    print(f"- {venue['name']}: {venue['capacity']} seats ({venue['address']})")
    total_seats += venue["capacity"]
print(f"Total: {total_seats} seats")

counts: dict[str, int] = {}
for perf in festival["performances"]:
    counts[perf["kind"]] = counts.get(perf["kind"], 0) + 1
for kind, count in counts.items():
    print(f"{kind}: {count}")

venue_names = {}
for venue in festival["venues"]:
    slug = (
        venue["name"]
        .lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("â", "a")
        .replace("ù", "u")
        .replace("û", "u")
        .replace("ô", "o")
        .replace("î", "i")
        .replace("ç", "c")
        .replace(" ", "-")
    )
    venue_names[slug] = venue["name"]

print("\nAt Le Kiosque:")
for perf in festival["performances"]:
    if perf["venue"] == "le-kiosque":
        print(f"- {perf['start']} {perf['title']}")

longest = festival["performances"][0]
for perf in festival["performances"]:
    if perf["duration_minutes"] > longest["duration_minutes"]:
        longest = perf
print(f"\nLongest: {longest['title']} ({longest['duration_minutes']} min)")

for perf in festival["performances"]:
    if perf["kind"] == "workshop":
        day = perf["start"][:10]
        taken = len(perf["participants"])
        print(
            f"{perf['title']} on {day}: "
            f"{taken}/{perf['max_participants']} registered"
        )

stage_counts: dict[str, int] = {}
for perf in festival["performances"]:
    people: list[str] = []
    if perf["kind"] == "solo":
        people.append(perf["artist"])
    elif perf["kind"] == "lineup":
        people.append(perf["host"])
        people.extend(perf["acts"])
    elif perf["kind"] == "workshop":
        people.append(perf["teacher"])
    for slug in people:
        stage_counts[slug] = stage_counts.get(slug, 0) + 1

most = max(stage_counts.values())
top = [slug for slug, n in stage_counts.items() if n == most]
print(f"\nOn stage {most} times: {', '.join(top)}")

days = sorted({perf["start"][:10] for perf in festival["performances"]})
day = ""
while day not in days:
    day = input("Day (YYYY-MM-DD): ").strip()
    if day not in days:
        print(f"No performance on '{day}'. Days: {', '.join(days)}")

print(f"Programme for {day}:")
for perf in festival["performances"]:
    if perf["start"][:10] == day:
        time = perf["start"][11:]
        venue = venue_names.get(perf["venue"], perf["venue"])
        print(f"{time} | {venue} | {perf['title']} ({perf['kind']})")
