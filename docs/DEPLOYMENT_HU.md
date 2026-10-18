# Éles ContentOps: telepítés és ChatGPT-kapcsolat

**Előkészített fájlok és ellenőrző parancs:** [deploy/README.md](../deploy/README.md). **Felhasználói útmutató:** [mit mire és hogyan használj](HASZNALATI_UTMUTATO.md).

Az alkalmazás modell-API nélkül működik. A szöveget a ChatGPT készíti; az MCP tárolja és kezeli a munkafolyamatot. A ChatGPT-előfizetés mellett a webes tárhely és az adatbázis külön infrastruktúra. A fiókodban elérhető egyéni MCP/OAuth kapcsolatot a bekötés előtt ellenőrizd.

## 1. Supabase: adatbázis és saját belépés

1. Hozz létre egy Supabase-projektet. Authentication → Users alatt hozz létre saját, megerősített email-címmel és jelszóval egy felhasználót. Jegyezd fel a **User UID** értéket. A nyilvános regisztrációt kapcsold ki.
2. A JWT Signing Keys beállításban használj **ES256 vagy RS256** aktív aláírókulcsot. A backend JWKS alapján ellenőriz; HS256-ot nem fogad el.
3. A SQL Editorban futtasd a `deploy/supabase-storage.sql` fájlt. Ez egy külön `contentops` sémát készít. Ezt **ne** add a Supabase Data API által elérhető sémákhoz.
4. A Connect panelből másold ki a PostgreSQL-kapcsolatot. A javasolt csatlakozási mód a **Session pooler**. A kapcsolat végére add hozzá: `?sslmode=require&options=-c%20search_path%3Dcontentops`. Ha már van query, az első `?` helyett `&` kell. A jelszó speciális karaktereit URL-kódolni kell. A DSN titok, csak a backend környezeti változóiba kerülhet.
5. Jegyezd fel a Project URL-t és a **publishable key** értéket is. A frontend nem kér `service_role` kulcsot.

Az új felhős adatbázis üres. A helyi SQLite-tartalom nem költözik át automatikusan: az alkalmazás Exportálás gombjával őrizd meg a helyi anyagaidat. Ne töröld a helyi adatbázist; az import/migráció külön művelet.

## 2. Címek és OAuth-kliens

Két stabil HTTPS-cím kell: egy a Next.js webnek, egy a Python backendnek. Példák a továbbiakban: `https://WEB_HOST` és `https://BACKEND_HOST` — ezeket mindenhol cseréld ki.

Supabase Authentication → OAuth Server:

- Engedélyezd az OAuth 2.1 servert.
- Authorization Path: `/oauth/consent`.
- URL Configuration → Site URL: `https://WEB_HOST`.
- Regisztrálj egy dedikált OAuth-klienst a ContentOps ChatGPT-kapcsolatához. Ehhez az implementációhoz **előre regisztrált kliens** kell; dinamikus regisztrációt nem szükséges engedélyezni.
- Őrizd meg a client ID-t és — bizalmas kliensnél — a client secretet. A secret csak a ChatGPT OAuth-beállításába kell, nem a frontend kódjába.
- A redirect URI-t a ChatGPT kapcsolatkezelőjében megjelenő **pontos** callback-címre állítsd. Ne találj ki callback ID-t és ne használj wildcardot. Ha a cím csak a kapcsolat felvétele során jelenik meg, a kliens redirect URI-ját akkor véglegesítsd, és indítsd újra a kapcsolódást.
- A kliens számára engedélyezd a szolgáltató által hirdetett OIDC scope-okat (pl. `openid`, `email`, `profile`), amelyeket a ChatGPT kér.

## 3. MCP-token beállítása

A `deploy/supabase-mcp-token-hook.sql` fájlban cseréld ki a két helyőrzőt:

- `REPLACE_WITH_MCP_OAUTH_CLIENT_ID`: az előző pont kliensazonosítója.
- `https://REPLACE_WITH_BACKEND_HOST/mcp`: a pontos publikus MCP URL.

Futtasd a SQL Editorban, majd Authentication → Hooks → Custom Access Token alatt válaszd ki a `public.contentops_access_token_hook` függvényt és engedélyezd. Ha már van saját tokenhookod, annak logikájába illeszd be ezt a klienságat; ne veszítsd el a meglévő szabályokat.

Ez a dedikált OAuth-kliens tokenjében az MCP URL-re állítja az `aud` értéket. A normál webes bejelentkezés továbbra is `authenticated` audience-t használ. A backend külön ellenőrzi az issuer, audience, lejárat, tulajdonos és MCP client ID értékét. Hibás hook esetén a kapcsolat 401-et kap; ne kapcsold ki az ellenőrzést.

## 4. Python backend telepítése

Docker futtatására alkalmas HTTPS tárhelyen a repository **`backend` könyvtárát** állítsd be build contextként/root directoryként. Dockerfile: `Dockerfile`. Egyetlen szolgáltatás kell; a konténer a szolgáltató `PORT` változóját használja, egyébként a 8000-es portot.

Környezeti változók:

```dotenv
APP_ENV=production
AUTH_MODE=supabase
CONTENTOPS_DATABASE_URL=IDE_KERUL_A_TELJES_PRIVAT_POSTGRES_DSN
SUPABASE_URL=https://PROJECT.supabase.co
SUPABASE_JWT_AUDIENCE=authenticated
CONTENTOPS_OWNER_USER_ID=SAJAT_USER_UID
MCP_OAUTH_CLIENT_ID=REGISZTRALT_KLIENS_ID
MCP_PUBLIC_URL=https://BACKEND_HOST/mcp
FRONTEND_ORIGIN=https://WEB_HOST
MCP_HOST=0.0.0.0
```

Health check path: **`/api/ready`**. A `/api/health` csak a folyamat állapotát jelzi, a `/api/ready` az adatbázist is olvassa. A tárhely őrizze meg az eredeti publikus Host fejlécet, és továbbítsa az Authorization fejlécet.

Egyetlen ASGI-folyamat kezeli a webes API-t (`/api`), az MCP-t (`/mcp`) és az OAuth discovery végpontokat. Kézi indítóparancs Docker nélkül, a `backend` könyvtárból:

```sh
uv sync --frozen --no-dev
uv run uvicorn app.deployment:create_app --factory --host 0.0.0.0 --port 8000 --no-access-log
```

Az adatbázistáblák induláskor jönnek létre a DSN-ben megadott sémában. A `production` beállítás nem engedi az autentikáció nélküli helyi módot vagy a tartós PostgreSQL-beállítás nélküli indulást.

## 5. Next.js web telepítése Vercelre

Importáld a repositoryt, a projekt gyökere a repository gyökere; framework Next.js. Környezeti változók:

```dotenv
PYTHON_BACKEND_URL=https://BACKEND_HOST/api
NEXT_PUBLIC_SUPABASE_URL=https://PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=SUPABASE_PUBLISHABLE_KEY
CONTENTOPS_OWNER_USER_ID=SAJAT_USER_UID
MCP_OAUTH_CLIENT_ID=REGISZTRALT_KLIENS_ID
```

A `/api` utótag kötelező az összevont backendnél. A két `NEXT_PUBLIC_` értéket már a build előtt állítsd be, majd telepíts újra. A két utolsó változó szerveroldali; ugyanaz legyen, mint a Python backendnél. A végleges domain egyezzen a Supabase Site URL-lel és a backend FRONTEND_ORIGIN értékével.

Nyisd meg a webet telefonon, lépj be, ments egy tesztötletet. Asztali böngészőből ugyanazzal a fiókkal belépve látnod kell ugyanazt az ötletet.

## 6. ChatGPT-bekötés és átvételi próba

A fiókod egyéni app/plugin/MCP-kapcsolatkezelőjében add meg:

- MCP URL: `https://BACKEND_HOST/mcp`.
- Auth: OAuth, az előre regisztrált kliens ID-jával és szükség esetén secretjével.
- A felület által megadott callbacket másold vissza a Supabase-kliens redirect URI-jai közé, ha ezt még nem tetted meg.

Kapcsolódáskor a ContentOps belépési oldalára, majd a **Hozzáférés a műhelyedhez** oldalra kell jutnod. Itt kifejezetten engedélyezd a kapcsolatot. Ez a hozzáférési döntés nem posztjóváhagyás.

Átvételi próba:

1. Kérd a ChatGPT-től a mentett ContentOps-ötletek listázását. A weben létrehozott tesztötletnek meg kell jelennie.
2. A weben válaszd a Mentés és draftkérés műveletet. A kérést másold és küldd el a csatlakoztatott beszélgetésben.
3. Visszatérve a webre meg kell jelennie egy új, még nem jóváhagyott draftnak.
4. Kérj egy módosítást, ellenőrizd a verziókat, és csak a megfelelő mentett verziót hagyd jóvá.
5. Próbálj MCP-hívást token nélkül: ennek 401-et kell adnia. Más Supabase-felhasználó ne férjen hozzá a műhelyhez.

## Hibakeresés

| Tünet | Ellenőrizendő |
| --- | --- |
| Backend nem indul | Production env, PostgreSQL DSN, séma, tulajdonos és client ID |
| Web nem éri el az API-t | PYTHON_BACKEND_URL végén `/api`, publikus backend elérhetőség |
| Bejelentkezés után hozzáférési hiba | Azonos owner UID a két szolgáltatáson |
| MCP 401 bejelentkezés után | Aktív aszimmetrikus kulcs, tokenhook, pontos MCP URL/audience és client ID |
| OAuth redirect hiba | ChatGPT által megjelenített pontos callback és Supabase Site URL |
| MCP 421 vagy Origin hiba | Publikus Host fejléc, MCP_PUBLIC_URL, reverse proxy beállítása |
| A draft nem érkezik vissza | Ugyanaz a backend/adatbázis, aktív ContentOps kapcsolat, kérés tényleges elküldése |

## Ellenőrzési határ és források

Helyben tesztelt: összevont ASGI-életciklus, discovery és 401 challenge, tulajdonos-/audience-/kliensellenőrzés, login-visszatérés, consent oldal, readiness. A konténer buildje és az éles Supabase/ChatGPT OAuth-kör ezen a gépen nem futott; telepítés után a fenti átvételi próba szükséges.

A bekötés az [OpenAI Docs OAuth-leírását](https://developers.openai.com/plugins/build/auth), a [Supabase OAuth-beállításait](https://supabase.com/docs/guides/auth/oauth-server/getting-started) és a [Supabase tokenhook dokumentációját](https://supabase.com/docs/guides/auth/oauth-server/token-security) követi. A callbacket mindig az aktuális ChatGPT-felületről másold.
