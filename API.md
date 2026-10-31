# Deauville Festival API

The website (`web/public/`) talks to this API over HTTP. Field names are a
contract.

Base URL: `http://127.0.0.1:8000`. Docs: `/docs`.

## Objects

### Festival

```json
{
  "name": "Deauville Festival du Rire 2027",
  "first_day": "2027-06-10",
  "last_day": "2027-06-13",
  "days": ["2027-06-10", "2027-06-11", "2027-06-12", "2027-06-13"]
}
```

### Venue

```json
{ "slug": "le-kiosque", "name": "Le Kiosque", "capacity": 120, "address": "Beach promenade" }
```

### Artist

```json
{
  "slug": "elodie-marchal",
  "name": "Élodie Marchal",
  "bio": "Stand-up about sport, failure and trying again.",
  "photo_url": ""
}
```

Sorted by `slug`. Detail route adds `performances`.

### Performance

Shared fields: `id`, `kind`, `title`, `venue`, `venue_name`, `start`, `end`,
`duration_minutes`, `festival_day`, `description`, `summary`, `capacity`,
`artists`.

| Kind       | Summary                                            | Extra fields |
| ---------- | -------------------------------------------------- | ------------ |
| solo       | artist name                                        | `artist`, `min_age` |
| lineup     | `hosted by …, with …`                              | `host`, `acts` |
| workshop   | `with …, n/m places taken`                         | `teacher`, `max_participants`, `participants`, `places_left` |

Workshop `capacity` is `min(max_participants, venue seats)`.

### Now

```json
{ "now_playing": [ ... ], "up_next": [ ... ] }
```

`up_next` holds at most 3 shows.

## Read

| Route                        | Filters            | Returns |
| ---------------------------- | ------------------ | ------- |
| `GET /api/festival`          | —                  | Festival |
| `GET /api/venues`            | —                  | venues |
| `GET /api/artists`           | —                  | artists |
| `GET /api/artists/{slug}`    | —                  | artist + performances |
| `GET /api/programme`         | `?day=` `?venue=` `?kind=` | performances |
| `GET /api/performances/{id}` | —                  | performance |
| `GET /api/now`               | `?at=`             | now |

Unknown venue/artist/id → `404` `{"detail": "…"}`. Bad `?day=` → `422`.

## Write

| Route | Body | Status |
| ----- | ---- | ------ |
| `POST /api/performances` | performance fields (`kind`, `title`, `venue`, `start`, `duration_minutes`, …) | `201` |
| `PUT /api/performances/{id}` | fields to change (moving may change the id) | `200` |
| `DELETE /api/performances/{id}` | — | `204` |
| `POST /api/performances/{id}/participants` | `{"name": "…"}` | `201` |
| `POST /api/artists` | `{"name": "…", "bio"?: "…", "photo_url"?: "…"}` | `201` |

A refused move changes nothing.

## Errors

| Status | When |
| ------ | ---- |
| `201`  | created |
| `200`  | replaced |
| `204`  | removed |
| `404`  | unknown venue, artist or id |
| `409`  | venue busy, artist on stage, workshop full, duplicate |
| `422`  | bad value or body |
| `500`  | cannot save the data file |
