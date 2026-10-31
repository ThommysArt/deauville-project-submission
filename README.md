# Deauville Festival du Rire 2027

Programme platform: command line, rules, and HTTP API for the festival website.

## Design decisions

### Domain classes (models.py)

- `Venue` is a frozen `dataclass` — immutable once created, with a derived `slug` (via `slugs.to_slug`) used as the canonical key.
- `Artist` is mutable; identity is defined by `slug`, so equality and ordering are based on name only (`__eq__`, `__hash__`, `__lt__`).
- `Performance` is abstract (`ABC`). It defines scheduling rules (`start`, `end`, `duration_minutes`, `festival_day`, `capacity`, `roles`, `summary`) and requires concrete kinds (`kind` class variable, `from_record`, `to_record`).
- Three concrete kinds implement the brief's requirements:
  - `SoloShow` — one artist (`artist`), optional age restriction (`min_age`).
  - `Lineup` — at least two acts, a separate `host`, and a minimum time calculation (`MINUTES_PER_ACT` * acts + `MINUTES_FOR_HOST` * (acts - 1)). The host cannot also be an act.
  - `Workshop` — `teacher`, `max_participants`, and live participant tracking (`register`). Capacity is capped by venue (`places = min(max_participants, venue.capacity)`).
- Performance IDs (`id`) are derived deterministically from venue slug and start time (`venue-start`), making them stable across saves.
- `KINDS` registry maps string kinds to classes, so `performance_from_record` can reconstruct any kind dynamically.

### Scheduling rules (festival.py)

- `Festival` owns the data and the scheduling rules. It holds dictionaries keyed by slug (`_venues`, `_artists`, `_performances`) for fast lookup.
- `check()` validates conflicts in two dimensions:
  1. Venue overlap (`too_close`) — prevents double-booking a venue.
  2. Artist overlap (`too_close`) — prevents an artist from being on stage in two performances at once.
- `add_performance`, `replace_performance`, `cancel`, `add_artist`, and `register` all use `_commit()` for atomic persistence: on `StorageError`, state is rolled back (before snapshot restored) so the API/client never sees partial changes.
- `Festival.open()` reads from any `Storage` (currently `JsonStorage` or `MemoryStorage`) and reconstructs the domain objects, so the same scheduling logic works whether data comes from a JSON file, memory, or a future database.
- Only a new `Storage` implementation is needed to switch persistence; scheduling rules are isolated from I/O.

### Errors (errors.py)

- All deliberate errors inherit from `FestivalError`.
- `NotFoundError` (404), `ConflictError` (409), `InvalidError` (422), `StorageError` (500) are mapped directly to HTTP status codes in `api.py` (`STATUS` dict) and to CLI messages.

### Storage abstraction (storage.py)

- `Storage` interface (`load`/`save`) keeps persistence out of the domain.
- `JsonStorage` writes atomically (temporary file + `replace`) so a crash never corrupts the data file. Deep copies (`MemoryStorage`) prevent accidental mutations across loads.

### API architecture (api.py)

- `create_app(storage)` builds a `FastAPI` instance from the storage layer, not from a hard-coded file path, which makes it easy to test with `MemoryStorage`.
- `PerformanceBody` uses Pydantic's `ConfigDict(extra="forbid")` for strict validation (unknown fields are rejected, matching the brief's strict schema requirements).
- The exception handler converts domain errors (`FestivalError`) to JSON responses using the `STATUS` mapping.
- Static site mounting (`/`, `/admin`) is conditional on `web_dir`, keeping the web layer optional.

### CLI (cli.py)

- `cli.py` uses `argparse` subcommands (`programme`, `artist`, `now`, `add`, `cancel`, `serve`) to expose the core scheduling rules from the terminal.
- The CLI reuses the same `Festival.open()` and `Storage` abstraction, ensuring consistency with the API.

### Time rules (times.py)

- Festival days are calculated as calendar dates (`date`) at −6 hours (`festival_day`), and a 30-minute gap is enforced (`too_close`) to separate overlapping performances on the same stage or by the same artist.

## Push notes

This repository was created on GitHub (`https://github.com/ThommysArt/deauville-project-submission`) and the `restart-scratch` branch (containing B1–B5 design commits: full API contract tests, performance kinds/admin routes, classes and scheduling rules, real dates/times, and summary/programme logic) was pushed to it. The original `main` branch (Step 00–05) remains in the source worktree (`/home/thommysart/Works/school/deauville-festival`).

## Structure

| Module | Role |
| --- | --- |
| `errors.py` | `FestivalError` family → HTTP statuses |
| `slugs.py`, `times.py` | slug, festival day (−6 h), 30-minute gap |
| `models.py` | `Venue`, `Artist`, abstract `Performance`, `SoloShow`, `Lineup`, `Workshop` |
| `festival.py` | owns the data and every scheduling rule |
| `storage.py` | `Storage` interface, JSON and memory |
| `cli.py` | command line |
| `api.py` | `create_app(storage)` |

Rules live in `Festival.check` and in each performance kind's constructor. With a database, only a new `Storage` would change.

## Known limits

No admin UI is shipped (`web/admin/`); write routes are available through `/docs`.

## Install and run

```bash
uv sync
uv run deauville
uv run deauville programme 2027-06-11
uv run deauville now 2027-06-11T21:00
uv run deauville serve
uv run pytest
uv build
```

`serve` starts the API on http://127.0.0.1:8000 (website at `/`, docs at `/docs`).
Use `--data PATH` for another data file.
