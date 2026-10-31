from datetime import date, datetime

import pytest

from deauville.errors import ConflictError, FestivalError, InvalidError, NotFoundError
from deauville.models import Lineup, Performance, SoloShow, Workshop
from deauville.slugs import to_slug


def solo(artist="karim-benali", venue="la-cabane", start="2027-06-13T08:00", minutes=30):
    return {
        "kind": "solo",
        "title": "T",
        "artist": artist,
        "venue": venue,
        "start": start,
        "duration_minutes": minutes,
    }


def test_data_file_loads_and_counts(festival):
    assert (len(festival.venues), len(festival.artists), len(festival.performances)) == (
        4,
        12,
        23,
    )


def test_slug_removes_accents_and_noise():
    assert to_slug("Théâtre des Planches") == "theatre-des-planches"
    assert to_slug("Élodie  Marchal !") == "elodie-marchal"


def test_night_show_belongs_to_previous_day(festival):
    after_hours = festival.performance("le-kiosque-2027-06-12-0100")
    assert after_hours.festival_day == date(2027, 6, 11)
    assert after_hours in festival.programme(date(2027, 6, 11))
    assert after_hours not in festival.programme(date(2027, 6, 12))


def test_venue_busy(festival):
    with pytest.raises(ConflictError, match="Le Kiosque is busy with After Hours"):
        festival.add_from_record(solo(venue="le-kiosque", start="2027-06-12T02:15"))


def test_gap_of_30_minutes_is_allowed_exactly(festival):
    festival.add_from_record(solo(venue="le-kiosque", start="2027-06-12T02:30", minutes=20))


def test_artist_busy_in_another_venue(festival):
    with pytest.raises(ConflictError, match="Max Pellerin is on stage in Late Laughs"):
        festival.add_from_record(solo("max-pellerin", "la-cabane", "2027-06-11T23:00"))


def test_artist_busy_as_act_of_a_lineup(festival):
    with pytest.raises(ConflictError, match="Hugo Lemaire"):
        festival.add_from_record(solo("hugo-lemaire", "la-cabane", "2027-06-12T01:15"))


def test_day_outside_festival(festival):
    with pytest.raises(InvalidError, match="not a day of the festival"):
        festival.add_from_record(solo(start="2027-06-14T08:00"))


@pytest.mark.parametrize("minutes", [0, 361])
def test_duration_out_of_range(festival, minutes):
    with pytest.raises(InvalidError):
        festival.add_from_record(solo(minutes=minutes))


@pytest.mark.parametrize("minutes", [1, 360])
def test_duration_limits_accepted(festival, minutes):
    festival.add_artist("Free Agent")
    festival.add_from_record(solo("free-agent", start="2027-06-10T06:30", minutes=minutes))


def test_unknown_venue_and_artist(festival):
    with pytest.raises(NotFoundError):
        festival.add_from_record(solo(venue="nowhere"))
    with pytest.raises(NotFoundError):
        festival.add_from_record(solo(artist="nobody"))


def test_bad_duration_text(festival):
    with pytest.raises(InvalidError, match="not a number of minutes"):
        festival.add_from_record(solo(minutes="half an hour"))


def lineup(acts, minutes, host="tom-vasseur"):
    return {
        "kind": "lineup",
        "title": "L",
        "venue": "grand-casino",
        "start": "2027-06-13T14:00",
        "duration_minutes": minutes,
        "host": host,
        "acts": acts,
    }


THREE = ["nora-lebrun", "lea-fontaine", "karim-benali"]


def test_lineup_needs_enough_minutes(festival):
    with pytest.raises(InvalidError, match="at least 36"):
        festival.add_from_record(lineup(THREE, 35))
    festival.add_from_record(lineup(THREE, 36))


def test_lineup_rules(festival):
    with pytest.raises(InvalidError, match="at least two acts"):
        festival.add_from_record(lineup(["nora-lebrun"], 60))
    with pytest.raises(InvalidError, match="twice"):
        festival.add_from_record(lineup(["nora-lebrun", "nora-lebrun"], 60))
    with pytest.raises(InvalidError, match="host"):
        festival.add_from_record(lineup(THREE, 60, host="nora-lebrun"))


def test_workshop_places_limited_by_venue(festival):
    record = {
        "kind": "workshop",
        "title": "W",
        "venue": "grand-casino",
        "start": "2027-06-13T11:00",
        "duration_minutes": 60,
        "teacher": "tom-vasseur",
        "max_participants": 999,
    }
    workshop = festival.add_from_record(record)
    assert workshop.places == 650


def test_workshop_needs_one_place(festival):
    with pytest.raises(InvalidError):
        festival.add_from_record(
            {
                "kind": "workshop",
                "title": "W",
                "venue": "la-cabane",
                "start": "2027-06-13T11:00",
                "duration_minutes": 60,
                "teacher": "ines-moreau",
                "max_participants": 0,
            }
        )


@pytest.mark.parametrize("age", [-1, 19])
def test_min_age_range(festival, age):
    with pytest.raises(InvalidError):
        festival.add_from_record({**solo(), "min_age": age})


def test_performance_is_abstract():
    with pytest.raises(TypeError):
        Performance("x", None, datetime.now(), 10)  # type: ignore[abstract]


def test_summaries(festival):
    names = festival.artist_names
    assert festival.performance("le-kiosque-2027-06-12-0100").summary(names) == (
        "hosted by Tom Vasseur, with Hugo Lemaire, Maya Choukri"
    )
    assert festival.performance("la-cabane-2027-06-11-1030").summary(names) == (
        "with Inès Moreau, 3/12 places taken"
    )
    assert festival.performance("grand-casino-2027-06-11-2030").summary(names) == ("Léa Fontaine")


def test_polymorphic_kinds(festival):
    kinds = {type(p) for p in festival.performances}
    assert kinds == {SoloShow, Lineup, Workshop}


def test_nobody_changes_the_schedule_from_outside(festival):
    festival.performances.append("junk")
    assert "junk" not in festival.performances
    with pytest.raises(AttributeError):
        festival.performances = []  # type: ignore[misc]


def test_lineup_acts_cannot_be_changed_from_outside(festival):
    after_hours = festival.performance("le-kiosque-2027-06-12-0100")
    after_hours.acts.append("zzz")
    assert "zzz" not in after_hours.acts


def test_move_changes_id(festival):
    added = festival.add_from_record(solo("nora-lebrun", "le-kiosque", "2027-06-13T11:00", 45))
    moved = festival.replace_performance(added.id, {"start": "2027-06-13T12:00"})
    assert moved.id == "le-kiosque-2027-06-13-1200"
    assert [p.id for p in festival.performances].count("le-kiosque-2027-06-13-1100") == 0


def test_refused_move_changes_nothing(festival):
    added = festival.add_from_record(solo("nora-lebrun", "le-kiosque", "2027-06-13T12:00", 45))
    before = festival.to_data()
    with pytest.raises(ConflictError):
        festival.replace_performance(added.id, {"start": "2027-06-13T15:00"})
    assert festival.to_data() == before


def test_register_twice_refused_and_full(festival):
    stand_up = next(p for p in festival.performances if p.title == "Stand-up Lab")
    festival.register(stand_up.id, "Zoe Z.")
    with pytest.raises(ConflictError, match="already registered"):
        festival.register(stand_up.id, "zoe z.")
    for i in range(stand_up.places_left):
        festival.register(stand_up.id, f"Person {i}")
    with pytest.raises(ConflictError, match="full"):
        festival.register(stand_up.id, "Late Comer")


def test_artist_added_once(festival):
    festival.add_artist("Zoé Tanguy")
    with pytest.raises(ConflictError):
        festival.add_artist("zoe tanguy")


def test_errors_are_one_family():
    for error in (NotFoundError, ConflictError, InvalidError):
        assert issubclass(error, FestivalError)


def test_artist_equality_by_slug(festival):
    from deauville.models import Artist

    assert Artist("Max Pellerin") == Artist("max pellerin")
    assert sorted([Artist("Zed"), Artist("Abe")])[0].name == "Abe"
    assert Artist("Abe") != "Abe"


def test_on_stage_and_up_next(festival):
    at = datetime(2027, 6, 11, 21, 0)
    assert [p.title for p in festival.on_stage(at)] == ["Tall Tales"]
    assert [p.title for p in festival.up_next(at)] == [
        "Straight Face",
        "Late Laughs",
        "After Hours",
    ]
    assert [p.title for p in festival.on_stage(datetime(2027, 6, 12, 1, 30))] == ["After Hours"]
