# Telepítési csomag

| Fájl | Mire való? |
| --- | --- |
| `backend.env.example` | A Python tárhelyen megadandó beállítások mintája |
| `frontend.env.example` | A Vercelen megadandó beállítások mintája |
| `supabase-storage.sql` | A privát adattárolási séma létrehozása |
| `supabase-mcp-token-hook.sql` | A dedikált OAuth-kliens tokenjének MCP-audience beállítása |
| `../backend/Dockerfile` | Az API és MCP közös konténere |
| `../vercel.json` | A web build- és telepítési konfigurációja |

## Beállítások kitöltése

A repository gyökerében, PowerShellből (csak ha még nem léteznek a célfájlok):

```powershell
Copy-Item deploy/backend.env.example deploy/backend.env.local
Copy-Item deploy/frontend.env.example deploy/frontend.env.local
```

Cseréld ki az összes `REPLACE_...` értéket. A kitöltött `.env.local` fájlokat a Git figyelmen kívül hagyja. A webes tárhelyre csak a frontend fájl értékei kerüljenek; az adatbázis jelszava kizárólag a backendhez tartozik. Ezek a fájlok helyi munkalapok: a szolgáltatókhoz külön kell felvinni az értékeket, a fejlesztői szerver nem tölti be automatikusan őket.

Ellenőrzés a `backend` könyvtárból:

```powershell
uv run python -m app.preflight --backend-env ../deploy/backend.env.local --frontend-env ../deploy/frontend.env.local
```

A parancs nem csatlakozik a fiókjaidhoz, nem módosít adatokat és nem írja ki a titkos értékeket. A hibás beállítás nevét és a javítás irányát jelzi. A sikeres eredmény konfigurációs egyezést jelent, nem igazolja az OAuth-folyamatot vagy az élő adatbázist.

A teljes, követendő sorrend és a szolgáltatói teendők: [Supabase → backend → Vercel → ChatGPT](../docs/DEPLOYMENT_HU.md).

A buildbeállítás a [Vercel projektkonfigurációját](https://vercel.com/docs/project-configuration) használja. A backend Docker-build a GitHub Actions ellenőrzésbe is bekerült; eredményét a CI futtatása után lehet igazolni.
