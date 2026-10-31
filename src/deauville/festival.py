from collections.abc import Callable
from datetime import date, datetime, timedelta

from .errors import ConflictError, InvalidError, NotFoundError, StorageError
from .models import Artist, Performance, Venue, Workshop, performance_from_record
from .storage import Storage
from .times import parse_day, too_close


class Festival:
    def __init__(
        self,
        name: str,
        first_day: date,
        last_day: date,
        venues: list[Venue],
        artists: list[Artist],
        storage: Storage | None = None,
    ) -> None:
        if last_day < first_day:
            raise InvalidError("The festival ends before it starts.")
        self.name = name
        self.first_day = first_day
        self.last_day = last_day
        self._venues = {v.slug: v for v in venues}
        self._artists = {a.slug: a for a in artists}
        self._performances: dict[str, Performance] = {}
        self._storage = storage

    @classmethod
    def open(cls, storage: Storage) -> "Festival":
        data = storage.load()
        try:
            festival = cls(
                data["name"],
                parse_day(data["first_day"]),
                parse_day(data["last_day"]),
                [Venue(v["name"], v["capacity"], v.get("address", "")) for v in data["venues"]],
                [
                    Artist(a["name"], a.get("bio", ""), a.get("photo_url", ""))
                    for a in data["artists"]
                ],
            )
            for record in data["performances"]:
                festival.add_performance(performance_from_record(record, festival._venues))
        except KeyError as error:
            raise StorageError(f"The data file lacks the field {error}.") from None
        festival._storage = storage
        return festival

    def to_data(self) -> dict:
        return {
            "name": self.name,
            "first_day": self.first_day.isoformat(),
            "last_day": self.last_day.isoformat(),
            "venues": [
                {"name": v.name, "capacity": v.capacity, "address": v.address}
                for v in self._venues.values()
            ],
            "artists": [a.to_record() for a in self._artists.values()],
            "performances": [p.to_record() for p in sorted(self._performances.values())],
        }

    @property
    def days(self) -> list[date]:
        count = (self.last_day - self.first_day).days + 1
        return [self.first_day + timedelta(days=i) for i in range(count)]

    @property
    def venues(self) -> list[Venue]:
        return list(self._venues.values())

    @property
    def artists(self) -> list[Artist]:
        return sorted(self._artists.values())

    @property
    def artist_names(self) -> dict[str, Artist]:
        return dict(self._artists)

    @property
    def performances(self) -> list[Performance]:
        return sorted(self._performances.values())

    def venue(self, slug: str) -> Venue:
        if slug not in self._venues:
            raise NotFoundError(f"No venue '{slug}'.")
        return self._venues[slug]

    def artist(self, slug: str) -> Artist:
        if slug not in self._artists:
            raise NotFoundError(f"No artist '{slug}'.")
        return self._artists[slug]

    def performance(self, performance_id: str) -> Performance:
        if performance_id not in self._performances:
            raise NotFoundError(f"No performance '{performance_id}'.")
        return self._performances[performance_id]

    def programme(self, day: date, venue_slug: str | None = None) -> list[Performance]:
        if venue_slug is not None:
            self.venue(venue_slug)
        return [
            p
            for p in self.performances
            if p.festival_day == day and (venue_slug is None or p.venue.slug == venue_slug)
        ]

    def performances_of(self, artist_slug: str) -> list[Performance]:
        self.artist(artist_slug)
        return [p for p in self.performances if p.involves(artist_slug)]

    def on_stage(self, at: datetime) -> list[Performance]:
        return [p for p in self.performances if p.is_on_stage(at)]

    def up_next(self, at: datetime, limit: int = 3) -> list[Performance]:
        return [p for p in self.performances if p.start > at][:limit]

    def check(self, new: Performance, ignore_id: str | None = None) -> None:
        if new.venue.slug not in self._venues:
            raise NotFoundError(f"Unknown venue '{new.venue.slug}'.")
        for slug in new.artist_slugs():
            if slug not in self._artists:
                raise NotFoundError(f"Unknown artist '{slug}'.")
        if not self.first_day <= new.festival_day <= self.last_day:
            raise InvalidError(f"{new.festival_day.isoformat()} is not a day of the festival.")
        others = [p for p in self._performances.values() if p.id != ignore_id]
        for other in others:
            if other.venue.slug == new.venue.slug and too_close(
                new.start, new.end, other.start, other.end
            ):
                raise ConflictError(
                    f"{new.venue.name} is busy with {other.title} "
                    f"({other.start:%Y-%m-%d %H:%M}-{other.end:%H:%M})."
                )
        for slug in new.artist_slugs():
            for other in others:
                if other.involves(slug) and too_close(new.start, new.end, other.start, other.end):
                    raise ConflictError(f"{self._artists[slug].name} is on stage in {other.title}.")

    def _commit(self, change: Callable[[], None]) -> None:
        before = dict(self._performances), dict(self._artists)
        change()
        if self._storage is not None:
            try:
                self._storage.save(self.to_data())
            except StorageError:
                self._performances, self._artists = before
                raise

    def add_performance(self, new: Performance) -> Performance:
        self.check(new)
        if new.id in self._performances:
            raise ConflictError(f"{new.id} already exists.")
        self._commit(lambda: self._performances.__setitem__(new.id, new))
        return new

    def add_from_record(self, record: dict) -> Performance:
        return self.add_performance(performance_from_record(record, self._venues))

    def replace_performance(self, performance_id: str, record: dict) -> Performance:
        old = self.performance(performance_id)
        new = performance_from_record({**old.to_record(), **record}, self._venues)
        self.check(new, ignore_id=old.id)

        def swap() -> None:
            del self._performances[old.id]
            self._performances[new.id] = new

        self._commit(swap)
        return new

    def cancel(self, performance_id: str) -> Performance:
        old = self.performance(performance_id)
        self._commit(lambda: self._performances.__delitem__(old.id))
        return old

    def register(self, performance_id: str, name: str) -> Workshop:
        workshop = self.performance(performance_id)
        if not isinstance(workshop, Workshop):
            raise InvalidError(f"{workshop.title} is not a workshop.")
        snapshot = workshop.participants
        workshop.register(name)
        try:
            self._commit(lambda: None)
        except StorageError:
            workshop._participants[:] = snapshot
            raise
        return workshop

    def add_artist(self, name: str, bio: str = "", photo_url: str = "") -> Artist:
        artist = Artist(name, bio, photo_url)
        if artist.slug in self._artists:
            raise ConflictError(f"Artist '{artist.slug}' already exists.")
        self._commit(lambda: self._artists.__setitem__(artist.slug, artist))
        return artist
