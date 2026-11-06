# Telefonos elérés felhő nélkül – Tailscale

Ezzel a beállítással a telefonodról, bárhonnan (mobilneten is) eléred a gépeden futó ContentOps webet. Nincs szükség Supabase-, Vercel- vagy tárhelyfiókra, és nincs költség. Az app nem kerül ki az internetre: csak a saját, Tailscale-be bejelentkezett eszközeid látják.

**Feltétel:** a gépednek bekapcsolva és ébren kell lennie, amikor a telefonról használod.

## 1. Egyszeri beállítás

1. **Gépen:** telepítsd a Tailscale-t a [tailscale.com/download](https://tailscale.com/download) oldalról, vagy PowerShellből:

   ```powershell
   winget install --id Tailscale.Tailscale -e
   ```

   Indítsd el, és jelentkezz be (Google-, Microsoft- vagy GitHub-fiókkal).
2. **Telefonon:** telepítsd a Tailscale appot (App Store / Google Play), és jelentkezz be **ugyanazzal** a fiókkal. Kapcsold be a VPN-t az appban.

## 2. Indítás (minden használat előtt)

Két terminálban, a repository gyökeréből:

```powershell
uv run --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
npm run serve:local
```

A `serve:local` production buildet készít, és a webet csak a `127.0.0.1:3000` címen indítja el. A Claude Code-ban a `contentops-api` és a `contentops-web-local` indítási konfiguráció ugyanezt csinálja.

Ezután tedd elérhetővé a tailneten:

```powershell
tailscale serve --bg 3000
tailscale serve status
```

Első alkalommal a Tailscale kérheti, hogy engedélyezd a HTTPS-tanúsítványokat. Ezt a megjelenő linken, a saját admin felületeden fogadd el. A `status` parancs kiírja a címet, például `https://gepnev.tailnet-nev.ts.net`.

## 3. Telefonon

1. Nyisd meg a kiírt `https://…ts.net` címet a telefon böngészőjében.
2. Add a kezdőképernyőhöz (Safari: Megosztás → Főképernyőhöz adás; Chrome: ⋮ → Hozzáadás a kezdőképernyőhöz). Így appként indul.
3. Próba: kapcsold ki a wifit, és mobilneten is töltsd be a címet.

## Biztonság

- Helyi módban az alkalmazás nem kér bejelentkezést. A védelmet az adja, hogy csak a tailneted eszközei érik el, és a web csak a `127.0.0.1`-en figyel, így a helyi hálózatról (pl. kávézó wifi) sem látható.
- **Soha ne használd a `tailscale funnel` parancsot.** Az nyilvánossá tenné az appot az interneten, bejelentkezés nélkül.
- Ne oszd meg ezt a gépet más Tailscale-felhasználóval.
- Kikapcsolás: `tailscale serve reset`.

## Mi működik így, és mi nem?

| | Tailscale-lel |
| --- | --- |
| Ötlet rögzítése, draft átnézése, jóváhagyás telefonon | ✅ |
| Draftírás Claude Code-dal a gépen | ✅ |
| Claude mobilapp vagy ChatGPT közvetlenül a ContentOps-szal | ❌ Ehhez felhős telepítés kell ([DEPLOYMENT_HU.md](DEPLOYMENT_HU.md)) |
| Elérés kikapcsolt gép mellett | ❌ |

Ha két hét használat után a telefonos és mobil-Claude-os használat valódi igény, a felhős telepítés a [DEPLOYMENT_HU.md](DEPLOYMENT_HU.md) szerint jöhet. A kód mindkettőt támogatja.
