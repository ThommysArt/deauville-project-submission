from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from .errors import ConflictError, FestivalError, InvalidError, NotFoundError
from .festival import Festival
from .storage import Storage

STATUS = {NotFoundError: 404, ConflictError: 409, InvalidError: 422}


class PerformanceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str | None = None
    title: str | None = None
    venue: str | None = None
    start: str | None = None
    duration_minutes: int | str | None = None
    description: str | None = None
    artist: str | None = None
    min_age: int | None = None
    host: str | None = None
    acts: list[str] | None = None
    teacher: str | None = None
    max_participants: int | None = None
    participants: list[str] | None = None


class ParticipantBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str


class ArtistBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    bio: str = ""
    photo_url: str = ""


def create_app(storage: Storage, web_dir: Path | None = None) -> FastAPI:
    festival = Festival.open(storage)
    app = FastAPI(title=festival.name)

    @app.exception_handler(FestivalError)
    def handle_error(_request: Request, error: FestivalError) -> JSONResponse:
        status = next((code for kind, code in STATUS.items() if isinstance(error, kind)), 500)
        return JSONResponse({"detail": str(error)}, status_code=status)

    def view(performance) -> dict:
        return performance.to_view(festival.artist_names)

    @app.get("/api/festival")
    def get_festival() -> dict:
        return {
            "name": festival.name,
            "first_day": festival.first_day.isoformat(),
            "last_day": festival.last_day.isoformat(),
            "days": [d.isoformat() for d in festival.days],
        }

    @app.get("/api/venues")
    def list_venues() -> list[dict]:
        return [v.to_view() for v in festival.venues]

    @app.get("/api/artists")
    def list_artists() -> list[dict]:
        return [a.to_view() for a in festival.artists]

    @app.get("/api/artists/{slug}")
    def get_artist(slug: str) -> dict:
        artist = festival.artist(slug)
        return {
            **artist.to_view(),
            "performances": [view(p) for p in festival.performances_of(slug)],
        }

    @app.get("/api/programme")
    def get_programme(
        day: date | None = None,
        venue: str | None = None,
        kind: str | None = None,
    ) -> list[dict]:
        if venue is not None:
            festival.venue(venue)
        shows = festival.performances if day is None else festival.programme(day)
        return [
            view(p)
            for p in shows
            if (venue is None or p.venue.slug == venue) and (kind is None or p.kind == kind)
        ]

    @app.get("/api/performances/{performance_id}")
    def get_performance(performance_id: str) -> dict:
        return view(festival.performance(performance_id))

    @app.get("/api/now")
    def get_now(at: datetime | None = None) -> dict:
        moment = at or datetime.now()
        return {
            "at": moment.isoformat(timespec="minutes"),
            "now_playing": [view(p) for p in festival.on_stage(moment)],
            "up_next": [view(p) for p in festival.up_next(moment, 3)],
        }

    @app.post("/api/performances", status_code=201)
    def create_performance(body: PerformanceBody) -> dict:
        return view(festival.add_from_record(body.model_dump(exclude_none=True)))

    @app.put("/api/performances/{performance_id}")
    def edit_performance(performance_id: str, body: PerformanceBody) -> dict:
        return view(
            festival.replace_performance(performance_id, body.model_dump(exclude_none=True))
        )

    @app.delete("/api/performances/{performance_id}", status_code=204)
    def cancel_performance(performance_id: str) -> Response:
        festival.cancel(performance_id)
        return Response(status_code=204)

    @app.post("/api/performances/{performance_id}/participants", status_code=201)
    def register_participant(performance_id: str, body: ParticipantBody) -> dict:
        return view(festival.register(performance_id, body.name))

    @app.post("/api/artists", status_code=201)
    def create_artist(body: ArtistBody) -> dict:
        return festival.add_artist(body.name, body.bio, body.photo_url).to_view()

    if web_dir is not None and (web_dir / "public").is_dir():
        if (web_dir / "admin").is_dir():
            app.mount("/admin", StaticFiles(directory=web_dir / "admin", html=True))
        app.mount("/", StaticFiles(directory=web_dir / "public", html=True))
    return app
