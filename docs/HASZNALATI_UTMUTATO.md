# ContentOps – mire való, és hogyan használd?

A ContentOps a saját LinkedIn-szerkesztőséged: megőrzi az ötleteidet, a profilodat, a régi posztjaidat és a készülő szövegek változatait. A ChatGPT kutat és ír, az alkalmazás pedig tárolja a munkát és segít átnézni. A végső döntés és a publikálás nálad marad.

## Melyik részt mire használod?

| Rész | Feladata | Mikor használod? |
| --- | --- | --- |
| Webalkalmazás | Ötletek, profil, posztok, szerkesztés, review | Telefonon rögzítesz, böngészőben átnézel és javítasz |
| ChatGPT | Kutatás, szövegalkotás, átdolgozás | Egy ötletből teljes draftot vagy forrásokra épülő témát kérsz |
| MCP | Összeköti a ChatGPT-t az alkalmazás adataival | A ChatGPT kiolvassa a profilodat és visszamenti az eredményt |
| Python backend | Mentés, verziók, jóváhagyási szabályok | Automatikusan dolgozik a web és az MCP mögött |
| Supabase | Felhős PostgreSQL-adatbázis, bejelentkezés és OAuth | Több eszközről, saját fiókkal akarod elérni ugyanazt a műhelyt |
| Vercel | A Next.js webes felület tárhelye | Az alkalmazást stabil webcímen nyitod meg |
| Dockeres Python-tárhely | Futtatja a backendet és az MCP-t | A ChatGPT és a web akkor is eléri az adatokat, ha a géped ki van kapcsolva |
| LinkedIn | A tényleges közzététel és időzítés | A kész szöveget bemásolod és kézzel publikálod vagy időzíted |

A Supabase és a Vercel nem írja meg a posztot. A projekt nem hív modell-API-t, és nem kér OpenAI API-kulcsot. A tárhely és az adatbázis külön szolgáltatás a ChatGPT-előfizetéstől.

## 1. Első beállítás: ki vagy, és hogyan írsz?

A fejléc **személyikonja → Profil és korábbi posztok** ablakban add meg:

- mivel foglalkozol, milyen tapasztalatokra támaszkodhatsz;
- miről szeretsz írni és mi a célod a posztolással;
- néhány saját, már megírt posztod teljes szövegét és témáját.

Példa háttérre: „Python- és webfejlesztést tanulok. Saját projektek építésén keresztül mutatom meg, mit értettem meg és hol hibáztam. Nem szeretnék több szakmai tapasztalatot sugallni, mint amennyim ténylegesen van.” A saját tényeidet írd be, ne ezt tekintsd kész profilnak.

A **Hangprofil** fülön külön állítod be a stílusutasítást, a célközönséget és a nyelvet. Például: „Rövid bekezdések, konkrét megfigyelések, közvetlen hang. Ne legyen motivációs közhely vagy kötelező zárókérdés.”

**A profil és a posztgyűjtemény mentése külön művelet a hangprofil mentésétől.** Mindkét felületen nyomd meg a saját mentésgombot.

### Hogyan használja a régi posztjaidat?

Legfeljebb 50 posztot tárolhatsz. Minden posztnál kikapcsolható a **Használja írásmintaként** jelölő. Ettől megmarad a gyűjteményben, de nem kerül az alapértelmezett írási kontextusba.

Írás előtt a ChatGPT a következőket kapja az MCP-től:

- a szakmai hátteredet és a hangprofilodat;
- alapértelmezésben az első 5 engedélyezett régi posztot;
- az engedélyezett régi posztok teljes cím- és témalistáját;
- legfeljebb 5, az alkalmazásban jóváhagyott szövegmintát.

A host kérésére a minták száma gyűjteményenként 10-ig növelhető; a teljes gyűjteményt külön is lekérheti. Az újonnan hozzáadott poszt a lista elejére kerül. Ez nem modellbetanítás: a ChatGPT minden alkalommal a mentett kontextusból dolgozik. A minőséget a saját mintáiddal kell kipróbálni; nem garantált, hogy elsőre pontosan eltalálja a hangodat.

A régi posztokat bemásolod az alkalmazásba, vagy a csatlakoztatott ChatGPT-ben kéred a mentésüket. Automatikus LinkedIn-letöltés nincs.

## 2. Séta közben eszedbe jut valami

Nyisd meg az **Új ötlet** ablakot. Írd le néhány mondatban a felismerést; a telefon billentyűzetével diktálhatsz is. A cím opcionális.

**Mentés későbbre:** a gondolat bekerül a gyűjteménybe. Nem indul generálás, nem kell rögtön posztot készítened belőle.

**Mentés és draftkérés:** az ötlet először elmentődik. Ezután kapsz egy előkészített kérést, amely tartalmazza a tétel azonosítóját és a szükséges MCP-lépéseket. Másold be és küldd el a ContentOpshoz csatlakoztatott ChatGPT-beszélgetésben.

A gombnyomás és a másolás nem indít önálló AI-háttérfeladatot. A munka a ChatGPT-ben, az elküldött kérés után indul. A webre visszatérve, illetve látható lapon 15 másodpercenként az alkalmazás ellenőrzi az új változatokat.

## 3. Nincs konkrét ötleted, témát és forrást keresel

A kutatást a ChatGPT-ben kérd. Például:

> Nézd meg a ContentOpsban a profilomat és a korábbi posztjaim témáit. Keress három hozzám illő témát. Mindegyikhez adj elsődleges forrást, dátumot és egy indoklást, hogy miért lenne releváns nekem. Először csak javasolj, ne készíts posztot.

A kiválasztott témához kérj mentett kutatási jegyzetet és forráslinkeket a ContentOpsba, majd draftot. Saját kutatást a weben az **Új ötlet → Kutatás** módban is rögzíthetsz: téma, jegyzet és soronként egy forráslink szükséges.

Az app tárolja a forrásokat, de nem végez önálló webkeresést vagy automatikus forrásminősítést. A link megléte nem bizonyítja a szöveg igazságát. Átnézéskor ellenőrizd a konkrét állítást és a forrás dátumát.

## 4. Szerkesztés és visszajelzés

Válassz egy tételt az **Ötletek és szövegek** listából. A kereső a címekben keres; az állapotszűrők az ötleteket, draftokat, javítandó, kész és archivált tételeket különítik el.

A középső szerkesztőben kézzel is írhatsz teljes szöveget. Az **Új verzió mentése** új változatot hoz létre; az előző verzió megmarad. A verziósorban visszanézheted és összehasonlíthatod őket. A másolás a látható szöveget másolja.

Az **Átnézés → Mit változtatnál?** mezőben konkrét visszajelzést adj, majd válaszd a **Visszajelzés és draftkérés** műveletet. A visszajelzés elmentődik, a javítási kérést ismét a ChatGPT-ben kell elküldeni.

Példa: „A bevezetés túl általános. Induljon a konkrét hibámból; az utolsó bekezdés pedig ne adjon tanácsot másoknak.” Ha ez minden jövőbeli szövegre vonatkozó szabály, a hangprofilban is rögzítsd. Egyetlen draft visszajelzése nem válik automatikusan tartós személyes preferenciává.

## 5. Jóváhagyás és közzététel

A **vN jóváhagyása** mindig egy konkrét mentett szövegverzióra vonatkozik. Mentetlen módosítást, korábbi verziót vagy feloldatlan szerkesztési ütközést nem lehet jóváhagyni. Egy új változat mentése a korábbi jóváhagyást érvényteleníti.

A **Megjelenés** fülön megadhatod a tervezett időpontot. Ez egy belső terv; az alkalmazás nem fog magától posztolni. Másold ki a jóváhagyott változatot, nyisd meg a LinkedInt, és ott végezd el a közzétételt vagy időzítést.

Ezután a ContentOpsban igazold vissza, ami valóban megtörtént:

| Állapot | Jelentés |
| --- | --- |
| Jóváhagyott | A kiválasztott szöveg kész |
| Tervezett | Az alkalmazásban feljegyeztél egy kívánt időpontot |
| Külsőleg időzített | A LinkedInen ténylegesen beállítottad az időzítést és ezt visszaigazoltad |
| Publikált | A poszt ténylegesen megjelent és ezt visszaigazoltad |

A megjelenés után kézzel rögzítheted a megtekintéseket, reakciókat, hozzászólásokat és újramegosztásokat. Nincs automatikus LinkedIn-statisztikaletöltés.

## 6. Mi marad meg, és hol?

| Adat | Helyi használat | Felhős használat |
| --- | --- | --- |
| Mentett profil, régi poszt, ötlet, forrás, verzió, review | A backend SQLite-adatbázisában | A backend által használt Supabase PostgreSQL-adatbázisban |
| Ötletfelvétel és szerkesztő helyi munkapéldánya | Az adott böngészőben, fiókhoz kötve | Ugyanúgy az adott böngészőben; szerveroldali mentés előtt nem szinkronizálódik |
| Profilablak még nem mentett módosítása | Csak a nyitott űrlap állapotában | Ugyanúgy menteni kell; bezárás előtt figyelmeztet |

Ha a ChatGPT közben új verziót ment, miközben te szerkesztesz, az app jelzi az ütközést. Hasonlítsd össze a szövegeket, és dönts arról, melyikből dolgozol tovább. A profilgyűjtemény párhuzamos módosítása is ütközési hibát ad; mentés nélkül ne zárd be a saját változatodat, előbb másold ki, ha szükséges.

Az **Exportálás** JSON-fájlt készít a szerverre mentett munkatérből, beleértve a profilt és a régi posztokat. Ez kézi export, nem automatikus biztonsági mentés. A JSON visszaimportálására jelenleg nincs felület, és a helyi adatok nem költöznek át automatikusan a felhőbe.

Az **Archiválás** kiveszi a tételt az aktív munkából, az Archívum szűrő alatt megmarad. A **Napló** az adott tétel mentett műveleteit mutatja.

## 7. Helyi vagy telefonos használat?

Helyben a web és a Python backend is fusson. A `127.0.0.1` cím mindig azt az eszközt jelenti, amelyiken megnyitod: a telefonról ez nem a számítógépedre mutat. A jelenlegi helyi indítás csak a számítógépen érhető el.

A stabil, többeszközös használathoz telepítsd a szolgáltatásokat a [telepítési útmutató](DEPLOYMENT_HU.md) alapján. A webet ugyanazzal a tulajdonosi fiókkal használd minden eszközön. Az AI-folyamat csak a működő ChatGPT–ContentOps kapcsolat után tesztelhető végig.

## Javasolt első saját menet

Profil + néhány saját poszt → egy valós ötlet mentése → draftkérés ChatGPT-ben → kézi átnézés → egy konkrét javítás → jóváhagyás → LinkedInre másolás.

Az első próbához használd a [rövid tesztforgatókönyvet](FIRST_TRIAL_HU.md). A legértékesebb visszajelzés egy konkrét mondat, amely nem úgy hangzott, mint te, és a saját átiratod mellé téve.
