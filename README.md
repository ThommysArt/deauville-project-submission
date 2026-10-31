# Deauville Festival du Rire 2027

Programme platform: command line, rules, and HTTP API for the festival website.

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

Rules live in `Festival.check` and in each performance kind's constructor.
With a database, only a new `Storage` would change.

## Known limits

No admin UI is shipped (`web/admin/`); write routes are available through `/docs`.
