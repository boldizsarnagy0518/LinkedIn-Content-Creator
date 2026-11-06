# Éles ContentOps: telepítés, Claude- és ChatGPT-kapcsolat

**Előkészített fájlok és ellenőrző parancsok:** [deploy/README.md](../deploy/README.md). **Felhasználói útmutató:** [mit mire és hogyan használj](HASZNALATI_UTMUTATO.md). **Felhő nélküli telefonos elérés:** [Tailscale](TELEFON_TAILSCALE_HU.md).

Az alkalmazás modell-API nélkül működik. A szöveget egy MCP-host (Claude, Claude Code, Codex vagy ChatGPT) készíti; az MCP tárolja és kezeli a munkafolyamatot. Helyi használathoz nem kell telepítés: a Claude Code a repository `.mcp.json` fájljával közvetlenül eléri a helyi szervert. Ez az útmutató a felhős változatról szól, amelyet a géped kikapcsolt állapotában is elérsz telefonról és a Claude mobilappból.

**Csomagok (2026. október, a bekötés előtt ellenőrizd újra):** az OpenAI súgója szerint egyéni MCP-szervert ChatGPT-ben csak Business és Enterprise/Edu csomagban, weben lehet bekötni, mobilon nem. Az Anthropic szerint egyéni connector minden Claude-csomagban elérhető (Free csomagban egy darab), és a weben bekötött connector a mobilappban is használható.

## Felépítés

| Szolgáltatás | Mit futtat? | Cím |
| --- | --- | --- |
| Supabase | PostgreSQL-adatbázis (privát `contentops` séma), bejelentkezés, OAuth 2.1 szerver | `https://PROJECT.supabase.co` |
| Google Cloud Run | Python backend egy konténerben: API a `/api`, MCP a `/mcp` alatt | `https://BACKEND_HOST` |
| Vercel | Next.js web, belépés, OAuth-hozzájárulási oldal | `https://WEB_HOST` |

A Cloud Run kérés nélkül nullára skáláz, és a következő kérésre néhány másodperc alatt indul újra. Havi nagyjából 2 millió kérés ingyenes, de a Google Cloudhoz bankkártyás számlázási fiók kell. A Supabase ingyenes projektje kb. 7 nap teljes tétlenség után szünetel; ilyenkor a Supabase felületén egy kattintással újraindítható.

## 1. Előkészítve – nincs teendő

- `backend/Dockerfile`: az API és az MCP közös konténere, a Cloud Run `PORT` változóját használja. A CI minden pushnál lefordítja.
- `deploy/deploy-backend-cloudrun.ps1`: preflight, majd Cloud Run-telepítés. A titkokat ideiglenes fájlban adja át, és utána törli; értékeket nem ír ki.
- `backend/app/preflight.py`: a két env-fájl offline ellenőrzése.
- `backend/app/transfer.py`: a helyi SQLite-munkatér egyszeri átmásolása a felhős adatbázisba.
- `deploy/supabase-storage.sql`, `deploy/supabase-mcp-token-hook.sql`: Supabase-séma és az MCP-token audience-beállítása.
- `vercel.json`: a web build-beállítása.
- A web OAuth-hozzájárulási oldala (`/oauth/consent`), és az MCP elfogadja a Claude és a ChatGPT origint.

## 2. A gépre telepítendő eszköz

A Google Cloud CLI-t (`gcloud`) a [hivatalos oldalról](https://cloud.google.com/sdk/docs/install) vagy PowerShellből telepítheted:

```powershell
winget install --id Google.CloudSDK -e
```

A Vercelhez és a Supabase-hez nem kell parancssori eszköz.

## 3. Fiókok és beállítások – egy ülésben, a legvégén

Az alábbi sorrendben haladj. Minden kimásolt értéket a repository gyökerében lévő két munkafájlba írj (ezeket a Git figyelmen kívül hagyja):

```powershell
Copy-Item deploy/backend.env.example deploy/backend.env.local
Copy-Item deploy/frontend.env.example deploy/frontend.env.local
```

A `.env.local` fájlokban ne használj soron belüli megjegyzést (`ÉRTÉK # megjegyzés`).

### 3.1 Google Cloud: projekt és várható backend-cím

1. Lépj be a [Google Cloud Console](https://console.cloud.google.com)-ba, hozz létre egy projektet (pl. `contentops`), és kapcsolj hozzá számlázási fiókot.
2. A gépen:

   ```powershell
   gcloud auth login
   gcloud config set project PROJEKT_ID
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
   gcloud projects describe PROJEKT_ID --format "value(projectNumber)"
   ```

3. A várható backend-cím: `https://contentops-api-PROJEKTSZAM.europe-west1.run.app`. Ez a `BACKEND_HOST`. A telepítő script a végén kiírja a tényleges címet; ha eltér, javítsd az env-fájlokban, és futtasd újra a scriptet.

### 3.2 Vercel: a web címe

1. Lépj be a [Vercelbe](https://vercel.com) a GitHub-fiókoddal, és importáld a repositoryt (Framework: Next.js, gyökér: a repository gyökere). Az első buildet még ne indítsd el, vagy hagyd hibázni.
2. A projekt neve adja a címet: `https://PROJEKTNEV.vercel.app`. Ez a `WEB_HOST`.

### 3.3 Supabase: adatbázis és saját belépés

1. Hozz létre egy Supabase-projektet; régiónak válassz egy európait (pl. Frankfurt).
2. Authentication → Users: hozz létre egy felhasználót saját, megerősített email-címmel és jelszóval. A **User UID** → `CONTENTOPS_OWNER_USER_ID` (mindkét fájlba). A nyilvános regisztrációt kapcsold ki.
3. JWT Signing Keys: **ES256 vagy RS256** aktív aláírókulcs legyen. A backend JWKS alapján ellenőriz, HS256-ot nem fogad el.
4. SQL Editor: futtasd a `deploy/supabase-storage.sql` fájlt. Ez a privát `contentops` sémát hozza létre; **ne** add a Data API által elérhető sémákhoz.
5. Connect → **Session pooler** kapcsolati szöveg → `CONTENTOPS_DATABASE_URL`. A végére írd: `?sslmode=require&options=-c%20search_path%3Dcontentops` (ha már van benne `?`, akkor `&`-tel kezdd). A jelszó speciális karaktereit URL-kódolni kell. Ez titok, csak a backend-fájlba kerül.
6. Project URL → `SUPABASE_URL` és `NEXT_PUBLIC_SUPABASE_URL`. **Publishable key** → `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`. `service_role` kulcs nem kell.

### 3.4 Supabase: OAuth szerver a Claude-hoz

Authentication → OAuth Server:

1. Engedélyezd az OAuth 2.1 servert. Authorization Path: `/oauth/consent`.
2. URL Configuration → Site URL: `https://WEB_HOST`.
3. Regisztrálj egy dedikált, **előre regisztrált** OAuth-klienst. Redirect URI Claude-hoz: `https://claude.ai/api/mcp/auth_callback` (a Claude felületén ellenőrizd). ChatGPT-hez a ChatGPT kapcsolatkezelőjében megjelenő pontos cím kell; ugyanahhoz a klienshez mindkettő felvehető. Wildcardot ne használj.
4. Engedélyezd az asszisztens által kért OIDC scope-okat (pl. `openid`, `email`, `profile`).
5. A client ID → `MCP_OAUTH_CLIENT_ID` (mindkét fájlba). A client secretet csak az asszisztens beállításánál használd, ne írd fájlba.
6. Nyisd meg a `deploy/supabase-mcp-token-hook.sql` fájlt, cseréld ki a `REPLACE_WITH_MCP_OAUTH_CLIENT_ID` és a `https://REPLACE_WITH_BACKEND_HOST/mcp` helyőrzőt, futtasd a SQL Editorban, majd Authentication → Hooks → Custom Access Token alatt válaszd ki és engedélyezd a `public.contentops_access_token_hook` függvényt.

A hook csak ennek a kliensnek a tokenjében állítja az `aud` értéket az MCP-címre; a webes belépés `authenticated` audience-e változatlan. Hibás hook esetén az MCP 401-et ad; az ellenőrzést ne kapcsold ki.

### 3.5 A többi érték

- `MCP_PUBLIC_URL=https://BACKEND_HOST/mcp`
- `FRONTEND_ORIGIN=https://WEB_HOST`
- `PYTHON_BACKEND_URL=https://BACKEND_HOST/api` (a `/api` utótag kötelező)

Ellenőrzés, a `backend` könyvtárból (nem csatlakozik semmihez, értéket nem ír ki):

```powershell
uv run python -m app.preflight --backend-env ../deploy/backend.env.local --frontend-env ../deploy/frontend.env.local
```

### 3.6 Backend telepítése

A repository gyökeréből:

```powershell
./deploy/deploy-backend-cloudrun.ps1 -Project PROJEKT_ID -DryRun
./deploy/deploy-backend-cloudrun.ps1 -Project PROJEKT_ID
```

A végén nyisd meg a kiírt `…/api/ready` címet: `{"status":"ready"}` a jó válasz. Ha a tényleges cím eltér a várttól, javítsd a `BACKEND_HOST`-ot mindkét fájlban és a token hook SQL-ben, majd telepíts újra.

### 3.7 Web telepítése

A Vercel projekt Settings → Environment Variables alá vidd fel a `deploy/frontend.env.local` öt értékét (Production), majd Deployments → Redeploy. A két `NEXT_PUBLIC_` érték a buildbe kerül, ezért módosításuk után mindig újra kell telepíteni.

Próba: nyisd meg telefonon a `https://WEB_HOST` címet, lépj be, ments egy tesztötletet; asztali böngészőben ugyanannak meg kell jelennie.

### 3.8 Helyi adatok átvitele (ha helyben már dolgoztál)

A `backend` könyvtárból, amíg a felhős munkatér még üres:

```powershell
uv run python -m app.transfer --target-env ../deploy/backend.env.local --dry-run
uv run python -m app.transfer --target-env ../deploy/backend.env.local
```

Az eszköz mindent megtart (azonosítók, verziók, jóváhagyások, napló), egyetlen tranzakcióban dolgozik, és nem ír olyan adatbázisba, amelyben már van munka. A helyi adatbázist tartsd meg biztonsági másolatnak.

### 3.9 Claude bekötése

- **Claude (web, asztali és mobilapp):** Customize → Connectors → egyéni connector. URL: `https://BACKEND_HOST/mcp`; az Advanced settings alatt add meg az OAuth client ID-t és secretet. A weben bekötött connectort a mobilapp is használja.
- **Claude Code távoli szerverrel:** `claude mcp add --transport http contentops https://BACKEND_HOST/mcp`, majd a `/mcp` paranccsal jelentkezz be. A Claude Code saját, helyi (loopback) callbacket használ.
- **ChatGPT (Business/Enterprise):** a kapcsolatkezelőben MCP URL `https://BACKEND_HOST/mcp`, OAuth a fenti klienssel; a megjelenő callbacket vedd fel a Supabase-kliens redirect URI-jai közé.

Kapcsolódáskor a ContentOps belépési oldalára, majd a **Hozzáférés a műhelyedhez** oldalra jutsz. Ott kifejezetten engedélyezd a kapcsolatot. Ez hozzáférési döntés, nem posztjóváhagyás.

### 3.10 Átvételi próba

1. Kérd a Claude-tól a mentett ContentOps-ötletek listázását; a weben létrehozott tesztötletnek meg kell jelennie.
2. A Claude mobilappban írd: „Van egy ötletem: …”. A webre visszatérve meg kell jelennie egy új, még nem jóváhagyott draftnak.
3. Kérj egy módosítást, ellenőrizd a verziókat, és csak a megfelelő mentett verziót hagyd jóvá.
4. Token nélküli MCP-hívásnak 401-et kell adnia; más Supabase-felhasználó ne férjen hozzá a műhelyhez.

## Hibakeresés

| Tünet | Ellenőrizendő |
| --- | --- |
| A telepítő script preflight hibával áll meg | A kiírt mezők az env-fájlokban; nincs-e benne `REPLACE` vagy soron belüli megjegyzés |
| `/api/ready` 503 | PostgreSQL DSN, `search_path`, a `supabase-storage.sql` lefutott-e, nincs-e szüneteltetve a Supabase-projekt |
| Web nem éri el az API-t | `PYTHON_BACKEND_URL` végén `/api`, a backend publikus elérhetősége |
| Bejelentkezés után hozzáférési hiba | Azonos owner UID a két szolgáltatáson |
| MCP 401 bejelentkezés után | Aktív aszimmetrikus kulcs, tokenhook, pontos MCP URL/audience és client ID |
| OAuth redirect hiba | Az asszisztens pontos callbackje (Claude: `https://claude.ai/api/mcp/auth_callback`) és a Supabase Site URL |
| MCP 421 vagy Origin hiba | `MCP_PUBLIC_URL` pontosan egyezik-e a Cloud Run (vagy saját domain) címével |
| Az első kérés lassú | A Cloud Run nulláról indul; néhány másodperc után a következő kérések gyorsak |
| A draft nem érkezik vissza | Ugyanaz a backend/adatbázis, aktív ContentOps-kapcsolat, a kérés tényleges elküldése |

## Ellenőrzési határ és források

Helyben tesztelt: összevont ASGI-életciklus, discovery és 401 challenge, tulajdonos-/audience-/kliensellenőrzés, Claude- és ChatGPT-origin, login-visszatérés, consent oldal, readiness, a telepítő script próbafuttatása kitalált értékekkel, és a munkatér-átvitel SQLite-on (Postgresen a CI futtatja). A konténer buildjét a CI ellenőrzi. Az éles Cloud Run-, Supabase- és Claude OAuth-kör még nem futott; telepítés után a fenti átvételi próba szükséges.

Források: [Cloud Run árazás](https://cloud.google.com/run/pricing), [Supabase OAuth 2.1 Server](https://supabase.com/docs/guides/auth/oauth-server), [Supabase tokenhook](https://supabase.com/docs/guides/auth/oauth-server/token-security), [Claude egyéni connectorok](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp), [OpenAI OAuth-leírás](https://developers.openai.com/plugins/build/auth).
