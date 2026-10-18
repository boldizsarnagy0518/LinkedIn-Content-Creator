# ContentOps – termék-, UX- és technikai értékelés

Dátum: 2026-09-08. Az értékelés a munkakönyvtár jelenlegi, jelentős részben még nem commitolt állapotáról szól.

> **Későbbi döntés és implementáció:** a felhasználó MCP-n keresztül, a saját ChatGPT-előfizetésével akar dolgozni. A lentebb szereplő szerveroldali modellgenerálási és háttérfeladat-javaslatokat ez felülírja: nem építünk modell-API-t. Az elkészült út: gyors ötletmentés → másolható ChatGPT-kérés → host által MCP-n mentett draft → kézi review. A mentési versenyhelyzetek, Postgres batch-írás és szerkesztőállapot hibái javítva; a lenti leírás az eredeti auditot őrzi. Aktuális használat és ellenőrzési határok: [MCP ötletfolyamat](MCP_IDEA_WORKFLOW.md).

## Vezető megállapítás

A projektben erős mérnöki alap van, de a jelenlegi termék a felhasználó problémáinak későbbi szakaszát kezeli a legjobban. A felhasználó két központi igényt erősített meg: **releváns témák és megbízható források megtalálása**, valamint **saját, gyakran séta közben felmerülő ötletek gyors rögzítése és igény szerint közel kész drafttá alakítása néhány percen belül**. A puszta ötletmentésnek önálló, generálást nem indító használati esetként is működnie kell.

A javasolt termékígéret: **a saját ötleteimből és a nekem releváns, ellenőrizhető témákból gyorsan átnézhető, saját hangomon megírt posztot készít; az ötleteimet későbbre is megőrzi.**

A meglévő szerkesztési folyamatot megtartanám. A megbízhatósági hibák javítása után először a rövid, mobilon is végigvihető ötlet → draft → review utat építeném meg. A kutatási beérkező lista a másik fő belépési pont, ugyanabba a szerkesztési folyamatba. Ez a sorrend a felhasználó későbbi pontosítását is figyelembe veszi.

## Mit ellenőriztem?

- README, projektkontextus, ADR-ek, MCP értékelési terv.
- Next.js oldalak, komponensek, állapotkezelés, CSS, BFF és API-kliens.
- Python service, repository, adatmodellek, API és MCP adapterek, autentikáció és tesztek.
- Helyi alkalmazás böngészőben: 1280 × 720-as asztali nézet, meglévő ötlet, szűrők és ötletfelvételi modal. A meglévő tartalmat nem módosítottam.
- `npm run check`: lint, typecheck, 6 frontend szerződésteszt és production build sikeres.
- `uv run pytest`: 19 sikeres teszt.
- `uv run ruff check app tests`: sikeres.
- Telepített psycopg API-jának helyi vizsgálata.
- Két párhuzamos művelet kontrollált összefuttatása külön, ideiglenes SQLite-adatbázison.

Nem futott valódi Supabase/Postgres integrációs teszt, éles deploy, távoli MCP-bejelentkezés vagy teljes böngészős életciklusteszt. A mobilértékelés a CSS felépítésén alapul. A zöld tesztek ezekre nem bizonyítékok.

## Mi értékes már most?

1. **Valós üzleti szabályok:** változtathatatlan szövegverziók, pontos verzióhoz és hashhez kötött jóváhagyás, visszavonás, visszakövethető események.
2. **Két használati felület:** a web és az MCP ugyanazt a tartós állapotot kezeli. Ez életszerűbb portfóliótörténet, mint egy önmagában álló generáló űrlap.
3. **Használható helyi indulás:** SQLite és külön modell-előfizetés nélkül futtatható alkalmazásbackend.
4. **Tudatos scope:** egyszemélyes termék, explicit publikálási visszaigazolás, dokumentált architekturális döntések.
5. **Felismerhető vizuális irány:** visszafogott papírszínek, szerkesztőségi tipográfia, lista–kézirat–ellenőrző panel. A látott felületben nincs tipikus generált SaaS-landingpage megjelenés.

## A felhasználónak megfelelő munkafolyamatok

### Saját ötlet: elmentés vagy azonnali draft

Mobilon megnyitom az alkalmazást, és egyetlen mezőbe leírom az ötletet. A telefon billentyűzetének diktálása kezdetben elegendő lehet; saját hangrögzítés és átírás külön, később validálandó funkció.

Két világos művelet:

- **Mentés későbbre:** az eredeti jegyzet biztonságosan bekerül az Ötletek közé, nem indul AI-munka. Később bármelyik ötletből elindítható a draftkészítés.
- **Draft készítése:** először ugyanúgy elmenti az eredeti ötletet, majd elindítja a szöveg elkészítését a saját hangprofilommal és korábbi elfogadott példáimmal.

Az AI teljes első változatot készít. Megőrzi a saját mondanivalómat, nem talál ki helyettem személyes élményt, számot vagy eredményt. Nem kötelező minden ötletet kutatássá alakítani: személyes megfigyelésből közvetlenül is készülhet poszt. Külső tényállítás esetén ellenőrzés és forrás kell, vagy a bizonytalan részt egyértelműen jelölni kell.

Ha az alapgondolat érthető, a rendszer ne kezdjen hosszú kérdéssorba. Legfeljebb egy lényegi pontosító kérdést tegyen fel, ha anélkül félreértené a mondanivalót. Az opcionálisan hiányzó részletek ne akadályozzák az első draft elkészülését.

A review mobilon: elolvasom → közvetlenül javítom vagy rövid instrukciót adok → elfogadom. Például „rövidebben”, „kevésbé formálisan”, „a saját példámat tedd előre”. A korábbi változat megmarad. Az elfogadás a konkrét mentett verziót teszi készre; a LinkedInre történő publikálás külön lépés.

### Mit változtat ez az architektúrán?

A jelenlegi rendszer szándékosan nem futtat modellt: a host ír, a backend állapotot tárol. A „Copy task prompt” lépés nem valósítja meg az alkalmazáson belüli, egygombos draftkészítést. Az MCP eszközfelület önmagában nem indít modellmunkát.

Az új igényhez felül kell vizsgálni a modell nélküli backendről szóló ADR-t. Javaslat: a webes alkalmazás mögött tényleges, szerveroldali generálási végrehajtás legyen; az MCP továbbra is ugyanazt a domainlogikát használó alternatív felület maradjon. Ez termék- és architektúrajavaslat, nem megvalósított integráció vagy kiválasztott szolgáltató.

Mivel séta közben lezárhatom a telefont vagy eltűnhet a kapcsolat, a generálás tartós feladatként fusson: `queued`, `running`, `completed`, `failed` állapottal és ismételhető, duplikációt elkerülő indítással. A böngésző bezárása ne legyen azonos a munkafolyamat megszűnésével. A lezárt böngésző mellett történő futást az implementációban valóban biztosítani és tesztelni kell.

A feladat az ötlet és a felhasznált kontextus rögzített változatára hivatkozzon. Ha közben kézzel új szöveget mentek, az AI eredménye ne írja felül vagy léptesse észrevétlenül hátrébb azt; összehasonlítható javaslatként érkezzen. A generálási státusz különüljön el a tartalom szerkesztési státuszától.

A gyenge hálózat miatt a gyorsrögzítéshez helyi helyreállítás és egyértelmű „eszközön mentve / szinkronizálva” visszajelzés is indokolt. A jelenlegi PWA ezt még nem nyújtja. Push értesítés később lehet hasznos, de az első verzióhoz elég, ha visszatéréskor az elkészült draft azonnal megtalálható.

A „pár perc” cél mérendő termékelvárás, nem garantált futásidő. Külön mérjük az ötlet rögzítésétől az első review-képes szövegig és az elfogadásig eltelt időt, valamint a szükséges átírások számát.

### Kutatással induló út

1. Beállítom az érdeklődési témáimat, célközönségemet, kívánt szakmai mélységet és kizárt témáimat.
2. Megnyitok egy rövid, priorizált témalistát. Minden javaslatnál látom, mi történt, miért releváns nekem, és miből tudjuk.
3. Kiválasztok egy témát, elolvasom az állításokat és forrásokat, hozzáadom a saját tapasztalatomat vagy álláspontomat.
4. Kézzel vagy a csatlakoztatott modellel elkészítem a vázlatot/szöveget.
5. Átnézem a változásokat, jóváhagyom a konkrét mentett változatot, majd átviszem LinkedInre.
6. Feljegyzem az eredményt és azt, érdemes-e hasonló témával újra foglalkozni.

A kutatási út első sikerélménye a jó témaválasztás. A saját ötlettel induló úté az, hogy a rövid jegyzetből gyorsan átnézhető szöveg lesz. A két belépési pont ugyanazt a mentést, verziókezelést és review-t használja.

## Először javítandó hibák

### P1 – Postgresen a tartalomfelvétel hibás metódust hív

Hely: `backend/app/content/repository.py:77`, valamint `:306`.

Az adapter `self.connection.executemany(...)` hívást használ. A telepített psycopg 3.3.4 `Connection` osztályán ez nem létezik; a `Cursor` osztályon igen. Ezt helyben ellenőriztem. A tartalom létrehozása üres forráslistával is meghívja ezt az ágat, így az ötlet- és kutatásfelvételt is érinti.

A jelenlegi teszt saját `RecordingConnection` objektuma megvalósítja ezt a nem létező connection-metódust, ezért elfedi a hibát. Valódi Postgres-kapcsolat nélkül is bizonyítható az API-eltérés; éles adatbázison a teljes folyamatot még külön ellenőrizni kell.

Javítás: kurzoron végzett batch írás, majd ugyanazon capture → verzió → review → publikálási folyamat integrációs futtatása SQLite-on és Postgresen.

### P1 – A jóváhagyás és a párhuzamos mentés nem alkot atomi döntést

Hely: `backend/app/content/repository.py:344`, `:441`, `:481`.

A jóváhagyás beolvassa az aktuális verziót, ellenőrzi, majd később azonosító alapján átállítja a tétel státuszát. Közben egy másik kliens új verziót menthet.

Izolált SQLite-próbában a jóváhagyás első olvasása után egy másik kapcsolaton elmentettem v2-t, majd továbbengedtem a jóváhagyást. Az eredmény:

```text
Concurrent approval result: approved
Current version: 2
Active approval: None
```

Ez bizonyított belső állapotellentmondás. Nem bizonyít automatikus publikálást: a további `active_approval` ellenőrzések megállíthatják a következő lépést.

Javítás: explicit tranzakciós stratégia és verziófeltételes írás; ahol szükséges, sorzárolás. A szerkesztéshez `expected_current_version_id` is indokolt, hogy egy régi ablakból mentett szöveg ne lépjen észrevétlenül az időközben elkészült verzió elé. A Postgres olvasási izolációja önmagában nem helyettesíti ezeket az invariánsokat: [PostgreSQL tranzakciós izoláció](https://www.postgresql.org/docs/current/transaction-iso.html).

A próba eredménye létrejött; az ideiglenes adatbázis automatikus takarítása nyitva maradt SQLite-kapcsolat miatt hibázott. A folyamat lezárulta után a tesztadatokat eltávolítottam. A SQLite-kapcsolatok explicit lezárását is érdemes rendezni: a connection context manager tranzakciót kezel, a kód nem hív külön `close()`-t.

### P1 – A látható szöveg és a jóváhagyás célja eltérhet

Hely: `app/_components/draft-editor.tsx:48`, `:69`; `app/_components/contentops-workspace.tsx:71`.

A szerkesztő saját állapotában tárolja a kiválasztott történeti verziót és a nem mentett szöveget. A jóváhagyó panel mindig a legutolsó mentett verziót használja, függetlenül attól, mit nézek vagy írok a középső panelen. A másolás szintén a legutolsó mentett szöveget veszi (`draft-editor.tsx:89`).

Javítás: közös szerkesztési/review állapot; történeti nézetben és nem mentett módosításnál egyértelmű tiltás vagy mentésre vezető lépés. A gomb nevezze meg a célt, például „v3 jóváhagyása”. A másolásnál legyen világos, hogy a szerkesztett vagy jóváhagyott változatot másoljuk.

### P1 – Nem mentett szöveg elveszhet

Hely: `app/_components/draft-editor.tsx:39`, `:69`.

A dokumentum-/verzióváltás újrainicializálja vagy felülírja a lokális szöveget; nincs dirty-state védelem vagy helyreállítás. A kód alapján egy másik tételre kattintás, történeti verzió kiválasztása vagy egy új MCP-verzió betöltése eldobhatja a munkát.

Javítás: automatikusan helyreállítható munkapéldány, mentési állapot, navigációvédelem. A munkapéldány automatikus mentését külön kell választani az explicit, változtathatatlan verzió létrehozásától; ne legyen minden leütés auditált új verzió.

### P2 – Az aktív szűrőre kattintás beragasztja a betöltést

Hely: `app/_hooks/use-contentops-workspace.ts:100`.

Böngészőben reprodukálva: a már aktív „Active” gombra kattintva a lista tartósan „Loading queue” állapotba kerül. A handler beállítja a loadingot, de az azonos filterérték miatt a betöltő effect nem indul újra.

Javítás: azonos szűrőnél korai visszatérés vagy külön, explicit újratöltési művelet. Regressziós komponens-/böngészőteszt szükséges.

### P2 – Az első szöveghez kötelező kerülőút tartozik

Hely: `app/_components/draft-editor.tsx:176`.

Verzió nélküli tételnél csak „Copy task prompt” van; nincs kézi elsődraft-szerkesztő. Ezt a futó felületen is láttam. A backend már tud első verziót menteni.

Javítás: „Megírom / Beillesztem a szöveget”, mellette opcionális modellmunkafolyamat. A csatlakozás állapota, a szükséges következő lépés és az elkészült verzió betöltése legyen érthető. Az első értékhez ne legyen kötelező az integráció beüzemelése.

### P2 – A publikálás UI-ja szűkebb a backendnél

Hely: `app/_components/workflow-inspector.tsx:236`.

A backend `planned` és `scheduled_externally` állapotból is enged publikálást visszaigazolni. A felületen a „Mark published” csak utóbbinál jelenik meg. Aki rögtön posztol, felesleges időzítési visszaigazolásra kényszerül. Terv nélküli, már megtörtént publikálásra sincs egyszerű út; a terv létrehozása jövőbeli időpontot igényel.

Javítás: külön „Most közzéteszem” és „Későbbre tervezem” út. Tárolható poszt-URL és tényleges publikálási idő, explicit felhasználói visszaigazolással.

Ha egy LinkedInen már időzített szöveg belső terve szerkesztés miatt törlődik, tartós teendő jelezze, hogy a külső időzítést kézzel is ellenőrizni kell. A belső állapotváltozás önmagában nem módosítja a LinkedInt.

### P2 – Az eredmények beírhatók, de nem olvashatók vissza érdemben

Hely: `app/_components/workflow-inspector.tsx`, `types/content.ts`.

A szerver és a frontend adatmodellje tartalmaz `performanceSnapshots` adatokat. A felület űrlapot ad a felvételhez, de nem rendereli a korábbi számokat és megfigyeléseket. Az eseménynaplóban a rögzítés ténye látható, az eredmény nem.

Javítás: posztonként egyszerű időrendi snapshotlista. Összesített elemzés később, már valódi adatokkal.

## További műszaki és UX-adósság

- A keresés csak az utolsó 100 betöltött tétel címében keres. Nincs lapozás, teljes szöveges keresés vagy témák szerinti visszakeresés.
- Az aszinkron tételkiválasztás nem védi ki a fordított sorrendben beérkező válaszokat. A review/publish űrlapok lokális állapota dokumentumváltáskor megmaradhat.
- A kliens minden új próbálkozásnál új idempotenciakulcsot készít; timeout utáni kézi ismétlés így új művelet lehet. A kulcs tartozzon a logikai művelethez, és annak újrapróbálásakor maradjon meg.
- A `Europe/Budapest` felirat hardcode-olt, a dátumkezelés részben a böngésző lokális időzónáját használja. Külföldi használatnál ez félrevezető lehet.
- A modalból a fókusz Tab billentyűvel kijutott a háttérben lévő Next.js Dev Tools gombra. A kódban nincs fókuszcsapda vagy inert háttér. Javítási referencia: [W3C modal dialog minta](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).
- A tartalomcím, források és forrásjegyzetek utólagos karbantartása hiányos; archiválás után nincs visszaállítási művelet.
- Az alkalmazási szolgáltatás sok helyen csak validál és továbbít, miközben a munkafolyamat-szabályok az 1000+ soros SQL repositoryban vannak. Közös domainhibák és explicit állapotátmenetek javítanák az áttekinthetőséget, a tranzakciós garanciákat az adattárolási határon megtartva.
- A táblák induláskori `CREATE TABLE IF NOT EXISTS` létrehozása nem kezeli a jövőbeni sémaváltozásokat. A kutatási modell bővítése előtt kell verziózott migráció.
- A repóban nem találtam CI-konfigurációt vagy komponens-/E2E-teszteket. A meglévő 6 frontendteszt adatnormalizálást ellenőriz.
- A PWA service worker statikus asseteket cache-el, de ettől az alkalmazás még nem biztosít offline ötletmentést és szinkronizálást.

## A következő nagy termékfejlesztés: kutatási beérkező lista

### Személyes kutatási profil

A meglévő hangprofil mellé külön kutatási preferenciák kellenek: témák, közönség, szakmai mélység, nyelvek, kizárt témák, kedvelt források, frissességi igény. Ezek más célt szolgálnak, mint az írás stílusa.

### Rövid, magyarázható témajavaslatok

Kezdésnek alkalmanként 3–5 témát mutatnék. Egy javaslat tartalma:

- Mi történt vagy milyen kérdés érdekes?
- Miért illik a témáimhoz és a célközönségemhez?
- Mely ellenőrizhető állításokra épül?
- Mely források támasztják alá, és mikoriak?
- Milyen saját nézőponttal tudnék hozzátenni?
- Miről írtam már hasonlót?

Műveletek: kiválasztás, későbbre mentés, elutasítás rövid indokkal. A „túl általános”, „nem az én közönségem” vagy „már írtam róla” visszajelzés konkrét bemenet a következő kutatáshoz. Kezdetben ehhez nem kell tanuló rangsorolórendszer.

### A linkgyűjteménytől az ellenőrizhető állításokig

A mostani kutatásmodell témát, szabad szöveges jegyzetet és URL-listát tárol. A `title` és `note` forrásmezők léteznek, de a capture út `NULL` értékkel tölti őket. Ez megőrzi a hivatkozásokat, de nem mondja meg, melyik állítás melyik forráson alapul.

Javasolt minimális adatok: forráscím, kiadó/szerző ha ismert, publikálási és hozzáférési dátum, elsődleges/másodlagos jelleg, rövid bizonyító részlet vagy összefoglaló; továbbá az állítások kapcsolata a forrásokhoz és az ellenőrzés állapota. Ismeretlen adat maradjon ismeretlen. Egy modelltől kapott forrásminősítés nem azonos emberi ellenőrzéssel.

Fontosabb egy világos indoklás, mint egy megalapozatlan „92/100 megbízhatóság” pontszám. A forrásnézet mutassa az ellentmondásokat és a hiányzó bizonyítékot is. A draftból legyen megnyitható a releváns állítás és annak forrása.

### Fokozatos megvalósítás

Első körben maradhat a kutatás a jelenlegi host modellben; a ContentOps kapjon strukturált kutatási csomagot MCP-n, saját profilból dolgozva, majd azt jó felületen lehessen értékelni. Ez kihasználja a meglévő architektúrát.

Ha a kézi indítás a használat során akadállyá válik, akkor jöhet időzített, néhány kiválasztott RSS/API-forrásból dolgozó begyűjtés, futási előzménnyel és duplikátumszűréssel. Ez jövőbeli termékjavaslat, jelen értékelés nem hozott létre automatizációt. Forrásoldalak tartalma adat legyen, soha ne munkafolyamatot engedélyező utasítás.

## UI-irány: a meglévő karakter megtartása, jobb hierarchia

A látott felület karakteres, de a nagy üres területek, apró címkék és a „host model”, „exact-version review”, illetve hash típusú részletek inkább a belső működést hangsúlyozzák. A professzionális hatást az olvashatóság és a kiszámítható interakció fogja tovább erősíteni.

- Fő navigáció: **Ötletek / Kutatás / Szövegek / Megjelenések**, mobilon a ritkább műveleteket másodlagos helyre rendezve. Állandóan könnyen elérhető „Új ötlet” művelet. A hang- és kutatási profil külön beállítás.
- Kutatás: bal oldalon tömör témalista, középen a kiválasztott összefoglaló és saját nézőpont, jobb oldalon az állítások és források. Az elrendezés a meglévő hárompaneles rendszerből továbbvihető.
- Szerkesztés: hangsúly a szövegen; becsukható forrásblokk, látható mentési állapot, verzió-összehasonlítás. Az audit/hash a részletek közé kerüljön.
- Normál felületszövegnek 13–15 px körüli méretet céloznék; a most sok helyen használt 9–10 px maradjon ritka, másodlagos metaadat.
- Egy elsődleges művelet legyen egyértelmű az adott állapotban: „Téma kiválasztása”, „Vázlat készítése”, „Mentés”, „Jóváhagyás”.
- A meglévő törtfehér/szürkészöld paletta, serif kézirat és kevés hangsúlyszín megtartható. Érdemes enyhíteni a sok fekete elválasztóvonalat, és a címeknek több helyet adni a bal listában.
- Mobilon külön lista és részletnézet kellene visszalépéssel. A jelenlegi egymás alá rendezés technikailag alkalmazkodik a szélességhez, de a hosszú kutatási anyag és az alulra kerülő műveletek sok görgetést okozhatnak.
- A LinkedIn-előnézet legyen opcionális olvasási nézet; a platform megjelenésének becsléseként kezeljük. Saját használatra előbb a téma- és forrásnézet fontosabb.

## Mitől lesz erős portfólióprojekt?

A bemutatható történet: **személyes kutatási és publikálási munkafolyamat, ellenőrizhető forrásokkal, közös web/MCP háttérrel, verzióbiztos emberi döntésekkel.**

Ehhez a legerősebb bizonyítékok:

1. Végigkattintható, elkülönített demóadatokkal működő bemutató és rövid videó: téma → forrás → saját megjegyzés → szöveg → változás → jóváhagyás.
2. Valódi használatból származó esettanulmány: hány témát fogadtál el, mennyi idő alatt választottál, hány poszt született. Csak ténylegesen mért eredmények.
3. CI, valódi Postgres-integráció, konkurenciatesztek, mentési és review E2E-tesztek.
4. Verziózott migráció, kipróbált export/helyreállítás és reprodukálható deploy.
5. Az ADR-ek és a README állításai egyezzenek a kóddal és a tesztelt képességekkel. A jelenlegi „deployment-ready” megfogalmazás túl erős a Postgres-hiba és az el nem végzett éles integrációs próbák mellett.

Új infrastruktúrát csak kimutatható használati probléma miatt vezetnék be. Többfelhasználós SaaS, bonyolult agenthálózat, vektoradatbázis vagy teljes közösségimédia-platform most nem szerepelne az első fejlesztési körben.

## Megvalósítási sorrend és elfogadási feltételek

| Sorrend | Cél | Akkor kész, ha… |
| --- | --- | --- |
| 1 | Megbízható meglévő szerkesztés | A párhuzamos mentés/jóváhagyás konzisztens; a munkapéldány helyreállítható; a látható és jóváhagyott verzió nem keverhető; Postgres capture működik; a szűrő nem ragad be. |
| 2 | Mobilos ötletmentés és AI-draft | Egy mezőből külön választható a mentés és a generálás; az eredeti ötlet megmarad; a generálás böngészőbezárás után is befejeződik; a draft mobilon javítható és elfogadható. |
| 3 | Kutatási profil és témalista | Saját preferenciák alapján érkezik rövid, indokolt témalista; lehet kiválasztani/elutasítani; minden téma ellenőrizhető forrásokhoz vezet. |
| 4 | Állítás–forrás kapcsolat és saját nézőpont | A draft fő tényállításai visszakövethetők; a személyes tapasztalat és a forrásból vett tény elkülöníthető. |
| 5 | Egyszerű szerkesztés és publikálás | Kézzel is létrehozható első draft; van diff, közvetlen publikálási visszaigazolás és eredmény-visszaolvasás. |
| 6 | Valódi használat és bemutató | Több héten át használod; a mért súrlódások javítva vannak; elkülönített demó és reprodukálható telepítés elérhető. |

Első validációs kísérletnek két hetet javaslok, automatikus időzített kutatás nélkül. Próbáljuk ki a saját ötletek gyors rögzítését és drafttá alakítását tényleges mobilos használatban, és külön a kutatási témaválasztást. Mérjük az első átnézhető draftig eltelt időt, az elfogadáshoz szükséges javításokat, a témaválasztás idejét, az elfogadott javaslatok arányát, az elutasítás okát, a forrásellenőrzés idejét és az elkészült posztok számát. A fejlesztés akkor talált célba, ha mindkét út kevesebb munkát és megbízhatóbb eredményt ad, mint a korábbi módszered.

A vizsgálat során alkalmazáskódot nem módosítottam; ez a dokumentum az elemzés eredménye.
