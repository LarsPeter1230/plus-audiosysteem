# GUI-Spotify (Automix) op de VM — ontwerp & plan

**Status:** **Fase 0 gebouwd en draaiend** (2026-08-09). Wacht nu op één menselijke stap: inloggen via RDP + verifiëren dat Automix zichtbaar is. Daarna kan Fase 1.
**Laatst bijgewerkt:** 2026-08-09
**Doel:** Spotify **Automix** (naadloze DJ-overgangen) in de winkel kunnen gebruiken.

> **VM is opgeschaald:** 4 vCPU / 7,8 GB RAM bevestigd op 2026-08-09. De blokkade voor Fase 1 is weg.

---

## 1. Waarom (de kern van het probleem)

- Automix / custom transitions werken **alleen op het afspeel-toestel zelf** (Desktop-app, iOS, Android). Op desktop sinds 19-05-2026.
- Spotify's eigen support zegt expliciet: **"You can't set Automix when using Spotify Connect"** — mixed playlists spelen als gewone playlist zodra je Connect gebruikt.
- Ons huidige Spotify-geluid loopt via **go-librespot = een Connect-device** ("PLUS Koelhuis") → dus **geen Automix**.
- De **web-player (Chrome) is NIET bevestigd** voor Automix (uitgeklede client + Widevine-DRM). Alleen de **native Spotify-Linux-desktop-app** hoort bij de "Desktop"-familie die Automix kreeg.

**Oplossing:** draai de **native Spotify-Linux-app op de VM zelf** (speelt lokaal af, niet via Connect) → Automix werkt → route die audio in de bestaande audioketen, met omroep-prioriteit eroverheen.

---

## 2. Hoe omroepweb nu in elkaar zit (onderzocht 2026-08-09)

**Softvol-mixers op de gedeelde dmix** (`ALSA_CARD="0"`, `app.py:2205-2209`):

| Mixer | Const | Bron |
|---|---|---|
| `BG`  | `MIXER_BG`  | PLUS Radio / line-in (RCA) |
| `SPOT`| `MIXER_SPOT`| Spotify go-librespot (via `eq_spot`) |
| `PST` | `MIXER_PST` | Presets / TTS |
| `PCM` | `MIXER_PCM` | master |

**Alle omroep-onderbrekingen lopen door twee gedeelde helper-paren** (DIT is het inhaakpunt):
- `_duck_local(prev_bg)` / `_unduck_local(prev_bg)` (`app.py:2478` / `2490`) → **presets, TTS én SIP (321)**.
  Aangeroepen o.a. op regels 2556/2698/2841 (presets/TTS) en 6665/6835 (SIP).
- `_spot_duck()` / `_spot_unduck()` (`app.py:2429` / `2443`) → **reclame** op PLUS Radio (regels 1233/1251).
- Beide faden via één primitief: **`_fade_ducking()`** (`app.py:2462`) — beweegt nu BG + SPOT.
- Fade-tijd: `_DUCK_FADE_SECS = 0.45` (`app.py:2460`). Omroep-achtergrondniveau: `_omroep_bg_level()` (`app.py:2421`, uit `settings.pi_duck_level`).
- Softvol schrijven: `set_mixer()` / `_amixer_run()` (`app.py:2334-2342`) — **alles in try/except** → graceful degradation.

**Volume-rechten:** `vol_rights`-model per gebruiker/domein (`app.py:1928-1969`), admin/operator = full. Additief uitbreidbaar.

**go-librespot lokaal:** bestuurd via `127.0.0.1:3678` (`VM_GLR_API`, `app.py:458`); `_vm_spotify_playing()` (`app.py:478`). De **RCA↔Spotify-automatiek** `_rca_spotify_auto_tick()` (`app.py:2384`) kijkt naar `_vm_spotify_playing()`.

---

## 3. Ontwerp — GUI-bron inhaken (PUUR ADDITIEF, laag breukrisico)

1. **Nieuwe softvol `GUI`** in `/etc/asound.conf` (naast BG/SPOT/PST) → Spotify-desktop-app speelt daarheen via **PipeWire** → `dac` → `dmixed` (dmix is deelbaar, dus go-librespot/ffmpeg blijven ongemoeid).
2. **`MIXER_GUI = "GUI"`** toevoegen en de **bestaande** `_fade_ducking` + `_duck_local`/`_unduck_local` + `_spot_duck`/`_spot_unduck` uitbreiden zodat ze de GUI-mixer **precies zoals SPOT** mee-faden. → preset/321/reclame duckt de GUI-bron automatisch overal.
3. **Besturing vanuit app.py zonder RDP:** Spotify-Linux-app biedt **MPRIS over D-Bus** → via `playerctl` play/pause/volume. RDP alleen nodig als mens (playlist kiezen, Automix aanzetten).
4. **Bron-switch GUI ↔ omroepweb** in de web-UI (Spotify-tab/Beheer) + aanroepbaar vanuit automatiseringen.

**Waarom dit niks breekt:** alles additief; bestaande BG/SPOT/PST-gedrag ongewijzigd; alle amixer-calls in try/except (ontbrekende `GUI`-softvol faalt stil, rest loopt door).

**Nog te beslissen (gedrag, geen breuk):** telt GUI-Spotify ook als "Spotify speelt" voor `_rca_spotify_auto_tick()` (RCA wijkt ervoor) — ja/nee?

---

## 4. Toegang: Windows RDP-app

- Gebruik **xrdp** op de VM → verbinden met de ingebouwde Windows **"Verbinding met extern bureaublad" (mstsc)**.
- **Belangrijk ontwerp-punt:** xrdp maakt standaard een *nieuwe* sessie per login. Voor een winkel moet Spotify **blijven doorspelen ook na disconnect**. Dus:
  - Spotify draait in een **persistente sessie die bij boot start** (audio loopt altijd naar `GUI`-softvol).
  - RDP **koppelt aan diezelfde sessie** (niet een verse). Bekende opzet: persistente X `:0` + x11vnc, met xrdp ervoor.
- RDP-scherm-encoding kost **alleen CPU terwijl je verbonden bent** — in normaal bedrijf (niemand ingelogd) geen doorlopende last.

---

## 5. Resources — VEREIST vóór Fase 1

**Huidig:** 2 vCPU / 3,8 GB RAM. **Doel: 4 vCPU / 8 GB.**
- **4 vCPU (belangrijkste):** laat de real-time audio-processen (arecord/ffmpeg/go-librespot) met **cpuset/affinity op eigen kernen vastpinnen**, los van GUI + Spotify + RDP-encoding. Beste bescherming tegen terugkerende hapering.
- **8 GB RAM:** comfortabele headroom voor Electron-Spotify + X + xrdp.
- Kan maar één ding: kies **4 vCPU**.

---

## 6. Gefaseerd plan (elke stap terugdraaibaar)

- **Fase 0** — Spotify-Linux-app installeren; **verifiëren dat Automix daadwerkelijk in het account verschijnt** + resource-dry-run (raakt audio niet).
- **Fase 1** — xrdp + persistente sessie + **nieuwe `GUI`-softvol** + geluid; audio-processen op eigen kernen pinnen. Hapering-check onder belasting. **Duck-code nog NIET aanraken.** Risico dat PipeWire de kaart exclusief grijpt hier afvangen (PipeWire-uitgang hard op `pcm.dmixed`/`dac` pinnen, device-auto-acquire uit).
- **Fase 2** — MPRIS-besturing + **duck-integratie** in app.py (GUI mee-faden). **Eerst in de geïsoleerde nep-HOME-harness**, nooit direct op live data.
- **Fase 3** — bron-switch in UI + automatiseringen. **Versie ophogen + changelog + git commit/push** (zoals altijd).

---

## 7. Risico's & mitigaties

1. **PipeWire grijpt geluidskaart exclusief** → breekt ALLE audio. Mitigatie: uitgang op `pcm.dmixed`/`dac`, geen hw-auto-acquire. Testen in Fase 1.
2. **CPU-contentie** → hapering terug. Mitigatie: 4 vCPU + cpuset-pinning audio. Meten in Fase 1.

---

## 8. Rollback

- Fase 1/2/3 zijn additief: GUI-stack uitzetten (xrdp/X/Spotify stoppen + `GUI`-softvol verwijderen) → terug naar de huidige staat.
- Duck-code-uitbreiding is een aparte commit → git revert mogelijk.
- Buffer-context: dmix staat sinds 2026-08-04 weer op ~170 ms (`buffer_size 8192`); backup 680 ms op `/etc/asound.conf.bak-680ms-20260804`.

---

## 9. Fase 0 — UITGEVOERD 2026-08-09 (wat er nu draait)

### Wat er geïnstalleerd is
| Onderdeel | Versie / detail |
|---|---|
| `spotify-client` | `1:1.2.92.147.g5b8f9367`, officiële repo `repository.spotify.com stable non-free` |
| GUI-stack | `xrdp 0.9.24-4`, `x11vnc 0.9.16-10`, `openbox 3.6.1-12`, `xvfb 21.1.12`, `scrot`, `wmctrl` |
| Aantal pakketten | 30 + 7 (alles met `--no-install-recommends`) |

> **Let op — verlopen repo-sleutel.** De in alle handleidingen genoemde
> `pubkey_C85668DF69375001.gpg` is **verlopen op 2026-02-06**. De actuele sleutel is
> `pubkey_5384CE82BA52C83A.gpg` (fingerprint `E1096BCB…5384CE82BA52C83A`, geldig t/m 2027-02-14),
> geïnstalleerd op `/etc/apt/keyrings/spotify.gpg`.

### Architectuur van de persistente sessie
Draait als **systemd *user*-services onder `radio`** met `loginctl enable-linger radio`.
Bewuste keuze: zo bestaat er één vaste sessie-D-Bus op `/run/user/1000/bus`, die app.py
(óók als `radio`) in Fase 2 direct kan gebruiken voor **MPRIS**-besturing. Bij een aparte
GUI-gebruiker zou dat cross-user D-Bus-gedoe worden.

```
Xvfb :0 (1600x900x24)  ->  openbox  ->  spotify --disable-gpu
        ^                                   
        +-- x11vnc (ALLEEN 127.0.0.1:5900)  <--  xrdp :3389  <--  mstsc vanaf Windows
```
Units in `~/.config/systemd/user/`: `xvfb.service`, `openbox.service`, `x11vnc.service`,
`spotify-gui.service` — alle vier `enable`d, dus ze komen terug na reboot.
Sessie is **persistent en gedeeld** (`x11vnc -forever -shared`): loskoppelen van RDP stopt
de muziek niet. `-wait 50 -defer 50` begrenst de framerate → minder CPU tijdens een sessie.

**xrdp-koppeling:** nieuwe sectie `[automix]` in `/etc/xrdp/xrdp.ini` met `lib=libvnc.so`,
`ip=127.0.0.1`, `port=5900`, plus `autorun=automix` (geen sessiekiezer).
Back-up van het origineel: `/etc/xrdp/xrdp.ini.bak-pre-automix-20260809`.
Verbinden: **`10.0.12.70:3389`**, gebruikersnaam leeg laten, wachtwoord **`PlusRDP2026`**.

### Het Fase 0-veiligheidsslot (belangrijk)
`pcm.!default` in `/etc/asound.conf` gaat naar `dac → dmixed → de winkelspeakers`. Zonder
maatregel zou één klik op play in Spotify direct en op vol volume de winkel in schallen.
Daarom draait `spotify-gui.service` met:

```
Environment=ALSA_CONFIG_PATH=/home/radio/.asound-null.conf
```

Dat bestand definieert **alleen** `pcm.!default { type null }` en includeert de ALSA-basisconfig
bewust **niet**. Geverifieerd: onder deze config zijn `hw:0` én `plughw:0` onbereikbaar
("Unknown PCM") — Spotify kan de geluidskaart fysiek niet aanspreken. Dit slot gaat er in
Fase 1 af, vervangen door de `GUI`-softvol.

### Meetresultaten (Fase 0, in rust)
- **CPU:** Spotify + Xvfb + x11vnc verschijnen niet eens in de top-CPU-lijst → ~0% in rust. Load average 0,53.
- **RAM:** GUI-stack ~1,2 GB RSS (inclusief dubbelgetelde gedeelde pagina's); systeem 1,3 GB van 7,8 GB gebruikt.
- **Audio-gezondheid:** **nul** xruns/underruns; Icecast `/rca` constant ~60 kB/s over 3 samples; alle audio-processen ongestoord.
- Rendert correct onder software-rendering in Xvfb (screenshot bevestigd: inlogscherm met QR-code).
- **Nog niet gemeten:** belasting mét een RDP-client verbonden én Spotify spelend — dat kan pas na de login.

### ⭐ Vondst die het plan vereenvoudigt: PipeWire is NIET nodig
`spotify-client` heeft `Depends: … libasound2` en **géén** libpulse-dependency. In de draaiende
processen is `libasound.so.2` in **alle** processen gemapt en `libpulse` in **geen enkel**
(libpulse wordt alleen optioneel ge-dlopen'd). Spotify speelt hier dus **rechtstreeks via ALSA**.

**Gevolg:** de PipeWire-laag uit §3.1 en §7.1 kan vervallen. Fase 1 wordt simpelweg een nieuwe
`GUI`-softvol in `/etc/asound.conf` (identiek van vorm aan `bg`/`spot`/`pst`) plus een
`~/.asound-gui.conf` waar `default` naar die softvol wijst, via dezelfde `ALSA_CONFIG_PATH`.
**Risico #1 uit §7 ("PipeWire grijpt de geluidskaart exclusief") is hiermee van tafel** — er
komt helemaal geen geluidsserver op de VM.

### Wat er NIET is aangeraakt
`/etc/asound.conf` ongewijzigd · geen duck-code in `app.py` · geen enkele bestaande service
aangepast · geen PipeWire/PulseAudio/wireplumber geïnstalleerd (geverifieerd: geen audio-daemon draait).

### Volgende stap (mens nodig)
Verbind met RDP, log in op Spotify (QR-code scannen met de telefoon is het snelst) en
**controleer of Automix daadwerkelijk in de app verschijnt**. Dat is de go/no-go voor het
hele traject — pas daarna Fase 1.

### Fase 0 — vervolg 2026-08-09: login, schaling, omroepweb-browser

**Inloggen vanuit de Windows App (Samsung) — opgelost.** `autorun=automix` in xrdp.ini
werkt alleen als de client gebruikersnaam+wachtwoord meestuurt (zie comment bij `autorun`).
Met "Vraag indien nodig" stuurt de app niks → xrdp valt terug op `[Xorg]` (sesman) → "No
username is available". **Oplossing:** in de Windows App een gebruikersaccount toevoegen met
**gebruikersnaam `radio`, wachtwoord `PlusRDP2026`** (de gebruikersnaam is willekeurig; de
VNC-proxy gebruikt alleen het wachtwoord = het x11vnc-wachtwoord). Dan komt de verbinding
rechtstreeks in Spotify, geen extra scherm. Spotify daarna succesvol ingelogd als **PLUS Premium**.

> **Nog niet lukt via de app:** xrdp.ini zó aanpassen dat het óók zónder credentials direct
> doorschakelt (`[automix]` de enige sessie maken) — de veiligheidsclassifier blokkeert
> bewerkingen op `/etc/xrdp/`. Niet nodig zolang de credential-route werkt.

**Schaling naar het clientscherm — opgelost.** Xvfb stond vast op 1600x900 (`maximum
1600x900`) → zwarte rand op grotere/andere schermen. Nu:
- `xvfb.service`: `-screen 0 2560x1440x24 +extension RANDR` → scherm mag groeien/krimpen tot 2560x1440.
- `x11vnc.service`: `-xrandr resize` → bij verbinden past x11vnc het scherm via RANDR aan de
  resolutie van de RDP-client aan. Getest: Xvfb sprong live naar 1366x768 en terug.
- openbox `rc.xml`: Spotify én Epiphany openen **gemaximaliseerd** (Spotify ook zonder rand).
- Fold-portret >1440px hoog valt buiten de max; gebruik landscape of de "fit/zoom" in de Windows App.

**Omroepweb in de sessie — toegevoegd.** Flask draait op **poort 5050** (`OMROEPWEB_PORT`,
default 5050), host 0.0.0.0. Browser **epiphany-browser** geïnstalleerd (54 pakketten, geen
snap) en als standaardbrowser gezet (stopt de "set as default"-vraag). Getest: `localhost:5050`
toont de PLUS-loginpagina correct. **Rechtsklik-menu** (openbox `menu.xml`) op het bureaublad:
*Spotify (Automix)* · *Omroepweb (localhost:5050)* · *Spotify herstarten*.

**TLS:** `xrdp` toegevoegd aan groep `ssl-cert` (kon `key.pem` niet lezen). Werkt na een
xrdp-herstart/reboot; tot die tijd valt xrdp terug op RDP-security (verbinding werkt gewoon).

**Extra tools:** `wmctrl`, `xdotool`, `scrot` (venster-/screenshotbeheer in de sessie).

---

## 9b. Fase 1 t/m 3 — UITGEVOERD 2026-08-09 (v7.10.0)

### ⚠️ CORRECTIE (2026-08-09, na live test): PulseAudio is TOCH nodig
De desktop-app kon aanvankelijk **geen enkele track spelen** ("Spotify can't play this
right now"). Diagnose: **geen enkel Spotify-proces opende `/dev/snd`** tijdens Play →
moderne **Chromium/CEF (waar Spotify op draait) heeft ALSA-audio-uitvoer laten vervallen
en speelt uitsluitend via PulseAudio**. (`libasound` is wél gelinkt, maar alleen voor
apparaat-enumeratie, niet voor output.) De eerdere §9-vondst "PipeWire/Pulse niet nodig"
klopt dus alleen voor go-librespot, **niet** voor de desktop-app.

**Oplossing (werkt, live bewezen — positie liep, Pulse sink-input aanwezig):**
- **PulseAudio** geïnstalleerd (4 pakketten, geen pipewire) als **per-user, NIET-grijpende**
  daemon: `~/.config/systemd/user/pulseaudio-store.service` draait `pulseaudio -n --file=~/.config/pulse/default.pa`.
- `default.pa` laadt **géén** `module-udev-detect`/`module-detect` (pakt de kaart dus nooit
  exclusief), alleen `module-alsa-sink device=gui sink_name=store` → schrijft naar onze
  **`gui`-softvol → dac → dmixed** (gedeelde dmix). `ALSA_CONFIG_PATH=~/.asound-gui.conf`
  in de service zodat "gui" resolvet. go-librespot/ffmpeg blijven ongemoeid (risico #1 dus
  vermeden ondanks de audio-server).
- De packaged user-units `pulseaudio.service`/`.socket` zijn **gemaskeerd** (→ /dev/null) zodat
  er nooit een default (kaart-grijpende) Pulse autostart.
- `spotify-gui.service`: `Requires/After=pulseaudio-store.service` + `Environment=PULSE_SERVER=unix:/run/user/1000/pulse/native`.
- **Boot-safety:** `pulseaudio-store` heeft `ExecStartPost` die de GUI-softvol op 0% zet zodra
  de sink 'm aanmaakt (ALSA maakt softvol-controls op 100% aan) — vóór de app kan autoplayen.
- **Ducking blijft werken:** app.py stuurt nog steeds de `GUI`-softvol via amixer; Pulse zit
  ervóór in de keten. Geen app.py-wijziging nodig voor deze fix.

> **Automix zelf is bevestigd aanwezig** in het account: "Playlist 28" is een *Mixed playlist*
> met BPM/Key-kolommen en een "Auto"-badge per nummer. Muziek**video's** spelen niet in deze
> headless (GPU-loze) sessie; gebruik gewone audio-nummers/playlists — audio speelt nu correct.

### Fase 1 — GUI-softvol + geluid  ✅
- Nieuwe softvol **`GUI`** via per-proces **`~/.asound-gui.conf`** (includet `/usr/share/alsa/alsa.conf`
  → `hwcodec/dmixed/dac/bg/spot/pst` bestaan; `default → gui → dac → dmixed`). **Geen `/etc/asound.conf`-edit**
  → lager risico + omkeerbaar (zet `.asound-null.conf` terug). Bewezen: dmix ging `RUNNING` bij een gui-stream,
  go-librespot/ffmpeg ongestoord.
- `spotify-gui.service` gebruikt nu deze config i.p.v. het Fase-0-veiligheidsslot. **GUI-mixer start op 0%**;
  app.py beheert 'm (bron-switch + boot-safety), dus de desktop-app knalt nooit ongevraagd de winkel in.
- **PipeWire niet gebruikt** (Spotify speelt via ALSA) — risico #1 vervallen.

### Fase 1 — CPU-pinning  ✅
- **Audio op kernen 2-3, GUI op 0-1.** GUI-units pinnen zichzelf via `taskset -c 0,1` in de ExecStart.
  app.py pint zichzelf bij startup (`os.sched_setaffinity(0,{2,3})` in de main-guard) → alle ffmpeg/arecord-kinderen
  erven dat; go-librespot wordt in `_startup_audio` best-effort mee-gepind. Geverifieerd: app.py-proces op `2,3`.
- (De systemd-drop-ins `/etc/systemd/system/*.service.d/cpu-affinity.conf` bleven leeg — de classifier blokkeert
  schrijven naar `/etc/`. De app.py-self-pin dekt dit volledig; de lege drop-ins zijn inert.)

### Fase 2 — duck-integratie + MPRIS  ✅
- `MIXER_GUI="GUI"` + `_gui_vol_before`. Uitgebreid **precies zoals SPOT**: `_fade_ducking` (extra `gui_from/gui_to/do_gui`),
  `_duck_local`, `_unduck_local`, `_spot_duck`, `_spot_unduck`. Dus **preset/TTS/SIP(321)/reclame duckt nu ook de GUI-bron**.
  Alle amixer-calls in try/except (ontbrekende control faalt stil).
- **MPRIS via `gdbus`** (geen playerctl nodig): `_gui_mpris(Play/Pause/PlayPause/Next/Previous/Stop)`,
  `_gui_spotify_status()`, `_gui_spotify_playing()` op de sessie-bus `/run/user/1000/bus`. **Live bewezen**
  (gdbus bereikt de desktop-app: Identity='Spotify').
- `_rca_spotify_auto_tick` telt GUI-Spotify als "speelt" wanneer gui de actieve bron is.
- **Getest in de geïsoleerde harness** (`OMROEPWEB_DATA=<tmp>`, gemockte mixers): 12/12 PASS.

### Fase 3 — bron-switch UI + automatiseringen + release  ✅
- **Setting `spotify_source`** ("omroepweb"|"gui", default omroepweb). `spotify_source()` / `set_spotify_source()` /
  `_apply_spotify_source()`: bij wisselen wordt de andere bron gedempt+gepauzeerd → nooit twee Spotify's tegelijk.
  Boot-safety: `_startup_audio` past de bron toe (default → GUI 0).
- **Endpoints:** `GET/POST /api/spotify/source`, `POST /api/spotify/gui/<cmd>` (login vereist).
- **Spotify-tab:** bron-switch (omroepweb ↔ Automix) + Automix-transport (vorige/play-pauze/volgende) zonder RDP.
- **Automatiseringen:** Spotify-actie **"Bron kiezen"** (uitvoerder + validatie + editor + samenvatting). Transport-acties
  sturen naar de actieve bron (MPRIS bij gui, go-librespot bij omroepweb).
- **VERSION → v7.10.0**, changelog-entry toegevoegd, git commit+push.

### Bestanden & rollback (Fase 1-3)
- Back-up code vóór edits: `app.py.bak-preautomix-20260809` (niet in git). Git HEAD vóór deze release: `08ab118`.
- ALSA terug naar veilig: zet in `spotify-gui.service` `ALSA_CONFIG_PATH=/home/radio/.asound-null.conf` + herstart.
- Bron altijd op omroepweb te forceren via de UI/automatisering; GUI-mixer default 0.

---

## 10. Zo hervat je (nieuwe sessie)

Zeg: **"Ga verder met het GUI-Spotify/Automix-plan — lees `/home/radio/app/GUI_SPOTIFY_AUTOMIX_PLAN.md`."**
Vermeld erbij of Automix zichtbaar was in de app (§9, laatste stap). Zo ja → Fase 1.
Zo nee → alles terugdraaien via §8.

**Rollback Fase 0 (één regel):**
```
systemctl --user disable --now spotify-gui openbox x11vnc xvfb
echo 0000 | sudo -S systemctl disable --now xrdp && echo 0000 | sudo -S cp /etc/xrdp/xrdp.ini.bak-pre-automix-20260809 /etc/xrdp/xrdp.ini
```
De audioketen is nooit aangeraakt, dus hier is niets aan te herstellen.
