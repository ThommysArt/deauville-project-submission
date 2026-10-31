# Deauville Festival du Rire 2027

Programme platform for the festival (ECE OOP track).

```bash
uv sync
uv run main.py
uv run main.py programme 2027-06-11
uv run main.py now 2027-06-11T21:00
uv run main.py artist max-pellerin
```

## Known bugs

None. A festival day ends at 06:00: the festival day of a show is the date
of its start minus 6 hours, so After Hours (01:00) belongs to Friday.
