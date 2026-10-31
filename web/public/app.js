// The festival website. It only talks to the API, never to the data file.
const params = new URLSearchParams(location.search);

async function get(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(path);
  return response.json();
}

// "2027-06-12T01:00" -> "01:00"
function showTime(iso) {
  return iso.slice(11, 16);
}

// "2027-06-11" -> "Friday 11 June"
function longDay(day) {
  return new Date(day + "T12:00").toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

// "2027-06-11" -> "Fri 11"
function shortDay(day) {
  return new Date(day + "T12:00").toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
  });
}

let currentDay = "";
let currentVenue = "";

async function loadFestival() {
  const festival = await get("/api/festival");
  document.getElementById("fest-name").textContent = festival.name;
  document.getElementById("fest-dates").textContent =
    `${longDay(festival.first_day)} to ${longDay(festival.last_day)}`;
  const nav = document.getElementById("days");
  nav.innerHTML = "";
  currentDay = festival.days[0];
  for (const day of festival.days) {
    const button = document.createElement("button");
    button.textContent = shortDay(day);
    if (day === currentDay) button.classList.add("active");
    button.addEventListener("click", () => {
      currentDay = day;
      for (const other of nav.children) other.classList.remove("active");
      button.classList.add("active");
      loadProgramme();
    });
    nav.appendChild(button);
  }
}

async function loadVenues() {
  const venues = await get("/api/venues");
  const select = document.getElementById("venue-filter");
  const list = document.getElementById("venues");
  list.innerHTML = "";
  for (const venue of venues) {
    const option = document.createElement("option");
    option.value = venue.slug;
    option.textContent = venue.name;
    select.appendChild(option);
    const item = document.createElement("li");
    item.textContent = `${venue.name}, ${venue.capacity} seats, ${venue.address}`;
    list.appendChild(item);
  }
  select.addEventListener("change", () => {
    currentVenue = select.value;
    loadProgramme();
  });
}

async function loadArtists() {
  const artists = await get("/api/artists");
  const grid = document.getElementById("artists");
  grid.innerHTML = "";
  for (const artist of artists) {
    const card = document.createElement("a");
    card.className = "artist";
    card.href = `artist.html?slug=${artist.slug}`;
    const photo = document.createElement("div");
    photo.className = "photo";
    if (artist.photo_url) {
      const img = document.createElement("img");
      img.src = artist.photo_url;
      img.alt = "";
      photo.appendChild(img);
    } else {
      photo.textContent = artist.name[0];
    }
    const name = document.createElement("strong");
    name.textContent = artist.name;
    const bio = document.createElement("span");
    bio.textContent = artist.bio;
    card.append(photo, name, bio);
    grid.appendChild(card);
  }
}

function programmeCard(perf) {
  const card = document.createElement("div");
  card.className = "card";
  const time = document.createElement("span");
  time.className = "time";
  time.textContent = `${showTime(perf.start)}-${showTime(perf.end)}`;
  const title = document.createElement("strong");
  title.textContent = `${perf.title} at ${perf.venue_name}`;
  const kind = document.createElement("span");
  kind.className = "kind";
  kind.textContent = perf.kind;
  card.append(time, title, kind);
  if (perf.min_age) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = `${perf.min_age}+`;
    card.appendChild(badge);
  }
  if (perf.places_left !== undefined) {
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = `${perf.places_left} places left`;
    card.appendChild(badge);
  }
  const summary = document.createElement("p");
  summary.textContent = perf.summary;
  card.appendChild(summary);
  return card;
}

async function loadProgramme() {
  const box = document.getElementById("programme");
  try {
    let path = `/api/programme?day=${currentDay}`;
    if (currentVenue) path += `&venue=${currentVenue}`;
    const shows = await get(path);
    box.innerHTML = "";
    if (shows.length === 0) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "No performances.";
      box.appendChild(empty);
    }
    for (const show of shows) box.appendChild(programmeCard(show));
  } catch {
    box.innerHTML = ""; // the route does not exist yet (step 07)
  }
}

async function loadNow() {
  const section = document.getElementById("now");
  try {
    let path = "/api/now";
    if (params.get("at")) path += `?at=${params.get("at")}`;
    const now = await get(path);
    section.hidden = false;
    const playing = document.getElementById("now-playing");
    playing.innerHTML = "";
    for (const show of now.now_playing) {
      const item = document.createElement("li");
      item.textContent =
        `${show.title} at ${show.venue_name}, until ${showTime(show.end)}`;
      playing.appendChild(item);
    }
    const next = document.getElementById("up-next");
    next.innerHTML = "";
    for (const show of now.up_next) {
      const item = document.createElement("li");
      item.textContent =
        `${showTime(show.start)}-${showTime(show.end)} at ${show.venue_name}: ${show.title}`;
      next.appendChild(item);
    }
  } catch {
    section.hidden = true; // the route does not exist yet (step 08)
  }
}

loadFestival().then(loadProgramme);
loadVenues();
loadArtists();
loadNow();
