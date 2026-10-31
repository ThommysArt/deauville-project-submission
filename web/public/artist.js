// One artist and their shows.
const slug = new URLSearchParams(location.search).get("slug");

function showTime(iso) {
  return iso.slice(11, 16);
}

function shortDay(day) {
  return new Date(day + "T12:00").toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
  });
}

async function loadArtist() {
  const response = await fetch(`/api/artists/${slug}`);
  if (!response.ok) {
    document.getElementById("artist-name").textContent = "Unknown artist";
    return;
  }
  const artist = await response.json();
  document.getElementById("artist-name").textContent = artist.name;
  document.getElementById("artist-bio").textContent = artist.bio;
  const box = document.getElementById("shows");
  for (const show of artist.performances) {
    const card = document.createElement("div");
    card.className = "card";
    const time = document.createElement("span");
    time.className = "time";
    time.textContent =
      `${shortDay(show.festival_day)} ${showTime(show.start)}-${showTime(show.end)}`;
    const title = document.createElement("strong");
    title.textContent = `${show.title} at ${show.venue_name}`;
    const kind = document.createElement("span");
    kind.className = "kind";
    kind.textContent = show.kind;
    card.append(time, title, kind);
    box.appendChild(card);
  }
}

loadArtist();
