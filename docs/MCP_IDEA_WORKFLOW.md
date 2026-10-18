# Ötletből átnézhető poszt, MCP-n keresztül

## Használat

Első használatkor nyisd meg a fejléc **Profil és korábbi posztok** gombját (személy ikon), vagy a Hangprofil panel ugyanezen nevű gombját. Írd be a szakmai hátteredet, a céljaidat és a témáidat, majd másolj be néhány saját korábbi posztot. Mindegyikhez tartozik cím, témaleírás és szöveg; a „Használja írásmintaként” kapcsolóval kizárhatod az elavult stílusmintákat. Legfeljebb 50 poszt tárolható. Mentsd a gyűjteményt.

A `contentops_get_writing_context` alapértelmezésben az első 5 engedélyezett korábbi posztot, legfeljebb 5 jóváhagyott alkalmazásbeli példát, a hangprofilt, a szakmai hátteret és az összes engedélyezett poszt címét/témáit adja vissza. A limit legfeljebb 10 lehet gyűjteményenként. Az újonnan hozzáadott poszt a gyűjtemény elejére kerül. Ez kontextusátadás, nem modellbetanítás vagy automatikus LinkedIn-szinkronizálás.

A ChatGPT-ben is megadhatod a hátteredet és bemásolhatod a régi írásaidat: kérd, hogy mentse őket a ContentOps szerzői memóriájába. A host először a `contentops_get_author_memory` eszközzel olvassa a teljes gyűjteményt, majd a `contentops_update_author_memory` eszközzel, a meglévő bejegyzéseket és az aktuális revision értéket megőrizve ment. Az egész gyűjtemény része a munkatér JSON-exportjának. Kitalált vagy frissen generált draft nem kerülhet automatikusan a valódi korábbi posztok közé.

1. Az **Új ötlet** ablakba írd vagy a telefon billentyűzetével diktáld be a gondolatot. A cím opcionális. A félbehagyott jegyzet ezen a böngészőn, az adott fiókhoz kötve megmarad; más eszközre csak a szerveroldali mentés után jut el.
2. **Mentés későbbre:** megőrzi az ötletet, és itt megáll. **Mentés és draftkérés:** elmenti, majd megmutatja a ChatGPT-be másolható kérést.
3. Másold be és küldd el a kérést egy olyan ChatGPT-beszélgetésben, ahol a ContentOps MCP elérhető. A host a megadott azonosítóval olvassa az ötletet és a hangprofilt, elkészíti a teljes szöveget, majd új verzióként menti. Nem kell újra létrehoznia az ötletet.
4. A webes műhely visszatéréskor és látható lapon 15 másodpercenként frissül. Olvasd át a szöveget, szerkeszd kézzel, vagy adj visszajelzést, és kérj új változatot ChatGPT-ben.
5. A konkrét mentett verziót hagyd jóvá. A jóváhagyás nem publikál: a LinkedInre való átadás külön, kézi művelet.

A webes gomb nem indít önálló ChatGPT-háttérfeladatot. A generálás a csatlakoztatott beszélgetésben, a kérés elküldése után történik. Az alkalmazás nem tartalmaz modell-API-hívást vagy modell-API-kulcsot. A használni kívánt host fiókjának MCP-elérését és bejelentkezését külön kell ellenőrizni; a helyi webalkalmazás ezt nem tudja igazolni.

## Mentés és verziók

- A böngésző helyi munkapéldányt őriz dokumentumonként és fiókonként. Ha ez nem elérhető, a felület jelzi. Ez nem teljes offline szinkronizáció.
- Ha közben az MCP új verziót ment, a saját szerkesztés nem vész el: összehasonlíthatod a változatokat, megnyithatod a szerver példányát, vagy a különbségek átnézése után megtarthatod a sajátodat.
- A web és a workflow skill a mentés alapjául szolgáló verziót is elküldi. Elavult alapból történő írás ütközési hibát ad. A régi MCP-kliensek opcionális paraméter nélkül továbbra is kompatibilisek.
- Nem mentett módosítás, régi verzió megtekintése vagy feloldatlan ütközés mellett a jóváhagyás tiltott.
- Bizonytalan hálózati eredmény után az ismételt mentés ugyanazt a műveletazonosítót használja, hogy ne keletkezzen duplikált ötlet vagy verzió.

## Ellenőrzés és határok

A változtatásokat frontend komponens-, állapotkezelési és kliens-tesztek, valamint Python API-, MCP-, konkurencia- és repository-tesztek fedik. A külön tesztadatbázison végzett böngészős próba lefedte az ötletmentést, a kérés másolását és az MCP-n visszamentett draft automatikus megjelenését. A mobilnézetet 390 × 844-es méretben ellenőriztük.

A PostgreSQL-életciklusteszt külön teszt-DSN-t igényel. A helyi ellenőrzésben ez kihagyott teszt; a GitHub Actions konfiguráció PostgreSQL 17 szolgáltatáson futtatja. Az éles Supabase-, távoli MCP- és ChatGPT-fiókos működés, valamint a telepítés nincs helyben igazolva.

A releváns témák és megbízható források felfedezése továbbra is a host kutatási feladata. A kutatási jegyzet és forráslinkek tárolhatók, de automatikus témaválogató és forrásminősítő rendszer ebben a változtatásban nem készült.
