from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import ClassVar

from .errors import ConflictError, InvalidError, NotFoundError
from .slugs import to_slug
from .times import MAX_MINUTES, MIN_MINUTES, festival_day_of, parse_minutes, parse_moment


@dataclass(frozen=True)
class Venue:
    name: str
    capacity: int
    address: str = ""

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise InvalidError(f"{self.name} needs at least one seat.")

    @property
    def slug(self) -> str:
        return to_slug(self.name)

    def to_view(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "capacity": self.capacity,
            "address": self.address,
        }


class Artist:
    def __init__(self, name: str, bio: str = "", photo_url: str = "") -> None:
        name = name.strip()
        if not to_slug(name):
            raise InvalidError("An artist needs a name.")
        self.name = name
        self.bio = bio
        self.photo_url = photo_url

    @property
    def slug(self) -> str:
        return to_slug(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Artist):
            return NotImplemented
        return self.slug == other.slug

    def __hash__(self) -> int:
        return hash(self.slug)

    def __lt__(self, other: "Artist") -> bool:
        return self.slug < other.slug

    def __str__(self) -> str:
        return self.name

    def to_view(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "bio": self.bio,
            "photo_url": self.photo_url,
        }

    def to_record(self) -> dict:
        return {"name": self.name, "bio": self.bio, "photo_url": self.photo_url}


def _require(record: dict, *keys: str) -> None:
    for key in keys:
        if key not in record:
            raise InvalidError(f"Missing field '{key}'.")


class Performance(ABC):
    kind: ClassVar[str] = ""

    def __init__(
        self,
        title: str,
        venue: Venue,
        start: datetime,
        duration_minutes: int,
        description: str = "",
    ) -> None:
        if not title.strip():
            raise InvalidError("A performance needs a title.")
        if not MIN_MINUTES <= duration_minutes <= MAX_MINUTES:
            raise InvalidError(
                f"A performance lasts from {MIN_MINUTES} to {MAX_MINUTES} "
                f"minutes, got {duration_minutes}."
            )
        self.title = title.strip()
        self.venue = venue
        self.start = start
        self.duration_minutes = duration_minutes
        self.description = description

    @property
    def end(self) -> datetime:
        return self.start + timedelta(minutes=self.duration_minutes)

    @property
    def festival_day(self) -> date:
        return festival_day_of(self.start)

    @property
    def id(self) -> str:
        return f"{self.venue.slug}-{self.start:%Y-%m-%d-%H%M}"

    @property
    def capacity(self) -> int:
        return self.venue.capacity

    @abstractmethod
    def roles(self) -> dict[str, str]: ...

    @abstractmethod
    def summary(self, artists: dict[str, Artist]) -> str: ...

    @abstractmethod
    def _extra_view(self) -> dict: ...

    @abstractmethod
    def _extra_record(self) -> dict: ...

    @classmethod
    @abstractmethod
    def from_record(cls, record: dict, venue: Venue) -> "Performance": ...

    def artist_slugs(self) -> list[str]:
        return list(self.roles())

    def role_of(self, slug: str) -> str:
        return self.roles().get(slug, "")

    def involves(self, slug: str) -> bool:
        return slug in self.roles()

    def is_on_stage(self, at: datetime) -> bool:
        return self.start <= at < self.end

    def to_record(self) -> dict:
        record = {
            "kind": self.kind,
            "title": self.title,
            "venue": self.venue.slug,
            "start": self.start.isoformat(timespec="minutes"),
            "duration_minutes": self.duration_minutes,
            "description": self.description,
        }
        record.update(self._extra_record())
        return record

    def to_view(self, artists: dict[str, Artist]) -> dict:
        view = {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "venue": self.venue.slug,
            "venue_name": self.venue.name,
            "start": self.start.isoformat(timespec="minutes"),
            "end": self.end.isoformat(timespec="minutes"),
            "duration_minutes": self.duration_minutes,
            "festival_day": self.festival_day.isoformat(),
            "description": self.description,
            "summary": self.summary(artists),
            "capacity": self.capacity,
        }
        view.update(self._extra_view())
        view["artists"] = [
            {"slug": slug, "name": artists[slug].name if slug in artists else slug}
            for slug in self.roles()
        ]
        return view

    def __lt__(self, other: "Performance") -> bool:
        return (self.start, self.venue.name) < (other.start, other.venue.name)

    def __str__(self) -> str:
        return (
            f"{self.start:%H:%M}-{self.end:%H:%M} | {self.venue.name} | {self.title} ({self.kind})"
        )


def _name(artists: dict[str, Artist], slug: str) -> str:
    return artists[slug].name if slug in artists else slug


class SoloShow(Performance):
    kind = "solo"

    def __init__(
        self,
        title: str,
        venue: Venue,
        start: datetime,
        duration_minutes: int,
        artist: str,
        min_age: int = 0,
        description: str = "",
    ) -> None:
        super().__init__(title, venue, start, duration_minutes, description)
        if not 0 <= min_age <= 18:
            raise InvalidError(f"The minimum age is from 0 to 18, got {min_age}.")
        self.artist = artist
        self.min_age = min_age

    def roles(self) -> dict[str, str]:
        return {self.artist: "solo"}

    def summary(self, artists: dict[str, Artist]) -> str:
        return _name(artists, self.artist)

    def _extra_view(self) -> dict:
        return {"artist": self.artist, "min_age": self.min_age}

    def _extra_record(self) -> dict:
        return {"artist": self.artist, "min_age": self.min_age}

    @classmethod
    def from_record(cls, record: dict, venue: Venue) -> "SoloShow":
        _require(record, "title", "start", "duration_minutes", "artist")
        return cls(
            record["title"],
            venue,
            parse_moment(record["start"]),
            parse_minutes(record["duration_minutes"]),
            record["artist"],
            int(record.get("min_age", 0)),
            record.get("description", ""),
        )


class Lineup(Performance):
    kind = "lineup"
    MINUTES_PER_ACT = 10
    MINUTES_FOR_HOST = 3

    def __init__(
        self,
        title: str,
        venue: Venue,
        start: datetime,
        duration_minutes: int,
        host: str,
        acts: list[str],
        description: str = "",
    ) -> None:
        super().__init__(title, venue, start, duration_minutes, description)
        if len(acts) < 2:
            raise InvalidError("A lineup needs at least two acts.")
        if len(set(acts)) != len(acts):
            raise InvalidError("An act cannot appear twice in a lineup.")
        if host in acts:
            raise InvalidError("The host of a lineup cannot also be one of its acts.")
        needed = self.MINUTES_PER_ACT * len(acts) + self.MINUTES_FOR_HOST * (len(acts) - 1)
        if duration_minutes < needed:
            raise InvalidError(
                f"A lineup of {len(acts)} acts lasts at least {needed} minutes, "
                f"got {duration_minutes}."
            )
        self.host = host
        self._acts = list(acts)

    @property
    def acts(self) -> list[str]:
        return list(self._acts)

    def roles(self) -> dict[str, str]:
        roles = {self.host: "host"}
        roles.update({slug: "act" for slug in self._acts})
        return roles

    def summary(self, artists: dict[str, Artist]) -> str:
        acts = ", ".join(_name(artists, slug) for slug in self._acts)
        return f"hosted by {_name(artists, self.host)}, with {acts}"

    def _extra_view(self) -> dict:
        return {"host": self.host, "acts": self.acts}

    def _extra_record(self) -> dict:
        return {"host": self.host, "acts": self.acts}

    @classmethod
    def from_record(cls, record: dict, venue: Venue) -> "Lineup":
        _require(record, "title", "start", "duration_minutes", "host", "acts")
        return cls(
            record["title"],
            venue,
            parse_moment(record["start"]),
            parse_minutes(record["duration_minutes"]),
            record["host"],
            list(record["acts"]),
            record.get("description", ""),
        )


class Workshop(Performance):
    kind = "workshop"

    def __init__(
        self,
        title: str,
        venue: Venue,
        start: datetime,
        duration_minutes: int,
        teacher: str,
        max_participants: int,
        participants: list[str] | None = None,
        description: str = "",
    ) -> None:
        super().__init__(title, venue, start, duration_minutes, description)
        if max_participants < 1:
            raise InvalidError("A workshop needs at least one place.")
        self.teacher = teacher
        self.max_participants = max_participants
        self._participants: list[str] = []
        for name in participants or []:
            self.register(name)

    @property
    def places(self) -> int:
        return min(self.max_participants, self.venue.capacity)

    @property
    def capacity(self) -> int:
        return self.places

    @property
    def participants(self) -> list[str]:
        return list(self._participants)

    @property
    def places_left(self) -> int:
        return self.places - len(self._participants)

    def register(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise InvalidError("A participant needs a name.")
        if name.lower() in (p.lower() for p in self._participants):
            raise ConflictError(f"{name} is already registered in {self.title}.")
        if self.places_left < 1:
            raise ConflictError(f"{self.title} is full ({self.places} places).")
        self._participants.append(name)

    def roles(self) -> dict[str, str]:
        return {self.teacher: "teacher"}

    def summary(self, artists: dict[str, Artist]) -> str:
        taken = len(self._participants)
        return f"with {_name(artists, self.teacher)}, {taken}/{self.places} places taken"

    def _extra_view(self) -> dict:
        return {
            "teacher": self.teacher,
            "max_participants": self.max_participants,
            "participants": self.participants,
            "places_left": self.places_left,
        }

    def _extra_record(self) -> dict:
        return {
            "teacher": self.teacher,
            "max_participants": self.max_participants,
            "participants": self.participants,
        }

    @classmethod
    def from_record(cls, record: dict, venue: Venue) -> "Workshop":
        _require(record, "title", "start", "duration_minutes", "teacher", "max_participants")
        return cls(
            record["title"],
            venue,
            parse_moment(record["start"]),
            parse_minutes(record["duration_minutes"]),
            record["teacher"],
            int(record["max_participants"]),
            list(record.get("participants", [])),
            record.get("description", ""),
        )


KINDS: dict[str, type[Performance]] = {
    SoloShow.kind: SoloShow,
    Lineup.kind: Lineup,
    Workshop.kind: Workshop,
}


def performance_from_record(record: dict, venues: dict[str, Venue]) -> Performance:
    _require(record, "kind", "venue")
    if record["kind"] not in KINDS:
        raise InvalidError(f"Unknown kind '{record['kind']}'.")
    if record["venue"] not in venues:
        raise NotFoundError(f"Unknown venue '{record['venue']}'.")
    return KINDS[record["kind"]].from_record(record, venues[record["venue"]])
