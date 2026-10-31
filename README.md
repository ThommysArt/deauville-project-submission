# Deauville Festival du Rire 2027

Programme platform for the festival (ECE OOP track).

```bash
uv sync
uv run main.py
```

## Known bugs

Asking for a day uses the first 10 characters of `start`. A show at 01:00
on Saturday is listed under Saturday, but for the festival it still belongs
to Friday night (a festival day ends at 06:00). Fixed in B2.
