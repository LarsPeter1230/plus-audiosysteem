#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Omroepweb v6.4.0 — PLUS Omroepsysteem
Lokaal gebruikersbeheer + OpenID Connect via webinterface
+ TTS download (WAV/MP3) en opslaan als preset
+ Raspberry Pi / Raspotify integratie (duck/unduck, volume, herstart)
+ iframe-compatibiliteit voor Home Assistant (SameSite=None + Partitioned cookies)

v6.3.0 wijzigingen:
- FIX: redirect-loop ("te vaak doorverwezen") op iOS — gebruikers zonder
  paginarechten kwamen in een oneindige /login → /login lus terecht.
  Er is nu een nette /geen-toegang pagina.
- FIX: SECRET_KEY wordt persistent opgeslagen zodat sessies een herstart
  van de app overleven (voorheen was iedereen na elke restart uitgelogd).
- NIEUW: Outro-audio (naast de bestaande Preroll/intro) — uploadbaar via
  Beheer, per preset in/uit te schakelen, en als checkbox bij TTS.
- SNELHEID: SSH naar de Pi hergebruikt nu één verbinding (ControlMaster/
  ControlPersist) en het ducken gebeurt in één SSH-roundtrip i.p.v. twee.
  Dit was de hoofdoorzaak van de vertraging bij het starten van presets.
- SNELHEID: logboek wordt gebufferd weggeschreven (elke ~2s) i.p.v. het
  volledige JSON-bestand (tot 5000 regels) synchroon bij elke actie.
- Cookie krijgt het "Partitioned"-attribuut (CHIPS) zodat de sessie ook
  in een cross-site iframe blijft werken in Chrome/Android.
- Ongeldige "X-Frame-Options: ALLOWALL" header verwijderd (CSP
  frame-ancestors * regelt iframe-toestemming).
- /events (SSE) vereist nu login.
- Uploads (preset/preroll/outro) valideren nu of ffmpeg-conversie slaagde.
"""

from flask import (
    Flask, request, jsonify, render_template_string,
    redirect, url_for, session, abort, Response, make_response,
    has_request_context, send_file
)
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash
import os, json, re, time, threading, subprocess, signal, glob, tempfile, secrets, shutil, unicodedata, socket, base64, collections
from datetime import datetime, date
from urllib.parse import urlencode
import urllib.request, urllib.error

try:
    import fcntl
except ImportError:
    fcntl = None

app = Flask(__name__)

@app.before_request
def _onboarding_gate():
    """Verse installatie (nog niet onboarded) → altijd naar de wizard, behalve de
    wizard zelf, de audio-/onboarding-API, static en in-/uitloggen."""
    try:
        if settings.get("onboarded"):
            return
    except Exception:
        return
    p = request.path
    for a in ("/onboarding", "/api/onboarding", "/api/audio", "/static", "/login", "/logout", "/favicon"):
        if p == a or p.startswith(a + "/"):
            return
    return redirect(url_for("onboarding_page"))

# ──────────────────────────────────────────────
# Paden
# ──────────────────────────────────────────────
HOME      = os.path.expanduser("~")
APP_DIR   = os.environ.get("OMROEPWEB_DATA", os.path.join(HOME, "omroepweb"))   # data-map (instelbaar → losse demo-instantie mogelijk)
PRESETS   = os.path.join(APP_DIR, "presets")
COMM_ARCHIVE_DIR = os.path.join(APP_DIR, "comm_archive")   # laatste opgenomen reclames (download)
PIPER_DIR = os.path.join(APP_DIR, "piper")
AVATARS   = os.path.join(APP_DIR, "avatars")
for d in [APP_DIR, PRESETS, PIPER_DIR, AVATARS]:
    os.makedirs(d, exist_ok=True)

NAMES_JSON    = os.path.join(APP_DIR, "presets", "namen.json")
LOGS_JSON     = os.path.join(APP_DIR, "app_logs.json")
SETTINGS_JSON = os.path.join(APP_DIR, "settings.json")
PVOL_JSON     = os.path.join(APP_DIR, "preset_volumes.json")
SCHED_JSON    = os.path.join(APP_DIR, "schedules.json")
AUTOM_JSON    = os.path.join(APP_DIR, "automations.json")
PFLAGS_JSON   = os.path.join(APP_DIR, "preset_flags.json")
PICONS_JSON   = os.path.join(APP_DIR, "preset_icons.json")
INTRO_WAV     = os.path.join(APP_DIR, "intro.wav")
OUTRO_WAV     = os.path.join(APP_DIR, "outro.wav")
EXPLICIT_WAV  = os.path.join(APP_DIR, "explicit_alert.wav")   # alarm bij explicit-nummer
USERS_JSON    = os.path.join(APP_DIR, "users.json")
OIDC_JSON     = os.path.join(APP_DIR, "oidc_config.json")
SPOTIFY_JSON  = os.path.join(APP_DIR, "spotify_oauth.json")   # Spotify Web API (huisaccount) — bevat secret
SECRET_FILE   = os.path.join(APP_DIR, "secret_key")

app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

# ──────────────────────────────────────────────
# JSON helpers
# ──────────────────────────────────────────────
def _load_json(path, default):
    try:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def _save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

# ──────────────────────────────────────────────
# State laden
# ──────────────────────────────────────────────
SETTINGS_DEFAULTS = {
    "version": "v7.5.1",
    "onboarded": False,           # eerste-keer-wizard doorlopen? (verse install = False)
    "demo_mode": False,           # demo: audio via dit apparaat (laptop), geen winkelhardware
    "eq_spot": [50, 50, 50, 50, 50, 50, 50, 50, 50, 50],   # 10-band Spotify-EQ (0-100, 50=vlak)
    "eq_bg":   [50, 50, 50, 50, 50, 50, 50, 50, 50, 50],   # 10-band PLUS Radio-EQ (0-100, 50=vlak)
    "location_name": "",          # filiaal-/locatienaam, bijv. "Centrum" (leeg = generiek "PLUS")
    "show_playing_popup": False,  # toon 'nu aan het afspelen'-popup bij presets/TTS (met stop-knop)
    "blocked_words": [],          # woordfilter: deze woorden worden in TTS geblokkeerd (zie DEFAULT_BLOCKED_WORDS)
    "tts_prefill": "Attentie, ",  # standaard ingevulde begintekst op de TTS-pagina
    "tts_quick_words": ["Attentie", "servicebalie", "slijterij", "kassa", "emballage"],
    "announcement_enabled": False,
    "announcement_text": "",
    "announcement_id": 1,
    "pages": {"volume": True, "presets": True, "tts": True},
    "presets_lock_enabled": False,
    "presets_lock_seconds": 30,
    "tts_lock_enabled": False,
    "tts_lock_seconds": 30,
    "tts_engine": "edge",
    "tts_edge_voice": "nl-NL-MaartenNeural",
    "tts_preroll_enabled": True,
    "tts_outro_enabled": False,
    "tts_gain": 100,
    "ip_rules": {},
    "user_rules": {},
    "pi_duck_level": 0,   # achtergrondniveau tijdens omroep (0 = volledig stil)
    "spotify_control": False,  # aan = go-librespot-modus (transportknoppen + seek)
    "rca_autostart": True,     # RCA (PLUS Radio) automatisch starten bij opstart service/VM
    "rca_spotify_auto": True,  # RCA automatisch uit als Spotify speelt, weer aan na 30s stilte
    "lisa_enabled": True,      # PLUS Radio now-playing via de Streamit Lisa (telnet)
    "lisa_host": "",           # IP van de Lisa-streamer (per winkel; via onboarding/Beheer)
    "lisa_port": 23,           # telnet-poort
    "public_base_url": "",     # publiek https-domein van deze installatie (voor Spotify-callback)
    "spotify_device_name": "", # naam van het go-librespot Connect-apparaat (per winkel)
    "house_sp_user": "",       # Spotify-huisaccount (om 'gecast door' te verbergen)
    "icecast_meta_enabled": True,  # huidige PLUS Radio-titel als metadata naar de /rca-stream
    "icecast_admin_url": "http://localhost:8000/admin/metadata",
    "icecast_mount": "/rca",
    "icecast_admin_user": "admin",
    "icecast_admin_pass": "",     # secret — echte waarde staat in ~/omroepweb/settings.json (niet in de code)
    "commercial_duck_spotify": True,  # reclame op PLUS Radio → Spotify dempen + RCA laten spelen
    "commercial_replay": False,    # experimenteel: commercial (incl. gemist begin) vertraagd over Spotify
    "ha_webhook_ip": "",  # webhooks vanaf dit IP = Home Assistant (eigen logcategorie)
    "commercial_stream_pct": 50,   # tijdens een reclame: online-stream-volume op dit % van normaal
    "shazam_enabled": True,        # nummer op de line-in herkennen → titel/artiest/cover verrijken
    "lisa_keepalive": True,        # Lisa stil? → 'pw 1' sturen om te herstarten (stream niet stil laten vallen)
    # TuneIn now-playing (AIR API): huidige titel/artiest doorgeven aan de TuneIn-zender
    "tunein_enabled": False,       # aan = huidige nummer naar TuneIn pushen (vereist credentials)
    "tunein_partner_id": "",       # van TuneIn (broadcaster)
    "tunein_partner_key": "",      # van TuneIn (broadcaster)
    "tunein_station_id": "s359456",# stationId, bijv. s359456 (uit de TuneIn-URL)
    # Now-playing als JSON in de Icecast-webroot → publiek op stream.example.nl/nowplaying.json
    "nowplaying_file": "/usr/share/icecast2/web/nowplaying.json",
    # ── Huisstijl / branding (white-label uitrol) ──
    "brand_theme": "plus",          # actieve huisstijl: "plus" | "ah" (uitbreidbaar, bijv. "jumbo")
    "brand_logo_overrides": {},     # per thema een geüpload logo als data-URI/URL, bijv. {"ah": "data:image/svg+xml;base64,..."}
    # ── Live omroep via SIP (3CX / SBC): bel een extensie → live over de speakers ──
    "sip_enabled": False,           # aan = registreer als toestel bij de SBC en neem inkomende gesprekken aan
    "sip_extension": "",            # extensienummer om te bellen, bijv. 321
    "sip_auth_id": "",              # Authentication ID (3CX)
    "sip_auth_pass": "",            # Authentication password (secret — alleen in ~/omroepweb/settings.json)
    "sip_registrar_host": "",       # Registrar hostname/IP, bijv. pluskoelhuis.my3cx.nl
    "sip_registrar_port": 5060,
    "sip_sbc_host": "",             # Outbound Proxy (SBC) adres, bijv. 10.0.13.254
    "sip_sbc_port": 5060,
    "sip_max_secs": 300,            # max. omroepduur (veiligheid tegen 'open microfoon')
    "sip_intro": True,              # intro (preroll) vóór de live omroep
    "sip_outro": True,              # outro ná de live omroep
    "sip_gain": 100,                # volume van de beller over de speakers (%, via PST-softvol; 100 = normaal)
    "sip_allowed_exts": [],         # toegestane extensies (leeg = alle interne); buitenlijn (>3 cijfers) altijd geweigerd
}
settings = _load_json(SETTINGS_JSON, dict(SETTINGS_DEFAULTS))
for _k, _v in SETTINGS_DEFAULTS.items():   # nieuwe default-sleutels invullen (bestaande blijven)
    settings.setdefault(_k, _v)

# Versie = de CODE-versie (VERSION-bestand in de repo), niet per-installatie. Zo
# klopt de weergegeven versie na een `omroepweb-update` in elke winkel.
try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")) as _vf:
        _code_ver = _vf.read().strip()
    if _code_ver and settings.get("version") != _code_ver:
        settings["version"] = _code_ver
        _save_json(SETTINGS_JSON, settings)
except Exception:
    pass

# OIDC config opgeslagen apart (bevat secret)
oidc_cfg = _load_json(OIDC_JSON, {
    "enabled": False,
    "provider_name": "Authentik",
    "discovery_url": "",
    "client_id": "",
    "client_secret": "",
    "redirect_uri": "",
    "scope": "openid email profile groups",
    "group_claim": "groups",
    "group_admin": "radio-admin",
    "group_operator": "radio-operator",
    "group_user": "radio-gebruiker",
})

# Spotify Web API-config (huisaccount, Premium) — apart bestand want het bevat een secret.
# redirect_uri leeg = automatisch de stream-callback (zie _sp_redirect_uri).
spotify_cfg = _load_json(SPOTIFY_JSON, {
    "client_id":     "",
    "client_secret": "",
    "refresh_token": "",
    "redirect_uri":  "",
})

# Gebruikers
users         = _load_json(USERS_JSON, {})
logs          = _load_json(LOGS_JSON,   [])
preset_names  = _load_json(NAMES_JSON,  {})
preset_vols   = _load_json(PVOL_JSON,   {})
schedules     = _load_json(SCHED_JSON,  [])
preset_flags  = _load_json(PFLAGS_JSON, {})
preset_icons  = _load_json(PICONS_JSON,  {})
_preset_icons_lock = threading.Lock()

_logs_lock         = threading.Lock()
_preset_names_lock = threading.Lock()
_preset_vols_lock  = threading.Lock()
_users_lock        = threading.Lock()
_oidc_meta_lock    = threading.Lock()
_oidc_meta_cache   = {}

# ──────────────────────────────────────────────
# SECRET_KEY: persistent opslaan zodat sessies een herstart overleven.
# Voorheen werd bij elke start een nieuwe random key gegenereerd waardoor
# alle sessie-cookies ongeldig werden (iedereen uitgelogd na restart).
# ──────────────────────────────────────────────
def _load_or_create_secret() -> str:
    env = (os.environ.get("SECRET_KEY") or "").strip()
    if env:
        return env
    try:
        if os.path.exists(SECRET_FILE):
            with open(SECRET_FILE, "r") as f:
                key = f.read().strip()
            if key:
                return key
        key = secrets.token_hex(32)
        with open(SECRET_FILE, "w") as f:
            f.write(key)
        os.chmod(SECRET_FILE, 0o600)
        return key
    except Exception:
        return secrets.token_hex(32)

app.secret_key = _load_or_create_secret()

# ──────────────────────────────────────────────
# Cookie instellingen voor iframe-compatibiliteit (Home Assistant)
# SameSite=None + Secure=True zodat cookies werken in een iframe
# ──────────────────────────────────────────────
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_COOKIE_SECURE"]   = True
app.config["SESSION_COOKIE_HTTPONLY"] = True

# ──────────────────────────────────────────────
# After-request:
# - iframe embedding toestaan via CSP frame-ancestors
#   (X-Frame-Options: ALLOWALL is geen geldige waarde en is verwijderd)
# - Session-cookie krijgt het "Partitioned"-attribuut (CHIPS) zodat de
#   sessie in een cross-site iframe blijft werken in Chrome/Android,
#   die third-party cookies zonder dit attribuut blokkeren.
# ──────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers.pop("X-Frame-Options", None)
    response.headers["Content-Security-Policy"] = "frame-ancestors *"
    return response

class _PartitionedCookieMiddleware:
    """Voegt '; Partitioned' toe aan de sessie-cookie. Dit moet als WSGI-
    middleware (dus ná Flask's session-save, die pas na after_request
    draait), anders is de Set-Cookie header er nog niet."""
    def __init__(self, wsgi_app, cookie_name: str):
        self.wsgi_app = wsgi_app
        self.prefix   = cookie_name + "="
    def __call__(self, environ, start_response):
        def _sr(status, headers, exc_info=None):
            patched = []
            for k, v in headers:
                if (k.lower() == "set-cookie" and v.startswith(self.prefix)
                        and "Partitioned" not in v):
                    v = v + "; Partitioned"
                patched.append((k, v))
            return start_response(status, patched, exc_info)
        return self.wsgi_app(environ, _sr)

app.wsgi_app = _PartitionedCookieMiddleware(
    app.wsgi_app, app.config.get("SESSION_COOKIE_NAME", "session"))

# ──────────────────────────────────────────────
# Raspberry Pi / Raspotify integratie
# ──────────────────────────────────────────────
PI_SSH_HOST  = os.environ.get("PI_SSH_HOST", "")
PI_SSH_USER  = os.environ.get("PI_SSH_USER", "radio")
PI_SSH_KEY   = os.environ.get("PI_SSH_KEY",  os.path.expanduser("~/.ssh/omroepweb_pi"))
PI_MIXER     = os.environ.get("PI_MIXER",    "PCM")
PI_ENABLED   = os.environ.get("PI_ENABLED",  "1") == "1"
# V7-cutover: go-librespot draait nu LOKAAL op de VM. In deze modus lezen/bedienen
# we Spotify rechtstreeks via de lokale API (127.0.0.1:3678) i.p.v. SSH naar de Pi,
# en dempt/muut Spotify via de SPOT-softvol i.p.v. de Pi-PCM. Zet op 0 (env) +
# herstart om terug te vallen op de oude Pi-SSH-route (rollback).
PI_LOCAL_GLR = os.environ.get("PI_LOCAL_GLR", "1") == "1"
# Vast account-id van het huis-account (go-librespot state.json bevat geen losse
# username-sleutel); gebruikt om de "Gecast door …"-badge NIET te tonen als het
# huis-account zelf speelt.
HOUSE_SP_USER = os.environ.get("HOUSE_SP_USER", "")   # generiek; per winkel via settings.house_sp_user

PI_DUCK_DEFAULT = 0          # 0 = achtergrond volledig stil tijdens omroep
PI_FADE_STEP    = 8
PI_FADE_DELAY   = 0.02

# Max. tijd dat het afspeelpad wácht tot Spotify (Pi, via SSH) écht stil is
# vóór de preroll begint. Met een warme SSH-verbinding is de duck ~50ms; deze
# grens zorgt dat de preset óók direct start als de Pi even traag/koud is.
PI_DUCK_WAIT      = 0.8
# Houd de SSH-ControlMaster warm (< ControlPersist=300s) zodat de Spotify-duck
# ALTIJD ~50ms is i.p.v. soms seconden na een koude verbinding.
PI_KEEPALIVE_SECS = 240

# SSH ControlMaster: de eerste verbinding blijft 5 min open en wordt
# hergebruikt. Elke vervolgcall duurt daardoor ~50ms i.p.v. 0.5–3s
# (nieuwe TCP+SSH-handshake). Dit was de hoofdoorzaak van de vertraging
# tussen het klikken op een preset en het daadwerkelijke afspelen.
_SSH_CTL = "/tmp/omroepweb_ssh-%r@%h:%p"

def _pi_ssh(cmd: str) -> tuple:
    if not PI_ENABLED:
        return 0, ""
    try:
        r = subprocess.run(
            ["ssh", "-i", PI_SSH_KEY,
             "-o", "StrictHostKeyChecking=no",
             "-o", "ConnectTimeout=3",
             "-o", "ControlMaster=auto",
             "-o", f"ControlPath={_SSH_CTL}",
             "-o", "ControlPersist=300",
             f"{PI_SSH_USER}@{PI_SSH_HOST}", cmd],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=8
        )
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        log_action(f"Pi SSH fout: {e}", source="system")
        return 1, str(e)

def pi_get_volume() -> int:
    if PI_LOCAL_GLR:
        try: return get_mixer(MIXER_SPOT)[0]
        except Exception: return -1
    rc, out = _pi_ssh(f"amixer sget {PI_MIXER}")
    m = re.search(r"\[(\d{1,3})%\]", out)
    return int(m.group(1)) if m else -1

def pi_set_volume(pct: int):
    pct = max(0, min(100, int(pct)))
    if PI_LOCAL_GLR:
        set_mixer(MIXER_SPOT, pct)
        return
    _pi_ssh(f"amixer sset {PI_MIXER} {pct}%")

def pi_fade_volume(start: int, end: int):
    step = PI_FADE_STEP if end > start else -PI_FADE_STEP
    for v in range(start, end, step):
        pi_set_volume(v)
        time.sleep(PI_FADE_DELAY)
    pi_set_volume(end)

def pi_raspotify_restart():
    # Herstart de Spotify-speler. V7: go-librespot draait LOKAAL op de VM, dus
    # herstarten we die hier (NOPASSWD-sudo). Anders (rollback) via SSH naar de Pi.
    if PI_LOCAL_GLR:
        try:
            r = subprocess.run(["sudo", "-n", "systemctl", "restart", "go-librespot.service"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
            ok = (r.returncode == 0)
            log_action("go-librespot herstart (VM)" + ("" if ok else f" — mislukt: {r.stderr.strip()[:80]}"),
                       source="system")
            return ok
        except Exception as e:
            log_action(f"go-librespot herstart fout: {e}", source="system")
            return False
    svc = "go-librespot" if spotify_control_on() else "raspotify"
    rc, out = _pi_ssh(f"sudo -n systemctl restart {svc}")
    log_action(f"{svc} herstart (rc={rc})", source="system")
    return rc == 0

_pi_vol_before: int = 100
_pi_duck_lock = threading.Lock()

def pi_duck():
    """Zet Spotify (Pi) stil (of op het ingestelde omroep-niveau) in één enkele
    SSH-roundtrip: eerst huidige stand uitlezen, daarna direct de omroep-waarde
    zetten. Voorheen waren dit twee losse SSH-verbindingen (get + set) — nu één
    command, één verbinding. Standaard is dit 0 (volledig stil tijdens omroep)."""
    if PI_LOCAL_GLR:          # V7: Spotify-duck loopt via SPOT (_spot_duck in _duck_local)
        return
    global _pi_vol_before
    duck_pct = _omroep_bg_level()
    with _pi_duck_lock:
        rc, out = _pi_ssh(f"amixer sget {PI_MIXER}; amixer sset {PI_MIXER} {duck_pct}%")
        m = re.search(r"\[(\d{1,3})%\]", out)
        if m:
            cur = int(m.group(1))
            # Bescherm tegen dubbel ducken: als de uitgelezen stand al de
            # duck-waarde is, behouden we het eerder opgeslagen volume.
            if cur != duck_pct:
                _pi_vol_before = cur

def pi_unduck():
    if PI_LOCAL_GLR:          # V7: herstel loopt via SPOT (_spot_unduck in _unduck_local)
        return
    with _pi_duck_lock:
        target = _pi_vol_before
    pi_set_volume(target)

def _pi_keepalive_loop():
    """Houdt de SSH-ControlMaster naar de Pi warm. Zonder dit vervalt de
    gemultiplexte verbinding na ControlPersist (300s) en kost de eerste duck
    daarna 0,5–3s (volledige SSH-handshake) — precies wanneer Spotify vól door
    de preroll heen bleef lopen. Met deze ping blijft elke duck ~50ms."""
    while True:
        time.sleep(PI_KEEPALIVE_SECS)
        if PI_ENABLED and not PI_LOCAL_GLR:   # V7: geen SSH meer nodig
            try: _pi_ssh("true")
            except Exception: pass

# ── Now-playing (raspotify / go-librespot) ───────────────────────
# In raspotify-modus schrijft de onevent-hook /run/raspotify/nowplaying.json.
# In go-librespot-modus (settings.spotify_control aan) schrijft de websocket-
# bridge /run/go-librespot-np/nowplaying.json in HETZELFDE formaat. We lezen dat
# samen met het Pi-volume in ÉÉN SSH-roundtrip, met korte cache.
PI_NP_PATH_RASPOTIFY = "/run/raspotify/nowplaying.json"
PI_NP_PATH_GOLIBRE   = "/run/go-librespot-np/nowplaying.json"
GLR_API              = "127.0.0.1:3678"   # lokale go-librespot besturings-API op de Pi
VM_GLR_API           = "127.0.0.1:3678"   # go-librespot dat LOKAAL op de VM draait (nieuw)
_vm_glr_lock         = threading.Lock()
_vm_glr_cache        = {"ts": 0.0, "raw": None}

def _vm_glr_status(max_age: float = 1.0) -> dict:
    """Ruwe /status van de lokale VM go-librespot, kort gecachet. {} bij fout."""
    now = time.time()
    with _vm_glr_lock:
        if _vm_glr_cache["raw"] is not None and now - _vm_glr_cache["ts"] < max_age:
            return _vm_glr_cache["raw"]
    d = {}
    try:
        r = urllib.request.urlopen(f"http://{VM_GLR_API}/status", timeout=1.5)
        d = json.loads(r.read().decode("utf-8") or "{}")
    except Exception:
        d = {}
    with _vm_glr_lock:
        _vm_glr_cache.update(ts=time.time(), raw=d)
    return d

def _vm_spotify_playing() -> bool:
    """True als de lokale VM go-librespot nu een nummer speelt (1s gecachet)."""
    d = _vm_glr_status()
    return bool(d.get("track") and not d.get("stopped") and not d.get("paused"))

def _glr_np_from_status(d: dict):
    """Map go-librespot /status → het now-playing-dictformaat dat current_state,
    de Spotify-UI en de geschiedenis verwachten (name/artist/album/cover/uri/
    state/position_ms/duration_ms/updated_at/is_explicit/played_by). None als er
    niets speelt."""
    t = (d or {}).get("track")
    if not t:
        return None
    if d.get("stopped"):   state = "stopped"
    elif d.get("paused"):  state = "paused"
    else:                  state = "playing"
    uri = (t.get("uri") or "").strip()
    tid = uri.rsplit(":", 1)[-1] if uri.startswith("spotify:track:") else ""
    np = {
        "name":        t.get("name", ""),
        "artist":      ", ".join(t.get("artist_names") or []),
        "album":       t.get("album_name", ""),
        "cover":       t.get("album_cover_url", ""),
        "uri":         uri,
        "track_id":    tid,
        "state":       state,
        "position_ms": int(t.get("position") or 0),
        "duration_ms": int(t.get("duration") or 0),
        "updated_at":  int(time.time()),
    }
    # Explicit-vlag alleen uit de cache halen (niet-blokkerend); de explicit-guard
    # vult die cache binnen enkele seconden via _track_is_explicit.
    if tid:
        with _EXPLICIT_CACHE_LOCK:
            np["is_explicit"] = bool(_EXPLICIT_CACHE.get(tid))
    # Castende account tonen — maar niet als het huis-account zelf speelt.
    uname = (d.get("username") or "").strip()
    if uname and uname != (settings.get("house_sp_user") or HOUSE_SP_USER):
        np["played_by"] = _resolve_caster_name(uname)
    return np

PI_SNAPSHOT_TTL  = 2.0
_pi_snap_lock    = threading.Lock()
_pi_snap_cache   = {"ts": 0.0, "vol": -1, "np": None}

def spotify_control_on() -> bool:
    """True = go-librespot-modus (besturing + now-playing via bridge)."""
    return bool(settings.get("spotify_control"))

def _pi_np_path() -> str:
    return PI_NP_PATH_GOLIBRE if spotify_control_on() else PI_NP_PATH_RASPOTIFY

def pi_snapshot():
    """(volume, nowplaying-dict|None), gecachet. In de V7-modus (PI_LOCAL_GLR)
    lokaal uit de VM go-librespot /status + het SPOT-volume; anders de oude
    Pi-SSH-roundtrip (rollback)."""
    now = time.time()
    with _pi_snap_lock:
        if now - _pi_snap_cache["ts"] < PI_SNAPSHOT_TTL:
            return _pi_snap_cache["vol"], _pi_snap_cache["np"]
    vol, np = -1, None
    if PI_LOCAL_GLR:
        np = _glr_np_from_status(_vm_glr_status())
        try: vol = get_mixer(MIXER_SPOT)[0]
        except Exception: vol = -1
        _record_track_history(np)
        with _pi_snap_lock:
            _pi_snap_cache.update(ts=time.time(), vol=vol, np=np)
        return vol, np
    if PI_ENABLED:
        glr = spotify_control_on()
        cmd = (f"amixer sget {PI_MIXER}; echo '<<<NP>>>'; cat {_pi_np_path()} 2>/dev/null; "
               f"echo '<<<NOW>>>'; date +%s")
        if glr:   # in go-librespot-modus óók de castende account ophalen
            cmd += f"; echo '<<<USER>>>'; curl -s -m 2 http://{GLR_API}/status 2>/dev/null"
        rc, out = _pi_ssh(cmd)
        vpart, _, rest = out.partition("<<<NP>>>")
        npart, _, rest2 = rest.partition("<<<NOW>>>")
        nowpart, _, userpart = rest2.partition("<<<USER>>>")
        m = re.search(r"\[(\d{1,3})%\]", vpart)
        if m: vol = int(m.group(1))
        npart = npart.strip()
        if npart:
            try: np = json.loads(npart)
            except Exception: np = None
        # Castende account → leesbare weergavenaam (gecachet per id).
        if np and glr:
            mu = re.search(r'"username"\s*:\s*"([^"]+)"', userpart or "")
            if mu:
                np["played_by"] = _resolve_caster_name(mu.group(1))
        # Positie serverside extrapoleren met de KLOK VAN DE PI (updated_at komt
        # ook van de Pi → geen klok-skew). librespot stuurt tijdens doorspelen
        # geen events, dus zonder dit zou de balk op de laatste event-positie
        # blijven staan. De client verfijnt daarna nog vloeiend vanaf ontvangst.
        if np:
            try:
                pi_now = int((nowpart or "").strip() or 0)
                pos = int(np.get("position_ms") or 0)
                if pi_now and np.get("state") == "playing":
                    pos += max(0, pi_now - int(np.get("updated_at") or pi_now)) * 1000
                dur = int(np.get("duration_ms") or 0)
                if dur > 0: pos = min(pos, dur)
                np["position_ms"] = pos
            except Exception: pass
    _record_track_history(np)
    with _pi_snap_lock:
        _pi_snap_cache.update(ts=time.time(), vol=vol, np=np)
    return vol, np

# ── Afgespeelde nummers (geschiedenis) ───────────────────────────
# We houden zelf bij welke nummers er langskwamen (via de go-librespot-events die
# pi_snapshot leest). Geen Spotify Web API nodig — dat token wordt door Spotify
# geweigerd (429). Ontdubbeld per uri; nieuwste eerst; persistent over herstart.
TRACK_HISTORY_JSON = os.path.join(APP_DIR, "track_history.json")
TRACK_HISTORY_MAX  = 50
_track_history_lock = threading.Lock()
def _load_track_history():
    try:
        with open(TRACK_HISTORY_JSON) as f:
            d = json.load(f)
            return d if isinstance(d, list) else []
    except Exception:
        return []
_track_history = _load_track_history()

def _record_track_history(np):
    if not np or not np.get("name"):
        return
    uri = np.get("uri") or np.get("name")
    with _track_history_lock:
        if _track_history and _track_history[0].get("uri") == uri:
            return                         # zelfde nummer speelt nog → niet dubbel
        caster = np.get("played_by") or ""
        _track_history.insert(0, {
            "name":     np.get("name", ""),
            "artist":   np.get("artist", ""),
            "album":    np.get("album", ""),
            "cover":    np.get("cover", ""),
            "uri":      uri,
            "explicit": bool(np.get("is_explicit")),
            "played_by": caster,
            "played_at": int(time.time()),
        })
        del _track_history[TRACK_HISTORY_MAX:]
        try:
            with open(TRACK_HISTORY_JSON, "w") as f:
                json.dump(_track_history, f)
        except Exception:
            pass
    # Buiten de lock loggen (audit): elk nieuw nummer + wie het cast.
    naam = np.get("name", "")
    art  = np.get("artist", "")
    msg  = f"Spotify speelt: {naam}" + (f" — {art}" if art else "")
    if caster:
        msg += f" (gecast door {caster})"
    log_action(msg, source="spotify", user=(caster or "Spotify"))

def _track_history_list():
    with _track_history_lock:
        return list(_track_history)

def _mark_track_skipped(tid_or_uri: str, reason: str = "explicit"):
    """Markeer het (recent gespeelde) nummer als overgeslagen + de reden, zodat
    de geschiedenis toont dat een expliciet nummer automatisch is overgeslagen."""
    if not tid_or_uri:
        return
    with _track_history_lock:
        for t in _track_history[:6]:
            u = t.get("uri", "")
            if u == tid_or_uri or (tid_or_uri and u.endswith(tid_or_uri)):
                t["skipped"] = True
                t["skip_reason"] = reason
                try:
                    with open(TRACK_HISTORY_JSON, "w") as f:
                        json.dump(_track_history, f)
                except Exception:
                    pass
                return

# ── PLUS Radio now-playing via de Streamit Lisa (telnet, poort 23) ─
# `getinfo title` geeft exact het nummer dat nu speelt. Geen Shazam nodig.
# De Lisa accepteert één verbinding tegelijk → alle toegang onder een lock.
LISA_TTL = 2.0
_lisa_cache = {"ts": 0.0, "title": ""}
_lisa_lock  = threading.Lock()
_lisa_last_pushed = ""     # laatst naar Icecast gepushte titel (voor prompte updates)

def _strip_telnet(b: bytes) -> bytes:
    out = bytearray(); i = 0
    while i < len(b):
        if b[i] == 0xFF: i += 3           # IAC + command + option overslaan
        else: out.append(b[i]); i += 1
    return bytes(out)

class _LisaConn:
    """Persistente telnet-verbinding naar de Lisa. De Lisa accepteert één
    verbinding tegelijk; daarom houden poll én beheer-console dezelfde socket
    aan, geserialiseerd via een lock. Reconnect automatisch bij verlies."""
    def __init__(self):
        self.sock = None
        self.lock = threading.Lock()
        self.history = []                 # laatste console-commando's (voor beheer)

    def _ensure(self):
        if self.sock is not None:
            return
        host = settings.get("lisa_host", "")
        port = int(settings.get("lisa_port", 23) or 23)
        s = socket.create_connection((host, port), timeout=4)
        s.settimeout(1.0)
        try: s.recv(2048)                 # begroeting/IAC opvangen
        except Exception: pass
        self.sock = s

    def _drop(self):
        try: self.sock.close()
        except Exception: pass
        self.sock = None

    def send(self, cmd: str, wait: float = 1.5, log: bool = False) -> str:
        """Stuur één commando en geef de respons terug (tot de '>'-prompt).
        Sommige commando's (loglev, quit, reset) verbreken de sessie — dan
        reconnecten we automatisch bij de volgende send."""
        with self.lock:
            for attempt in (1, 2):
                try:
                    self._ensure()
                    self.sock.sendall((cmd + "\r\n").encode())
                    data = b""; end = time.time() + wait
                    while time.time() < end:
                        try:
                            ch = self.sock.recv(4096)
                            if not ch:
                                self._drop(); break
                            data += ch
                            if data.rstrip().endswith(b">"): break
                        except socket.timeout:
                            if data: break
                    resp = _strip_telnet(data).decode(errors="replace").strip()
                    if log:
                        self.history.append({"cmd": cmd, "resp": resp, "ts": int(time.time())})
                        del self.history[:-100]
                    return resp
                except Exception:
                    self._drop()
            if log:
                self.history.append({"cmd": cmd, "resp": "(geen verbinding met de Lisa)",
                                     "ts": int(time.time())})
                del self.history[:-100]
            return ""

_lisa_conn = _LisaConn()

def lisa_now_playing(force: bool = False) -> str:
    """Huidige PLUS Radio-titel (gecachet). Snelle uitlezing — alléén de titel,
    zodat de commercial-detectie elke seconde kan draaien."""
    if not settings.get("lisa_enabled", True):
        return ""
    now = time.time()
    if not force and now - _lisa_cache["ts"] < LISA_TTL:
        return _lisa_cache["title"]
    title = _lisa_cache["title"]
    out = _lisa_conn.send("getinfo title")
    m = re.search(r"title\s*=\s*(.+)", out or "")
    if m: title = m.group(1).strip().strip("\r").strip()
    with _lisa_lock:
        _lisa_cache.update(ts=time.time(), title=title)
    return title

def _lisa_refresh_meta():
    """Kanaal (presetid) verversen — minder vaak dan de titel."""
    if not settings.get("lisa_enabled", True):
        return
    out = _lisa_conn.send("getinfo presetid")
    mc = re.search(r"presetid\s*=\s*(\d+)", out or "")
    if mc:
        with _lisa_lock:
            _lisa_cache["channel"] = int(mc.group(1))

def lisa_current_title() -> str:
    """Alleen de gecachete titel (geen netwerk) — voor current_state/SSE."""
    return _lisa_cache.get("title", "")

def lisa_current_channel() -> int:
    return int(_lisa_cache.get("channel", 0) or 0)

def lisa_set_channel(n: int) -> bool:
    """Wissel naar kanaal 1 (Plus Main) of 2 (Plus Easy) via 'pp <n>'."""
    n = 2 if int(n) == 2 else 1
    out = _lisa_conn.send(f"pp {n}")
    ok = "OK" in (out or "")
    if ok:
        with _lisa_lock:
            _lisa_cache["channel"] = n
            _lisa_cache["ts"] = 0.0        # volgende poll haalt meteen de verse titel
    return ok

# ── Commercials op de Lisa-SD-kaart (handmatig omroepen via 'sc <bestand>') ──
_lisa_com_cache = {"ts": 0.0, "files": []}
_lisa_com_lock  = threading.Lock()
# Muziek heeft hash-namen (77DF2C35.mp3) of MnnnTnnn.mp3; commercials hebben een
# onderstreping + campagnenaam (25539_101427_PlusSup.mp3). Zo onderscheiden we ze.
_COMMERCIAL_RE = re.compile(r"^[0-9A-Za-z]+_.*[A-Za-z]{2,}\.mp3$", re.I)

def lisa_list_commercials(force: bool = False):
    """Lijst met commercial-bestanden op de SD-kaart (5 min gecachet)."""
    now = time.time()
    with _lisa_com_lock:
        if not force and now - _lisa_com_cache["ts"] < 300 and _lisa_com_cache["files"]:
            return list(_lisa_com_cache["files"])
    files = []
    try:
        out = ""
        # De gedeelde telnet-verbinding kan door de 1s-poll een 'één-terug'-respons
        # geven; probeer daarom tot een echte mappenlijst binnenkomt.
        for _ in range(4):
            out = _lisa_conn.send("dir", wait=4.0)
            if out and out.count(".mp3") > 5:
                break
            time.sleep(0.2)
        for line in (out or "").splitlines():
            nm = line.strip()
            if _COMMERCIAL_RE.match(nm):
                files.append(nm)
    except Exception:
        files = []
    # Nieuwste eerst: DDJ nummert spots oplopend, dus hoogste nummer bovenaan.
    def _com_num(n):
        m = re.match(r"^(\d+)", n)
        return int(m.group(1)) if m else -1
    files = sorted(set(files), key=lambda n: (-_com_num(n), n))
    if files:
        with _lisa_com_lock:
            _lisa_com_cache.update(ts=time.time(), files=files)
    return files

def lisa_play_commercial(fname: str) -> bool:
    """Roep een commercial om via 'sc <bestand>'. Alleen bestanden die echt op de
    kaart staan (validatie tegen de lijst) worden geaccepteerd."""
    fname = (fname or "").strip()
    if not fname or fname not in lisa_list_commercials():
        return False
    out = _lisa_conn.send(f"sc {fname}", wait=2.0)
    return "ERROR" not in (out or "").upper()

# Afgespeelde nummers op PLUS Radio (zelf bijgehouden, net als bij Spotify)
LISA_HISTORY_JSON = os.path.join(APP_DIR, "plusradio_history.json")
LISA_HISTORY_MAX  = 50
_lisa_hist_lock = threading.Lock()
def _load_lisa_history():
    try:
        with open(LISA_HISTORY_JSON) as f:
            d = json.load(f); return d if isinstance(d, list) else []
    except Exception:
        return []
_lisa_history = _load_lisa_history()

# Huidige titel als ICY-metadata naar de Icecast-stream (instelbaar per winkel).
def _icecast_push_title(title: str):
    if not settings.get("icecast_meta_enabled", True) or not title:
        return
    try:
        import base64
        from urllib.parse import urlencode
        url  = settings.get("icecast_admin_url", "http://localhost:8000/admin/metadata")
        # Verrijkte StreamTitle als Shazam het nummer kent: "Artiest - Titel".
        # (De zendernaam "PLUS Radio" staat al als icy-name op de stream.) Anders
        # de kale titel. Een albumcover kan NIET mee via Icecast-metadata — die
        # levert de webplayer los op via /api/nowplaying.
        e = _lisa_enrich_for(title)
        if e.get("artist") and e.get("title"):
            song = f"{e['artist']} - {e['title']}"
        else:
            song = f"PLUS Radio - {title}"
        q = urlencode({"mount": settings.get("icecast_mount", "/rca"), "mode": "updinfo",
                       "song": song, "charset": "UTF-8"})
        req = urllib.request.Request(url + "?" + q)
        user = settings.get("icecast_admin_user", "admin")
        pw   = settings.get("icecast_admin_pass", "")
        cred = base64.b64encode(f"{user}:{pw}".encode()).decode()
        req.add_header("Authorization", "Basic " + cred)
        urllib.request.urlopen(req, timeout=4).read()
    except Exception:
        pass

def _tunein_push(title: str = "", artist: str = "", album: str = "", commercial: bool = False):
    """Geef het huidige nummer door aan TuneIn (AIR API 'Now Playing').
    Fire-and-forget in een thread zodat de detectie niet blokkeert."""
    if not settings.get("tunein_enabled"):
        return
    pid = (settings.get("tunein_partner_id") or "").strip()
    key = (settings.get("tunein_partner_key") or "").strip()
    sid = (settings.get("tunein_station_id") or "").strip()
    if not (pid and key and sid):
        return
    def _go():
        try:
            from urllib.parse import urlencode
            params = {"partnerId": pid, "partnerKey": key, "id": sid}
            if commercial:
                params["commercial"] = "true"       # TuneIn: reclame speelt
            else:
                params["title"] = title or ""
                if artist: params["artist"] = artist
                if album:  params["album"]  = album
            url = "http://air.radiotime.com/Playing.ashx?" + urlencode(params)
            urllib.request.urlopen(url, timeout=5).read()
        except Exception:
            pass
    threading.Thread(target=_go, daemon=True).start()

# ── Commercial-detectie: reclame op PLUS Radio → Spotify dempen ──
# De Lisa geeft tijdens een reclame de titel "Commercial" terug. Zodra we die
# zien: RCA aan (reclame moet hoorbaar zijn) + Spotify (Pi) dempen; daarna terug.
_commercial_active = False
def _title_is_commercial(title: str) -> bool:
    return (title or "").strip().lower() == "commercial"

# Runtime-volume van de online stream (rca-stream ffmpeg) via zmq (azmq-filter).
STREAM_ZMQ_ADDR    = "tcp://127.0.0.1:5555"
STREAM_NORMAL_GAIN = 20.0     # gelijk aan volume@vol in rca-stream.service
def _stream_set_volume(gain: float):
    try:
        import zmq
        s = zmq.Context.instance().socket(zmq.REQ)
        s.setsockopt(zmq.LINGER, 0); s.setsockopt(zmq.RCVTIMEO, 1500); s.setsockopt(zmq.SNDTIMEO, 1500)
        s.connect(STREAM_ZMQ_ADDR)
        s.send_string(f"volume@vol volume {max(0.0, float(gain)):.3f}")
        s.recv_string()
        s.close()
    except Exception:
        pass

# Tijdelijke instrumentatie (ms-precisie) om de reclame-duck te meten. Schrijft
# naar ~/omroepweb/commercial_debug.log; veilig te verwijderen na de meting.
COMMERCIAL_DEBUG   = True
_COMM_DEBUG_FILE   = os.path.join(APP_DIR, "commercial_debug.log")
_comm_on_ts        = 0.0
def _comm_debug(line: str):
    if not COMMERCIAL_DEBUG:
        return
    try:
        with open(_COMM_DEBUG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ── Commercial-replay (experimenteel, settings["commercial_replay"], std. UIT) ──
# We houden de lijn-in continu in een geheugen-ringbuffer. Zodra een commercial
# wordt gedetecteerd (Lisa-titel, ~4s laat) spelen we 'm — inclusief het gemiste
# begin — vertraagd over Spotify af via de BG-mixer. Niets wordt op schijf bewaard;
# na het afspelen is de opname weg (alleen geheugen).
_COMM_SR, _COMM_CH   = 48000, 2
_COMM_PREROLL_SECS   = 8.0      # zoveel pakken we terug (dekt de ~4-6s Lisa-lag + marge)
_COMM_RING_SECS      = 16.0
_COMM_SILENCE_DB     = -35      # onder deze drempel = stilte (voor het bijsnijden)
_COMM_GAP_SECS       = 0.4      # zó lange stilte = grens (transitie muziek↔reclame is vaak maar ~0,5s)
# Loudnorm alleen op de DOWNLOAD-mp3 (de lijn-in staat erg zacht); het afspelen
# in de winkel houdt het bronniveau aan (via RCA_GAIN), anders veel te hard.
_COMM_LOUDNORM_AF    = "loudnorm=I=-16:TP=-1.5:LRA=11"

def _comm_detect_bounds(raw_path):
    """Vind begin/einde van de eigenlijke reclame. De opname bevat vóór (en soms ná)
    de spot nog PLUS Radio-muziek, gescheiden door korte stiltes. We splitsen op die
    stiltes en kiezen het LANGSTE geluidssegment als de reclame — die is langer dan de
    (per dag wisselende) aanloop-/na-muziek, dus dit past zich vanzelf aan elke
    reclamelengte en -timing aan. Geeft (start_sec, end_sec|None)."""
    try:
        dur = os.path.getsize(raw_path) / float(_COMM_SR * _COMM_CH * 2)
    except Exception:
        dur = 0.0
    try:
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats",
             "-f", "s16le", "-ar", str(_COMM_SR), "-ac", str(_COMM_CH), "-i", raw_path,
             "-af", f"silencedetect=noise={_COMM_SILENCE_DB}dB:d={_COMM_GAP_SECS}",
             "-f", "null", "-"],
            capture_output=True, text=True, timeout=30).stderr
    except Exception:
        return 0.0, None
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", out)]
    ends   = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    gaps   = sorted(zip(starts, ends))
    if not gaps or dur <= 0:
        return 0.0, None
    # Geluidssegmenten = het complement van de stiltes.
    segs, prev = [], 0.0
    for gs, ge in gaps:
        gs = max(0.0, gs)
        if gs > prev + 0.15:
            segs.append((prev, gs))
        prev = max(prev, ge)
    if dur > prev + 0.15:
        segs.append((prev, dur))
    if not segs:
        return 0.0, None
    start, end = max(segs, key=lambda s: s[1] - s[0])   # langste segment = de reclame
    start = max(0.0, start - 0.10)                       # klein randje mee
    if end >= dur - 0.20:
        end = None                                      # loopt tot het einde → geen na-trim
    else:
        end = min(dur, end + 0.10)
    return start, end
_comm_ring           = collections.deque()
_comm_ring_lock      = threading.Lock()
_comm_ring_run       = False
_comm_capture_run    = threading.Event()
_comm_capture_active = False
_comm_capture_used   = False
_comm_pending        = {"file": None}   # klaargezette commercial (WAV) voor de volgende overgang
_comm_pending_lock   = threading.Lock()
_comm_playing        = False

def _comm_ring_loop():
    global _comm_ring_run
    chunk_bytes = (_COMM_SR // 10) * _COMM_CH * 2      # ~0,1s
    while _comm_ring_run:
        p = None
        try:
            p = subprocess.Popen(["arecord", "-D", "linein", "-q", "-f", "S16_LE",
                                  "-c", str(_COMM_CH), "-r", str(_COMM_SR), "-t", "raw"],
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            while _comm_ring_run:
                data = p.stdout.read(chunk_bytes)
                if not data:
                    break
                now = time.time()
                with _comm_ring_lock:
                    _comm_ring.append((now, data))
                    while _comm_ring and now - _comm_ring[0][0] > _COMM_RING_SECS:
                        _comm_ring.popleft()
        except Exception:
            time.sleep(1)
        finally:
            if p:
                try: p.terminate(); p.wait(timeout=2)
                except Exception:
                    try: p.kill()
                    except Exception: pass
    with _comm_ring_lock:
        _comm_ring.clear()

def _kill_ring_recorders():
    """Ruim (wees-)ringbuffer-arecords op. Het '-q' onderscheidt ze van de RCA-arecord."""
    try:
        subprocess.run(["pkill", "-f", "arecord -D linein -q -f S16_LE"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def _comm_ring_ensure():
    """Start/stop de ringbuffer-opname op basis van de setting; ruimt wezen op."""
    global _comm_ring_run
    want = bool(settings.get("commercial_replay"))
    if not want:
        _comm_ring_run = False
        _kill_ring_recorders()            # ook eventuele wees-recorders weg
        with _comm_pending_lock:
            _comm_pending["file"] = None
        for _f in glob.glob("/tmp/comm_*.wav"):   # klaargezette/oude opnames opruimen
            try: os.remove(_f)
            except Exception: pass
        return
    if not _comm_ring_run:
        _kill_ring_recorders()            # oude wees vóór een nieuwe start opruimen
        _comm_ring_run = True
        threading.Thread(target=_comm_ring_loop, daemon=True).start()

def _capture_commercial_thread():
    """Neem de gedetecteerde commercial op naar een tijdelijk WAV: pre-roll uit de
    buffer (zodat het begin niet mist) + live door tot de commercial voorbij is.
    Knipt het vorige-nummer-stukje vooraan weg en zet 'm klaar om bij de volgende
    Spotify-nummerovergang af te spelen — nooit midden in een nummer."""
    global _comm_capture_active
    wav = None
    try:
        pcm = bytearray()
        cutoff = time.time() - _COMM_PREROLL_SECS
        with _comm_ring_lock:
            for ts, d in _comm_ring:
                if ts >= cutoff:
                    pcm += d
            last_ts = _comm_ring[-1][0] if _comm_ring else (time.time() - _COMM_PREROLL_SECS)
        while _comm_capture_run.is_set():
            with _comm_ring_lock:
                new = [(ts, d) for (ts, d) in _comm_ring if ts > last_ts]
            if new:
                last_ts = new[-1][0]
                for ts, d in new:
                    pcm += d
            else:
                time.sleep(0.05)
        if len(pcm) < _COMM_SR * _COMM_CH:        # < ~0,5s → niks bruikbaars
            return
        # Ruwe opname even naar schijf → grenzen bepalen (stilte/muziek weg) en
        # de uitsnede normaliseren (de lijn-in staat erg zacht).
        rfd, raw = tempfile.mkstemp(suffix=".raw", dir="/tmp", prefix="comm_")
        with os.fdopen(rfd, "wb") as rf: rf.write(bytes(pcm))
        start, end = _comm_detect_bounds(raw)
        fd, wav = tempfile.mkstemp(suffix=".wav", dir="/tmp", prefix="comm_"); os.close(fd)
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-f", "s16le", "-ar", str(_COMM_SR), "-ac", str(_COMM_CH),
               "-ss", f"{max(0.0, start):.3f}"]
        if end and end > start:
            cmd += ["-t", f"{(end - start):.3f}"]
        cmd += ["-i", raw, "-ac", "1", wav]      # alleen bijsnijden (bronniveau behouden)
        try: subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        except Exception: pass
        try: os.remove(raw)
        except Exception: pass
        with _comm_pending_lock:
            old = _comm_pending["file"]
            _comm_pending["file"] = wav
            wav = None                            # niet in finally verwijderen
        if old:
            try: os.remove(old)                   # eerdere, nog niet gespeelde spot weg
            except Exception: pass
    except Exception:
        pass
    finally:
        if wav:
            try: os.remove(wav)
            except Exception: pass
        _comm_capture_active = False

def _start_commercial_capture() -> bool:
    global _comm_capture_active
    if _comm_capture_active:
        return False
    with _comm_ring_lock:
        have = len(_comm_ring)
    if not have:
        return False
    _comm_capture_active = True
    _comm_capture_run.set()
    threading.Thread(target=_capture_commercial_thread, daemon=True).start()
    return True

_COMM_ARCHIVE_KEEP = 2   # aantal laatst opgenomen reclames dat we bewaren voor download

def _archive_commercial(wav):
    """Zet de zojuist afgespeelde reclame-opname als mp3 in het archief (voor
    download door de beheerder) en bewaar alleen de laatste _COMM_ARCHIVE_KEEP.
    Verwijdert daarna de ruwe WAV."""
    try:
        os.makedirs(COMM_ARCHIVE_DIR, exist_ok=True)
        out = os.path.join(COMM_ARCHIVE_DIR, "reclame_" + time.strftime("%Y%m%d-%H%M%S") + ".mp3")
        subprocess.run(                           # download-mp3: wél op nette luisterloudness
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
             "-i", wav, "-af", _COMM_LOUDNORM_AF, "-ac", "2", "-b:a", "192k", out],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        keep = sorted(glob.glob(os.path.join(COMM_ARCHIVE_DIR, "reclame_*.mp3")))
        for old in keep[:-_COMM_ARCHIVE_KEEP]:
            try: os.remove(old)
            except Exception: pass
    except Exception:
        pass
    finally:
        try: os.remove(wav)
        except Exception: pass

def _play_pending_commercial():
    """Pauzeer het zojuist gestarte volgende nummer, speel de klaargezette
    commercial via de BG-mixer, en laat daarna dat nummer nét vanaf het begin
    doorlopen (seek 0 → resume). Archiveer tot slot het opnamebestand."""
    global _comm_playing
    with _comm_pending_lock:
        wav = _comm_pending["file"]; _comm_pending["file"] = None
    if not wav or not os.path.exists(wav):
        _comm_playing = False
        return
    bg_before = None; p = None
    try:
        # Pauzeer en zet het net gestarte nummer terug naar 0, zodat het ná de
        # reclame netjes vanaf het begin speelt i.p.v. midden in de intro.
        _glr_post("/player/pause")
        _glr_post("/player/seek", json.dumps({"position": 0}))
        try:
            bg_before = get_bg_volume_pct()
            set_bg_volume(max(45, min(80, int(_bg_vol_before or 65))))
        except Exception: pass
        # Direct afspelen (geen extra wachttijd → minder stilte vóór de reclame).
        p = subprocess.Popen(                     # bronniveau + modeste boost (matcht PLUS Radio)
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", wav,
             "-filter:a", f"volume={RCA_GAIN}", "-ac", "1", "-f", "alsa", "bg"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p.wait(timeout=90)
    except Exception:
        pass
    finally:
        try:
            if p and p.poll() is None: p.terminate()
        except Exception: pass
        try:
            if bg_before is not None: set_bg_volume(bg_before)
        except Exception: pass
        # Zeker vanaf het begin en dan hervatten → volgend nummer loopt schoon door.
        _glr_post("/player/seek", json.dumps({"position": 0}))
        _glr_post("/player/resume")
        _archive_commercial(wav)                  # bewaren voor download (laatste 2)
        _comm_playing = False

def _comm_boundary_loop():
    """Wacht op een Spotify-nummerovergang; is er een commercial klaargezet, speel
    'm dan af tússen de nummers (nooit midden in een nummer)."""
    global _comm_playing
    last_uri = None
    while True:
        time.sleep(0.4)
        try:
            if not settings.get("commercial_replay"):
                last_uri = None
                continue
            d = _vm_glr_status(0.4)
            t = d.get("track") or {}
            uri = t.get("uri") or None
            playing = bool(t and not d.get("stopped") and not d.get("paused"))
            with _comm_pending_lock:
                pend = bool(_comm_pending["file"])
            if pend and playing and not _comm_playing and last_uri and uri and uri != last_uri:
                last_uri = uri
                _comm_playing = True
                threading.Thread(target=_play_pending_commercial, daemon=True).start()
            elif playing and uri:
                last_uri = uri
        except Exception:
            pass

def _handle_commercial(title: str):
    global _commercial_active, _comm_on_ts, _comm_capture_used
    is_comm = _title_is_commercial(title)
    duck = settings.get("commercial_duck_spotify", True)
    if is_comm and not _commercial_active:
        _commercial_active = True
        # 1. online stream zachter (op ingesteld % van normaal) — meet de zmq-duur
        t0 = time.perf_counter(); wall = time.time()
        try:
            pct = max(0, min(100, int(settings.get("commercial_stream_pct", 50))))
            _stream_set_volume(STREAM_NORMAL_GAIN * pct / 100.0)
        except Exception: pass
        zmq_ms = (time.perf_counter() - t0) * 1000.0
        _comm_on_ts = wall
        _comm_debug(f"{wall:.3f}\tDUCK_ON\tzmq={zmq_ms:.1f}ms\ttitle={title!r}")
        _tunein_push(commercial=True)          # TuneIn: reclame speelt
        _write_nowplaying_json()               # stream-JSON: reclame-vlag
        # 2. Spotify dempen (optioneel) — met replay of live-RCA
        if duck:
            try:
                _comm_capture_used = False
                if settings.get("commercial_replay") and _vm_spotify_playing():
                    # Niet onderbreken: neem de commercial op en speel 'm straks
                    # tússen de nummers af (via _comm_boundary_loop).
                    _comm_capture_used = _start_commercial_capture()
                if not _comm_capture_used:                    # normale weg (geen Spotify / buffer leeg)
                    if not rca_running(): rca_start()         # reclame moet klinken
                    _spot_duck()                              # Spotify (VM, SPOT) dempen
                    if PI_ENABLED and not PI_LOCAL_GLR:
                        _pi_ssh(f"amixer sset {PI_MIXER} mute")
            except Exception: pass
        log_action("Reclame op PLUS Radio → stream zachter" + (" + Spotify gedempt" if duck else ""),
                   source="plusradio", user="PLUS Radio")
    elif not is_comm and _commercial_active:
        _commercial_active = False
        wall = time.time(); dur = (wall - _comm_on_ts) if _comm_on_ts else -1
        try: _stream_set_volume(STREAM_NORMAL_GAIN)           # stream terug naar normaal
        except Exception: pass
        _comm_debug(f"{wall:.3f}\tDUCK_OFF\tduur={dur:.1f}s\tnext_title={title!r}")
        _write_nowplaying_json()               # stream-JSON: reclame voorbij
        if duck:
            try:
                if _comm_capture_used:
                    _comm_capture_run.clear()                 # opname stoppen → WAV wordt klaargezet
                else:
                    _spot_unduck()                            # Spotify (VM, SPOT) herstellen
                    if PI_ENABLED and not PI_LOCAL_GLR and not explicit_blocked():
                        _pi_ssh(f"amixer sset {PI_MIXER} unmute")
            except Exception: pass
            _comm_capture_used = False
        log_action("Reclame voorbij → normaal volume", source="plusradio", user="PLUS Radio")

# ── Shazam-verrijking ──────────────────────────────────────────────────────
# De Lisa kapt titels af op ~16 tekens en geeft geen artiest/albumcover. We
# herkennen het nummer op de line-in (Shazam) en verrijken de now-playing +
# geschiedenis met volledige titel + artiest + album + cover — maar ALLEEN als
# de Shazam-titel overeenkomt met de (afgekapte) getinfo-titel, zodat een
# mismatch nooit een verkeerd nummer toont. getinfo blijft leidend voor de
# snelle detectie en de commercial-afhandeling.
_lisa_enrich        = {}                 # {"key","title","artist","album","year","cover"}
_lisa_enrich_lock   = threading.Lock()
_lisa_reco_inflight = set()
_lisa_reco_lock     = threading.Lock()

def _norm_title(s: str) -> str:
    # Accenten naar ASCII vouwen (Corazón→corazon) vóór het strippen, anders
    # mismatch tussen de platte Lisa-titel en de Shazam-titel met accenten.
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s)

def _shazam_recognize(seconds: int = 6):
    """Neem een korte line-in-clip op en herken via Shazam. Track-dict of None."""
    wav = None
    try:
        import asyncio
        fd, wav = tempfile.mkstemp(suffix=".wav", dir="/tmp"); os.close(fd)
        subprocess.run(["arecord", "-D", "linein", "-d", str(seconds), "-f", "S16_LE",
                        "-c", "2", "-r", "44100", wav],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=seconds + 6)
        from shazamio import Shazam
        async def _go():
            sh = Shazam()
            try:
                return await sh.recognize(wav)
            except AttributeError:
                return await sh.recognize_song(wav)
        return asyncio.run(_go())
    except Exception:
        return None
    finally:
        if wav:
            try: os.remove(wav)
            except Exception: pass

SHAZAM_MAX_TRIES   = 4      # meerdere pogingen: nummers halverwege/luider zijn beter herkenbaar
SHAZAM_RETRY_DELAY = 4.0    # pauze tussen pogingen (ander stuk van het nummer)

def _lisa_enrich_worker(getinfo_title: str):
    key = _norm_title(getinfo_title)
    try:
        for attempt in range(SHAZAM_MAX_TRIES):
            # Speelt er inmiddels een ander nummer? Dan heeft doorgaan geen zin.
            if attempt and _norm_title(lisa_current_title()) != key:
                return
            out = _shazam_recognize()
            t = (out or {}).get("track") or {}
            sh_title  = (t.get("title") or "").strip()
            sh_artist = (t.get("subtitle") or "").strip()
            nt = _norm_title(sh_title)
            # Verificatie: de (afgekapte) getinfo-titel moet matchen met de Shazam-titel.
            if not (sh_title and len(key) >= 4 and (nt.startswith(key) or key.startswith(nt))):
                if attempt < SHAZAM_MAX_TRIES - 1:
                    time.sleep(SHAZAM_RETRY_DELAY)   # even wachten, dan een nieuwe poging
                continue
            album = year = None
            for sec in t.get("sections", []) or []:
                for md in sec.get("metadata", []) or []:
                    lab = (md.get("title") or "").lower()
                    if   lab == "album":              album = md.get("text")
                    elif lab in ("released", "year"): year  = md.get("text")
            imgs  = t.get("images") or {}
            cover = imgs.get("coverarthq") or imgs.get("coverart")
            with _lisa_enrich_lock:
                _lisa_enrich.clear()
                _lisa_enrich.update(key=key, title=sh_title, artist=sh_artist,
                                    album=album, year=year, cover=cover)
            # Bovenste geschiedenis-entry verrijken als die nog dit nummer is.
            with _lisa_hist_lock:
                if _lisa_history and _norm_title(_lisa_history[0].get("title")) == key:
                    _lisa_history[0].update(artist=sh_artist, cover=cover,
                                            full_title=sh_title, album=album)
                    try:
                        with open(LISA_HISTORY_JSON, "w") as f: json.dump(_lisa_history, f)
                    except Exception: pass
            log_action(f"Shazam: {sh_artist} — {sh_title}" + (f" (poging {attempt+1})" if attempt else ""),
                       source="plusradio", user="Shazam")
            _tunein_push(sh_title, sh_artist, album or "")   # TuneIn: verrijkte titel + artiest
            _icecast_push_title(getinfo_title)               # Icecast StreamTitle → "Artiest - Titel"
            _write_nowplaying_json()                         # stream-JSON aanvullen met artiest/cover
            return
    finally:
        with _lisa_reco_lock:
            _lisa_reco_inflight.discard(key)

def _maybe_enrich(getinfo_title: str):
    """Start (eenmalig per nummer) een achtergrond-herkenning."""
    if not settings.get("shazam_enabled", True):
        return
    if not getinfo_title or _title_is_commercial(getinfo_title):
        return
    key = _norm_title(getinfo_title)
    if len(key) < 4:
        return
    with _lisa_enrich_lock:
        if _lisa_enrich.get("key") == key:
            return                                   # al verrijkt
    with _lisa_reco_lock:
        if key in _lisa_reco_inflight:
            return
        _lisa_reco_inflight.add(key)
    threading.Thread(target=_lisa_enrich_worker, args=(getinfo_title,), daemon=True).start()

def _lisa_enrich_for(getinfo_title: str) -> dict:
    """Verrijking voor de HUIDIGE titel (alleen als de key nog matcht)."""
    key = _norm_title(getinfo_title)
    if not key:
        return {}
    with _lisa_enrich_lock:
        if _lisa_enrich.get("key") == key:
            return dict(_lisa_enrich)
    return {}

NOWPLAYING_FILE_DEFAULT = "/usr/share/icecast2/web/nowplaying.json"
def _nowplaying_dict():
    """Now-playing + geschiedenis als dict (gedeeld door /api/nowplaying én het
    stream-JSON-bestand). Bevat de albumcover, die niet via Icecast-metadata kan."""
    title   = lisa_current_title()
    e       = _lisa_enrich_for(title)
    is_comm = _title_is_commercial(title)
    hist = []
    for h in _lisa_history_list()[:12]:
        if _title_is_commercial(h.get("title", "")):
            continue
        hist.append({
            "title":     h.get("full_title") or h.get("title", ""),
            "artist":    h.get("artist", ""),
            "cover":     h.get("cover", ""),
            "played_at": h.get("played_at", 0),
        })
    return {
        "title":      ("" if is_comm else (e.get("title") or title)),
        "raw_title":  title,
        "artist":     ("" if is_comm else e.get("artist", "")),
        "album":      ("" if is_comm else e.get("album", "")),
        "cover":      ("" if is_comm else e.get("cover", "")),
        "channel":    lisa_current_channel(),
        "commercial": is_comm,
        "station":    "PLUS Radio",
        "history":    hist,
        "updated":    int(time.time()),
    }

def _write_nowplaying_json():
    """Schrijf now-playing naar de Icecast-webroot → publiek op
    stream.example.nl/nowplaying.json (met cover, die niet via de
    Icecast-streammetadata kan). Overschrijft een bestaand (radio-eigen) bestand."""
    path = settings.get("nowplaying_file") or NOWPLAYING_FILE_DEFAULT
    if not path:
        return
    try:
        with open(path, "w") as f:
            f.write(json.dumps(_nowplaying_dict(), ensure_ascii=False))
    except Exception:
        pass

_lisa_empty_count  = 0        # opeenvolgende lege titel-reads (Lisa stil/uit?)
_lisa_last_restart = 0.0      # laatste keer 'pw 1' gestuurd (cooldown)

def _lisa_tick():
    """Ververs de titel en leg een nieuw nummer vast (geschiedenis + log + Icecast)."""
    global _lisa_empty_count, _lisa_last_restart
    if not settings.get("lisa_enabled", True):
        return
    title = lisa_now_playing(force=True)   # altijd verse uitlezing (snelle detectie)
    # Lisa "uit"/stil geeft een lege titel OF alleen de telnet-prompt ">" terug
    # (bijv. de CD-speler valt 's avonds na het laatste nummer uit). Na ~3s
    # aanhoudend stil 'pw 1' sturen om 'm weer te starten, zodat de RCA + online
    # stream niet stilvallen. Cooldown 60s; losse glitches triggeren niets.
    if (not title) or title.strip() in (">", ""):
        _lisa_empty_count += 1
        if (settings.get("lisa_keepalive", True) and _lisa_empty_count >= 6
                and time.time() - _lisa_last_restart > 60):
            _lisa_last_restart = time.time()
            try:
                _lisa_conn.send("pw 1")        # aanzetten
                time.sleep(0.5)
                _lisa_conn.send("pp 1")        # Plus Main selecteren → begint te spelen
            except Exception: pass
            log_action("PLUS Radio (Lisa) stond stil → 'pw 1' + 'pp 1' gestuurd om te herstarten",
                       source="plusradio", user="Systeem")
        return
    _lisa_empty_count = 0
    # Reclame-duck ALS EERSTE: het zachter zetten van de stream (zmq → ffmpeg) is
    # tijdkritisch en mag niet wachten op de Icecast-titelpush (timeout 4s) of de
    # geschiedenis/logging hieronder — anders duckt de stream pas seconden later.
    # _handle_commercial is idempotent (guard op _commercial_active), dus elke tick
    # aanroepen is veilig en self-healing als een eerder commando verloren ging.
    _handle_commercial(title)
    # Icecast-titel pushen zodra hij afwijkt van wat we laatst pushten — óók
    # meteen na een (her)start, niet pas bij de volgende nummerwissel.
    global _lisa_last_pushed
    if title != _lisa_last_pushed:
        _icecast_push_title(title)
        _lisa_last_pushed = title
    with _lisa_hist_lock:
        if _lisa_history and _lisa_history[0].get("title") == title:
            return                        # zelfde nummer speelt nog
        _lisa_history.insert(0, {"title": title, "played_at": int(time.time())})
        del _lisa_history[LISA_HISTORY_MAX:]
        try:
            with open(LISA_HISTORY_JSON, "w") as f: json.dump(_lisa_history, f)
        except Exception: pass
    log_action(f"PLUS Radio speelt: {title}", source="plusradio", user="PLUS Radio")
    _maybe_enrich(title)                  # Shazam: volledige titel/artiest/cover (async)
    if not _title_is_commercial(title):
        _tunein_push(title)               # TuneIn: snelle titel (verrijking volgt bij match)
    _write_nowplaying_json()              # stream.example.nl/nowplaying.json bijwerken

def _lisa_history_list():
    with _lisa_hist_lock:
        return list(_lisa_history)

def _lisa_loop():
    i = 0
    try:
        _t0 = lisa_now_playing(force=True); _write_nowplaying_json()   # bij opstart meteen vullen
        if _t0: _maybe_enrich(_t0)      # huidig nummer meteen (her)kennen na een herstart
    except Exception: pass
    while True:
        try:
            # Demo/laptop of geen streamer geconfigureerd → niet pollen (geen
            # verbindingsfouten op hardware zonder Streamit Lisa).
            if settings.get("demo_mode") or not settings.get("lisa_enabled", True) \
               or not settings.get("lisa_host"):
                time.sleep(3); continue
            _lisa_tick()                      # titel + commercial: elke 0,5s
            if i % 10 == 0:
                _lisa_refresh_meta()          # kanaal minder vaak (~elke 5s)
        except Exception: pass
        i += 1
        # 0,5s i.p.v. 1s: onze detectie draagt zo max ~0,5s bij (was ~1s). De
        # Lisa levert per tick één 'getinfo title' — één commando, veilig. De
        # ~4s restlag zit ín de Lisa (titel-veld loopt achter op het geluid).
        time.sleep(0.5)

# ── Spotify Jam (socialsession) meedoen-link ─────────────────────
# Wie op de speaker cast heeft (via Connect) automatisch een sociale sessie. We
# vragen met go-librespot's eigen access-token (POST /token) de huidige sessie op
# bij Spotify's social-connect API en bouwen daaruit een deel-/join-link. Anderen
# openen die op hun telefoon → Spotify opent de Jam en ze doen mee. Geen API-
# credentials nodig; het token komt van de castende account zelf.
_JAM_REMOTE_CMD = (
    'T=$(curl -s -m3 -X POST http://127.0.0.1:3678/token | grep -o \'"token":"[^"]*"\' | cut -d\'"\' -f4); '
    'if [ -n "$T" ]; then '
    'curl -s -m4 -H "Authorization: Bearer $T" '
    'https://spclient.wg.spotify.com/social-connect/v2/sessions/current; fi'
)
_sp_analysis_cache = {}                 # {track_id: {ts, data}} voor de visualizer
_sp_analysis_lock  = threading.Lock()
_jam_cache = {"ts": 0.0, "url": ""}
_jam_lock  = threading.Lock()
JAM_TTL    = 15.0

_glr_tok_cache = {"tok": "", "exp": 0.0}
_glr_tok_lock  = threading.Lock()

def _glr_token() -> str:
    """Access-token van de castende/huis-account bij de lokale go-librespot.
    LANG gecachet: elke POST /token laat go-librespot opnieuw inloggen (Login5),
    en de Jam-check deed dat elke 15s → constante her-auth die de Connect-sessie
    verstoorde. Nu ~45 min hergebruikt."""
    now = time.time()
    with _glr_tok_lock:
        if _glr_tok_cache["tok"] and now < _glr_tok_cache["exp"]:
            return _glr_tok_cache["tok"]
    try:
        req = urllib.request.Request(f"http://{VM_GLR_API}/token", method="POST")
        d = json.loads(urllib.request.urlopen(req, timeout=3).read().decode() or "{}")
        tok = (d.get("token") or "").strip()
        exp = now + int(d.get("expires_in") or 3300) - 120
    except Exception:
        return ""
    if tok:
        with _glr_tok_lock:
            _glr_tok_cache.update(tok=tok, exp=exp)
    return tok

def pi_jam_join_url() -> str:
    """Join-link van de huidige Spotify-Jam van wie er cast, of '' als er geen
    sessie is. Alleen in go-librespot-modus; 15s gecachet. V7: token + social-
    connect-lookup draaien lokaal; anders via SSH naar de Pi (rollback)."""
    if not spotify_control_on():
        return ""
    if not (PI_LOCAL_GLR or PI_ENABLED):
        return ""
    now = time.time()
    with _jam_lock:
        if now - _jam_cache["ts"] < JAM_TTL:
            return _jam_cache["url"]
    url = ""
    try:
        if PI_LOCAL_GLR:
            tok = _glr_token()
            out = ""
            if tok:
                req = urllib.request.Request(
                    "https://spclient.wg.spotify.com/social-connect/v2/sessions/current",
                    headers={"Authorization": "Bearer " + tok})
                out = urllib.request.urlopen(req, timeout=4).read().decode("utf-8", "replace")
        else:
            rc, out = _pi_ssh(_JAM_REMOTE_CMD)
        m = re.search(r'"join_session_token"\s*:\s*"([^"]+)"', out or "")
        if m:
            url = f"https://open.spotify.com/socialsession/{m.group(1)}"
    except Exception:
        url = ""
    with _jam_lock:
        _jam_cache.update(ts=time.time(), url=url)
    return url

# ── Explicit-nummer blokker ──────────────────────────────────────
# Speelt iemand een als 'explicit' gemarkeerd nummer op Spotify, dan mag dat
# niet in de winkel klinken. Met raspotify kunnen we niet skippen, dus dempen
# we Spotify (ALSA-mute op de Pi — los van het volume, zodat de omroep-duck de
# demping niet opheft), spelen een hoorbaar alarm op de winkelspeakers, en
# blokkeren het terugzetten van het volume tot iemand het nummer overslaat.
EXPLICIT_POLL_SECS   = 3
EXPLICIT_ALARM_EVERY = 5     # alarm herhalen om de 5 seconden ...
EXPLICIT_ALARM_MAX   = 30    # ... gedurende maximaal 30 seconden per nummer
_explicit_active     = False
_explicit_track      = ""
_explicit_name       = ""

def explicit_blocked() -> bool:
    return _explicit_active

def _play_explicit_alert(gain: float = 1.5):
    # Niet over een lopende omroep/TTS heen spelen (pst is dan bezet).
    if os.path.exists(EXPLICIT_WAV) and _active_pst_proc is None:
        threading.Thread(target=_play_file_to_pst, args=(EXPLICIT_WAV, gain), daemon=True).start()

def _explicit_alarm_cycle(tid: str):
    """Speelt het alarm elke EXPLICIT_ALARM_EVERY sec, maximaal EXPLICIT_ALARM_MAX
    sec — zolang hetzelfde explicit-nummer nog speelt en niet is overgeslagen."""
    start = time.time()
    while (_explicit_active and _explicit_track == tid
           and time.time() - start < EXPLICIT_ALARM_MAX):
        _play_explicit_alert()
        time.sleep(EXPLICIT_ALARM_EVERY)

def _start_alarm_cycle(tid: str):
    threading.Thread(target=_explicit_alarm_cycle, args=(tid,), daemon=True).start()

# ── Explicit-status opzoeken (go-librespot levert geen E-vlag) ──
# go-librespot's now-playing bevat geen explicit-veld (raspotify's hook wél, via
# IS_EXPLICIT). We halen het per track op bij de PUBLIEKE Spotify-embed — geen
# API-credentials nodig — en cachen het per track-id. Faalt de lookup, dan geldt
# "onbekend" → NIET blokkeren (fail-open, net als vóór deze fix) en proberen we
# het de volgende ronde opnieuw.
_EXPLICIT_CACHE      = {}
_EXPLICIT_CACHE_LOCK = threading.Lock()

def _spotify_track_id(np) -> str:
    """Bare track-id uit de now-playing (track_id, of uit de spotify:track:-uri)."""
    if not np:
        return ""
    tid = (np.get("track_id") or "").strip()
    if tid:
        return tid
    uri = (np.get("uri") or "").strip()
    if uri.startswith("spotify:track:"):
        return uri.rsplit(":", 1)[-1]
    return ""

def _track_is_explicit(track_id: str):
    """True/False, of None bij onbekend/fout. Gecachet per track_id."""
    if not track_id:
        return None
    with _EXPLICIT_CACHE_LOCK:
        if track_id in _EXPLICIT_CACHE:
            return _EXPLICIT_CACHE[track_id]
    val = None
    try:
        req = urllib.request.Request(
            f"https://open.spotify.com/embed/track/{track_id}",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            html = r.read(300000).decode("utf-8", "replace")
        m = re.search(r'"is_?explicit"\s*:\s*(true|false)', html, re.I)
        if m:
            val = (m.group(1).lower() == "true")
    except Exception as e:
        log_action(f"Explicit-opzoeken faalde ({track_id}): {e}", source="system")
        return None
    if val is not None:
        with _EXPLICIT_CACHE_LOCK:
            _EXPLICIT_CACHE[track_id] = val
    return val

# ── Wie cast er? (Spotify-weergavenaam bij de go-librespot-username) ──
# go-librespot's /status.username is de account-id van wie op de speler cast.
# Die resolven we naar een leesbare naam via de PUBLIEKE profielpagina (og:title),
# gecachet per id — geen API-credentials nodig.
_CASTER_CACHE      = {}
_CASTER_CACHE_LOCK = threading.Lock()

def _resolve_caster_name(uid: str) -> str:
    if not uid:
        return ""
    with _CASTER_CACHE_LOCK:
        if uid in _CASTER_CACHE:
            return _CASTER_CACHE[uid]
    name = ""
    try:
        req = urllib.request.Request(
            f"https://open.spotify.com/user/{uid}",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            html = r.read(200000).decode("utf-8", "replace")
        m = re.search(r'property="og:title"\s+content="([^"]*)"', html)
        if m:
            name = m.group(1).strip()
    except Exception:
        name = ""
    if name:
        with _CASTER_CACHE_LOCK:
            _CASTER_CACHE[uid] = name
    return name

def _handle_explicit_track(tid: str, name: str):
    """Reageer op een NIEUW gedetecteerd explicit-nummer: het waarschuwings-
    geluid één keer op volume 1.5 laten horen en — in go-librespot-modus —
    automatisch doorskippen naar het volgende nummer. Kan er niet worden
    geskipt (raspotify-modus), dan het herhalende alarm tot iemand handmatig
    overslaat."""
    _play_explicit_alert(2.0)                        # geluid, één keer, +100%
    if spotify_control_on():
        _glr_post("/player/next")                    # automatisch volgend nummer
        _mark_track_skipped(tid, "explicit")         # in de geschiedenis markeren
        log_action(f"Explicit \"{name}\" — geluid gespeeld, automatisch overgeslagen",
                   source="system")
    else:
        _start_alarm_cycle(tid)                      # geen auto-skip mogelijk
        log_action(f"Explicit geblokkeerd: \"{name}\" — Spotify gedempt (geen auto-skip)",
                   source="system")

def _explicit_guard_tick():
    """Eén ronde van de explicit-bewaker (los getest).

    Nieuw explicit-nummer → Spotify meteen dempen, geluid één keer op 1.5 en
    automatisch doorskippen (zie _handle_explicit_track). Blijft gedempt tot er
    weer een niet-explicit nummer speelt."""
    global _explicit_active, _explicit_track, _explicit_name
    _, np = pi_snapshot()
    playing = bool(np and np.get("state") == "playing")
    tid = _spotify_track_id(np) if playing else ""
    is_exp = False
    if playing:
        if np.get("is_explicit"):          # raspotify-hook levert dit direct
            is_exp = True
        elif tid:                          # go-librespot: opzoeken (gecachet)
            is_exp = bool(_track_is_explicit(tid))
    if is_exp:
        # Nieuw nummer = eerste detectie, óf een ánder explicit-nummer dan de
        # vorige (bijv. het volgende bleek óók explicit → opnieuw skippen).
        new_track = (not _explicit_active) or (tid and tid != _explicit_track)
        _explicit_active = True
        _explicit_track  = tid
        _explicit_name   = np.get("name", "")
        # her-assert de mute elke ronde (V7: SPOT-softvol; anders Pi-ALSA)
        if PI_LOCAL_GLR: _spot_hard_mute()
        else:            _pi_ssh(f"amixer sset {PI_MIXER} mute")
        if new_track:
            _handle_explicit_track(tid, _explicit_name)
    elif _explicit_active and playing:
        # Weer een gewoon (niet-explicit) nummer aan het spelen → vrijgeven.
        _explicit_active = False; _explicit_track = ""; _explicit_name = ""
        if PI_LOCAL_GLR: _spot_hard_unmute()
        else:            _pi_ssh(f"amixer sset {PI_MIXER} unmute")
        log_action("Explicit voorbij — Spotify weer hoorbaar", source="system")

def explicit_guard_loop():
    while True:
        time.sleep(EXPLICIT_POLL_SECS)
        if not (PI_ENABLED or PI_LOCAL_GLR):
            continue
        try:
            _explicit_guard_tick()
        except Exception as e:
            log_action(f"Explicit-guard fout: {e}", source="system")
        try:
            _rca_spotify_auto_tick()
        except Exception as e:
            log_action(f"RCA-automatiek fout: {e}", source="system")
        try:
            _sp_queue_tick()
        except Exception as e:
            log_action(f"Spotify-wachtrij fout: {e}", source="system")

# ──────────────────────────────────────────────
# Login rate limiting
# ──────────────────────────────────────────────
_login_attempts: dict = {}
_login_lock = threading.Lock()
MAX_ATTEMPTS = 10
LOCKOUT_SECS = 300

def _check_rate_limit(ip: str) -> bool:
    now = time.time()
    with _login_lock:
        attempts = [t for t in _login_attempts.get(ip, []) if now - t < LOCKOUT_SECS]
        _login_attempts[ip] = attempts
        return len(attempts) < MAX_ATTEMPTS

def _record_failed_login(ip: str):
    now = time.time()
    with _login_lock:
        _login_attempts.setdefault(ip, []).append(now)

def _clear_rate_limit(ip: str):
    with _login_lock:
        _login_attempts.pop(ip, None)

# ──────────────────────────────────────────────
# Gebruikersbeheer
# ──────────────────────────────────────────────
DEFAULT_RIGHTS = {
    "admin":    {"role": "admin",    "can_volume": True,  "can_tts": True,  "can_presets": "all"},
    "operator": {"role": "operator", "can_volume": True,  "can_tts": True,  "can_presets": "all"},
    "user":     {"role": "user",     "can_volume": False, "can_tts": False, "can_presets": []},
    "custom":   {"role": "custom",   "can_volume": False, "can_tts": False, "can_presets": []},
}

def _rights_from_groups(groups: list) -> dict:
    ga = oidc_cfg.get("group_admin", "radio-admin")
    go = oidc_cfg.get("group_operator", "radio-operator")
    if ga and ga in groups:
        return dict(DEFAULT_RIGHTS["admin"])
    if go and go in groups:
        return dict(DEFAULT_RIGHTS["operator"])
    return dict(DEFAULT_RIGHTS["user"])

def _create_local_user(username, password, display_name, role,
                        can_volume, can_tts, can_presets) -> bool:
    with _users_lock:
        if username in users:
            return False
        users[username] = {
            "password_hash": generate_password_hash(password),
            "display_name": display_name or username,
            "source": "local",
            "role": role,
            "can_volume": can_volume,
            "can_tts": can_tts,
            "can_presets": can_presets,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_login": None,
        }
        _save_json(USERS_JSON, users)
    return True

def _radio_groups(groups):
    """Alleen groepen die met 'radio-' beginnen zijn relevant voor dit
    systeem; alle andere (Wordpress/Nextcloud/HA/…) worden genegeerd."""
    return [g for g in (groups or []) if str(g).lower().startswith("radio-")]

def _upsert_sso_user(username, display_name, groups):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    groups = _radio_groups(groups)
    rights = _rights_from_groups(groups)
    with _users_lock:
        existing = users.get(username, {})
        is_new = not existing
        update_rights = is_new or existing.get("role") != "custom"
        users[username] = {
            "password_hash": existing.get("password_hash", ""),
            "display_name": display_name or username,
            "source": "sso",
            "groups": groups,
            "role":         rights["role"]         if update_rights else existing.get("role"),
            "can_volume":   rights["can_volume"]   if update_rights else existing.get("can_volume"),
            "can_tts":      rights["can_tts"]      if update_rights else existing.get("can_tts"),
            "can_presets":  rights["can_presets"]  if update_rights else existing.get("can_presets"),
            "created": existing.get("created", now),
            "last_login": now,
        }
        _save_json(USERS_JSON, users)
    if is_new:
        log_action(f"Nieuwe SSO-gebruiker: {username} groepen={groups}", source="sso")

def _verify_local_login(username, password) -> bool:
    u = users.get(username)
    if not u or u.get("source") not in ("local", ""):
        return False
    return check_password_hash(u.get("password_hash", ""), password)

def ensure_default_admin():
    for u in users.values():
        if u.get("role") == "admin" and u.get("source") == "local":
            return
    _create_local_user(
        username="admin", password="admin", display_name="Beheerder",
        role="admin", can_volume=True, can_tts=True, can_presets="all",
    )
    log_action("Standaard admin aangemaakt (gebruiker: admin, wachtwoord: admin — WIJZIG DIT!)", source="system")

# ──────────────────────────────────────────────
# Auth helpers
# ──────────────────────────────────────────────
def current_user() -> dict:
    un = session.get("username")
    return users.get(un, {}) if un else {}

def current_username() -> str:
    return session.get("username", "")

def is_admin() -> bool:
    return current_user().get("role") == "admin"

def is_logged_in() -> bool:
    return bool(session.get("username"))

def login_required():
    if not is_logged_in():
        return redirect(url_for("login_page"))
    return None

def admin_required():
    if not is_admin():
        abort(403)

def can_do(permission: str) -> bool:
    if not is_logged_in(): return False
    u = current_user()
    if u.get("role") == "admin": return True
    return bool(u.get(permission, False))

def can_preset(preset_id: int) -> bool:
    if not is_logged_in(): return False
    u = current_user()
    if u.get("role") in ("admin", "operator"): return True
    allowed = u.get("can_presets", [])
    if allowed == "all": return True
    return preset_id in (allowed or [])

def can_generate_tts() -> bool:
    if not is_logged_in(): return False
    u = current_user()
    if u.get("role") in ("admin", "operator"): return True
    return bool(u.get("can_tts_generate", False))

# ──────────────────────────────────────────────
# Fijnmazige volume-/Spotify-rechten (per subtab: PLUS Radio "omroep" + Spotify)
# Per domein losse capability-vlaggen + een volume-bereik (vmin/vmax 0-100).
#   omroep : view mute volume rca stop
#   spotify: view mute volume transport restart
# Admin/operator = volledige rechten. Oude vlag can_volume=True → volledig
# (backward-compat migratie); can_volume ontbreekt/False → geen rechten.
# ──────────────────────────────────────────────
VOL_DOMAINS = ("omroep", "spotify")
_VOL_CAPS = {
    "omroep":  ("view", "mute", "volume", "rca", "stop", "nowplaying", "channel", "commercial"),
    "spotify": ("view", "mute", "volume", "transport", "restart", "history", "jam"),
}
# Capabilities die standaard AAN staan (opt-out i.p.v. opt-in): zichtbaar tenzij
# de beheerder ze expliciet uitzet. Gelden alleen als het domein 'view' aan heeft.
_VOL_CAPS_DEFAULT_ON = {("spotify", "history"), ("spotify", "jam"),
                        ("omroep", "nowplaying"), ("omroep", "channel"),
                        ("omroep", "commercial")}

def _blank_vol_rights(val: bool = False) -> dict:
    out = {}
    for dom in VOL_DOMAINS:
        d = {cap: bool(val) for cap in _VOL_CAPS[dom]}
        d["vmin"], d["vmax"] = 0, 100
        out[dom] = d
    return out

def _normalize_vol_rights(vr: dict) -> dict:
    out = _blank_vol_rights(False)
    for dom in VOL_DOMAINS:
        src = (vr.get(dom) or {}) if isinstance(vr, dict) else {}
        for cap in _VOL_CAPS[dom]:
            default_on = (dom, cap) in _VOL_CAPS_DEFAULT_ON
            out[dom][cap] = bool(src.get(cap, default_on))
        try:    lo = max(0, min(100, int(src.get("vmin", 0))))
        except Exception: lo = 0
        try:    hi = max(0, min(100, int(src.get("vmax", 100))))
        except Exception: hi = 100
        if hi < lo: hi = lo
        out[dom]["vmin"], out[dom]["vmax"] = lo, hi
    return out

def vol_rights_for(u: dict = None) -> dict:
    """Effectieve volume-/Spotify-rechten voor een gebruiker-dict (of de huidige)."""
    u = current_user() if u is None else (u or {})
    if not u: return _blank_vol_rights(False)
    if u.get("role") in ("admin", "operator"): return _full_vol_rights()
    if u.get("role") == "custom":
        vr = u.get("vol_rights")
        if isinstance(vr, dict): return _normalize_vol_rights(vr)
        if u.get("can_volume"):  return _full_vol_rights()   # migratie oude vlag
        # Nog geen vol_rights: lege normalisatie zodat de standaard-AAN caps
        # (queue/jam) alvast aan staan (view blijft uit → nog geen toegang).
        return _normalize_vol_rights({})
    return _blank_vol_rights(False)

def _full_vol_rights() -> dict:
    return _blank_vol_rights(True)

def _vol_cap(domain: str, cap: str, u: dict = None) -> bool:
    return bool(vol_rights_for(u).get(domain, {}).get(cap))

def _require_vol(domain: str, cap: str):
    """Guard voor volume-endpoints: 401 zonder login, 403 zonder recht.
    Geeft de effectieve rechten terug voor evt. bereik-clamping."""
    if not is_logged_in(): abort(401)
    vr = vol_rights_for()
    if not vr.get(domain, {}).get(cap): abort(403)
    return vr

def _clamp_vol(domain: str, v, vr: dict = None) -> int:
    """Klem een volumewaarde binnen het toegestane bereik van het domein."""
    vr = vr or vol_rights_for()
    d = vr.get(domain, {})
    v = max(0, min(100, int(v)))
    return max(d.get("vmin", 0), min(d.get("vmax", 100), v))

def can_save_preset_right() -> bool:
    if not is_logged_in(): return False
    u = current_user()
    if u.get("role") in ("admin", "operator"): return True
    allowed = u.get("can_presets", [])
    return allowed == "all" or bool(allowed)

def client_ip() -> str:
    fwd = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return fwd or request.remote_addr or "unknown"

# ──────────────────────────────────────────────
# Logboek — gebufferd wegschrijven.
# Voorheen werd het volledige logs-JSON (tot 5000 regels) synchroon
# weggeschreven bij ELKE actie, óók midden in het preset-afspeelpad.
# Nu: in-memory appenden en een achtergrondthread schrijft max. elke
# ~2 seconden. Dit scheelt merkbaar in de reactietijd.
# ──────────────────────────────────────────────
_logs_dirty = threading.Event()

def _logs_saver_loop():
    while True:
        _logs_dirty.wait()
        time.sleep(2)  # verzamel meerdere log-regels in één schrijfactie
        _logs_dirty.clear()
        with _logs_lock:
            snapshot = list(logs)
        try:
            _save_json(LOGS_JSON, snapshot)
        except Exception:
            pass

threading.Thread(target=_logs_saver_loop, daemon=True).start()

def _safe_actor_ip() -> str:
    """Echt client-IP, maar alleen als er een request-context is.
    Achtergrondthreads (scheduler, afspeel-thread) hebben die niet."""
    try:
        if has_request_context():
            return client_ip()
    except Exception:
        pass
    return ""

def _safe_actor_user() -> str:
    try:
        if has_request_context():
            return current_username() or ""
    except Exception:
        pass
    return ""

# Nette naam voor bron-systemen die geen ingelogde gebruiker hebben.
_ACTOR_FALLBACK = {
    "3cx":      "3CX",
    "ha":       "Home Assistant",
    "schedule": "Planner",
    "sso":      "SSO",
    "system":   "Systeem",
}

def log_action(text: str, source: str = None, user: str = None, ip: str = None):
    """Registreer een actie in het logboek.

    Belangrijk (fix): 'source' is UITSLUITEND de categorie. Het IP-veld
    werd voorheen met deze categorie-string overschreven (waardoor de
    IP-kolom "preset"/"tts"/… toonde i.p.v. een echt adres) en de
    gebruiker werd nooit vastgelegd. Nu bevat elke regel apart:
      - user : wie de actie deed (ingelogde gebruiker of bron-systeem)
      - ip   : het echte client-IP
      - cat  : de categorie

    Voor acties die in een achtergrondthread draaien (afspelen/TTS) moeten
    'user' en 'ip' door de aanroeper worden meegegeven, omdat daar geen
    request-context beschikbaar is.
    """
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    src = (source or "").lower()
    if   src in ("login","logout"):          cat = src
    elif src == "sso":                       cat = "sso"
    elif src in ("preset","3cx","schedule"): cat = src
    elif src == "tts":                       cat = "tts"
    elif src in ("admin","system"):          cat = src
    elif src == "ha":                        cat = "ha"
    elif src == "rca":                       cat = "rca"
    elif src == "volume":                    cat = "volume"
    elif src == "spotify":                   cat = "spotify"
    elif src == "plusradio":                 cat = "plusradio"
    else:                                    cat = "system"

    if ip   is None: ip   = _safe_actor_ip()
    if user is None: user = _safe_actor_user()
    if not user:     user = _ACTOR_FALLBACK.get(cat, "")

    with _logs_lock:
        logs.append({"time": ts, "action": text,
                     "user": user or "", "ip": ip or "", "cat": cat})
        if len(logs) > 5000:
            del logs[:len(logs) - 5000]
    _logs_dirty.set()

ensure_default_admin()

# ──────────────────────────────────────────────
# HA token auth
# ──────────────────────────────────────────────
HA_TOKEN = (os.environ.get("OMROEP_HA_TOKEN") or "").strip()

def _ha_auth_ok() -> bool:
    if not HA_TOKEN: return True
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer ") and auth.split(None, 1)[1].strip() == HA_TOKEN:
        return True
    return (request.headers.get("X-HA-Token") or "").strip() == HA_TOKEN

def ha_required():
    if not _ha_auth_ok(): abort(401)

# ──────────────────────────────────────────────
# OIDC
# ──────────────────────────────────────────────
def _load_oidc_meta() -> dict:
    global _oidc_meta_cache
    discovery = oidc_cfg.get("discovery_url", "")
    if not discovery: return {}
    with _oidc_meta_lock:
        if (_oidc_meta_cache.get("_url") == discovery
                and _oidc_meta_cache.get("_ts", 0) > time.time() - 3600
                and _oidc_meta_cache.get("authorization_endpoint")):
            return _oidc_meta_cache
        try:
            req  = urllib.request.Request(discovery, headers={
                "User-Agent": "OmroepwebOIDC/6.0",
                "Accept": "application/json",
            })
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read().decode())
            if data.get("authorization_endpoint"):
                data["_url"] = discovery
                data["_ts"]  = time.time()
                _oidc_meta_cache = data
                return _oidc_meta_cache
        except Exception:
            pass
        return _oidc_meta_cache if _oidc_meta_cache.get("authorization_endpoint") else {}

def _oidc_post(url, data) -> dict:
    body = urlencode(data).encode()
    req  = urllib.request.Request(url, data=body,
                                   headers={"Content-Type": "application/x-www-form-urlencoded",
                                            "User-Agent": "OmroepwebOIDC/6.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read().decode())

def _oidc_get(url, token) -> dict:
    req  = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}",
                                                 "User-Agent": "OmroepwebOIDC/6.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read().decode())

# ──────────────────────────────────────────────
# Per-IP paginarechten
# ──────────────────────────────────────────────
def effective_ui_for_ip(ip: str):
    """Effectieve pagina-zichtbaarheid + sloten voor het huidige verzoek.
    Toegangsregels kunnen op een IP-adres én op een gebruiker gericht zijn;
    eerst wordt de IP-regel toegepast, daarna de gebruiker-regel (die wint bij
    overlap). Admins zijn overal van uitgezonderd."""
    eff_pages = {"volume": True, "presets": True, "tts": True}
    eff_locks = {"presets": False, "tts": False}
    if is_admin(): return eff_pages, eff_locks
    def _apply(rule):
        if isinstance(rule, dict):
            p = rule.get("pages") or {}; l = rule.get("locks") or {}
            for k in eff_pages: eff_pages[k] = bool(p.get(k, eff_pages[k]))
            for k in eff_locks: eff_locks[k] = bool(l.get(k, eff_locks[k]))
    _apply((settings.get("ip_rules")   or {}).get(ip))
    _apply((settings.get("user_rules") or {}).get(current_username()))
    return eff_pages, eff_locks

def _user_can_page(key: str) -> bool:
    """Controleer of de huidige gebruiker toegang heeft tot een pagina,
    rekening houdend met zowel IP-regels als gebruikersrechten."""
    u = current_user()
    if not u: return False
    role = u.get("role", "user")
    if role == "admin": return True
    if key == "volume":
        vr = vol_rights_for(u)
        if not (vr["omroep"]["view"] or vr["spotify"]["view"]): return False
    if key == "presets":
        allowed = u.get("can_presets", [])
        if allowed != "all" and not allowed: return False
    if key == "tts"     and not u.get("can_tts", False): return False
    return True

def _first_allowed_endpoint() -> str:
    """FIX redirect-loop: gaf voorheen 'login_page' terug voor ingelogde
    gebruikers zonder enige paginarechten. De loginpagina stuurt ingelogde
    gebruikers echter meteen wéér door naar _first_allowed_endpoint(),
    waardoor een oneindige /login → /login redirect-lus ontstond
    ("Safari kan de pagina niet openen omdat er te vaak is doorverwezen").
    Nu krijgen zulke gebruikers de nette pagina /geen-toegang."""
    if not is_logged_in():
        return "login_page"
    ip = client_ip()
    pages, locks = effective_ui_for_ip(ip)
    for ep, key in [("volume_page","volume"), ("presets_page","presets"), ("tts_page","tts")]:
        if pages.get(key, True) and _user_can_page(key):
            if key == "presets" and locks.get("presets") and not session.get("presets_unlocked"):
                return "locked_page"
            if key == "tts" and locks.get("tts") and not session.get("tts_unlocked"):
                return "locked_tts_page"
            return ep
    return "no_access_page"

# ──────────────────────────────────────────────
# Audio
# ──────────────────────────────────────────────
ALSA_CARD = "0"
MIXER_BG  = "BG"
MIXER_PST = "PST"
MIXER_PCM = "PCM"
MIXER_SPOT = "SPOT"   # softvol voor Spotify (lokale VM go-librespot) → mee-ducken bij omroep

_bg_muted      = False
_bg_lock       = threading.Lock()

# Laatst ingestelde PLUS Radio (BG)-volume onthouden over een service-/VM-herstart.
BG_STATE_JSON = os.path.join(APP_DIR, "bg_state.json")
def _load_bg_volume(default=100):
    try:
        with open(BG_STATE_JSON) as f:
            return max(0, min(100, int(json.load(f).get("bg_volume", default))))
    except Exception:
        return default
def _save_bg_volume(v):
    try:
        with open(BG_STATE_JSON, "w") as f:
            json.dump({"bg_volume": int(max(0, min(100, v)))}, f)
    except Exception:
        pass
_bg_vol_before = _load_bg_volume(100)

DUCK_LEVEL          = 25
DEFAULT_PRESET_GAIN = 100
DEFAULT_TTS_GAIN    = 100

# Icoon-suggesties voor de preset-bewerkpagina (Material Symbols).
PRESET_ICON_SUGGESTIONS = [
    "campaign","mic","volume_up","record_voice_over","speaker","queue_music","music_note","headphones",
    "alarm","schedule","timer","event","today","calendar_month","notifications","notification_important",
    "warning","error","info","help","priority_high","report","new_releases","flag",
    "person","group","people","badge","supervisor_account","engineering","support_agent","manage_accounts",
    "store","local_grocery_store","shopping_cart","shopping_basket","storefront","local_mall","point_of_sale",
    "local_bar","liquor","wine_bar","sports_bar","local_cafe","coffee","bakery_dining","restaurant",
    "recycling","delete","cleaning_services","build","handyman","construction","home_repair_service",
    "directions_car","local_shipping","delivery_dining","two_wheeler","electric_car","agriculture",
    "lock","lock_open","security","verified","shield","key","vpn_key","fingerprint",
    "phone","phone_in_talk","call","contact_phone","headset_mic","support",
    "bolt","power","electrical_services","outlet","settings","tune","device_hub",
    "star","thumb_up","celebration","cake","favorite","emoji_events","workspace_premium",
    "close","check","done","add","remove","search","refresh","sync","autorenew",
    "arrow_forward","arrow_back","arrow_upward","arrow_downward","open_in_new","link",
    "local_pizza","fastfood","lunch_dining","dinner_dining","brunch_dining",
    "thermostat","ac_unit","water_drop","opacity","light_mode","dark_mode",
    "monetization_on","euro","attach_money","payments","receipt","savings","account_balance",
    "inventory","inventory_2","warehouse","shelves","category","label","sell",
    "factory","precision_manufacturing",
]

# ──────────────────────────────────────────────
# Woordfilter — voorkomt dat schuttingtaal via TTS wordt omgeroepen.
# Startlijst (50); admin kan deze in Beheer → Woordfilter aanpassen.
# ──────────────────────────────────────────────
DEFAULT_BLOCKED_WORDS = [
    "kut","kutwijf","kutkop","kutzak","kutzooi","klootzak","klootviool","lul",
    "lulhannes","lullo","lulkoek","eikel","hoer","hoerenjong","hoerenzoon",
    "stoephoer","straathoer","temeier","sloerie","snol","slet","del","kanker",
    "kankerlijer","kankerhoer","kankermongool","kankerzooi","kankerkop","kankerhond",
    "kankeren","tering","teringlijer","teringhoer","teringzooi","tyfus","tyfuslijer",
    "tyfushoer","tyfuszooi","pleuris","pleuriszooi","godverdomme","verdomme","gvd",
    "godskolere","klerelijer","klerezooi","klerezut","kolere","sodemieter","mieter",
    "flikker","mietje","debiel","imbeciel","mongool","mongolen","spast","spasticus",
    "achterlijk","idioot","randdebiel","trut","kreng","rotzak","rotkop","schoft",
    "hufter","smeerlap","viezerik","gluiperd","etterbak","etter","sufferd","mafkees",
    "uitschot","tuig","schorem","schijt","schijtlijer","neuken","neuk","optyfen",
    "shit","fuck","fucking","fucker","motherfucker","bitch","asshole","bastard","dickhead",
]

def _blocked_words_list():
    return settings.get("blocked_words") or DEFAULT_BLOCKED_WORDS

# ── Woordfilter-normalisatie: vangt obfuscatie/typfouten die tóch als het
# scheldwoord klinken (kl00tzak, kloootzak, kànker, k.u.t → kut). ──
_LEET = {"0":"o","1":"i","3":"e","4":"a","5":"s","6":"g","7":"t","8":"b","9":"g",
         "@":"a","$":"s","€":"e","!":"i","|":"l","(":"c"}

def _normalize_word(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")   # accenten weg
    t = "".join(_LEET.get(c, c) for c in t)                        # leetspeak → letters
    t = re.sub(r"[^a-z]", "", t)                                    # alleen letters
    t = re.sub(r"(.)\1+", r"\1", t)                                 # herhalingen inklappen
    return t

def _lev1(a: str, b: str) -> bool:
    """True als de bewerkingsafstand hooguit 1 is (1 typfout)."""
    if a == b: return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1: return False
    if la > lb: a, b, la, lb = b, a, lb, la      # a is de kortste
    i = j = diffs = 0
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1; j += 1
        else:
            diffs += 1
            if diffs > 1: return False
            if la == lb: i += 1; j += 1           # vervanging
            else: j += 1                          # invoeging in de langere
    return True

def _blocked_hit(text: str):
    """Eerste geblokkeerde woord in de tekst, of None. Werkt op hele woorden
    en herkent obfuscatie (leetspeak, herhaalde letters, accenten) en lichte
    typfouten bij langere woorden — maar houdt onschuldige woorden vrij."""
    if not text: return None
    norm_blocked = []
    for w in _blocked_words_list():
        nb = _normalize_word(w)
        if nb: norm_blocked.append((w, nb))
    for tok in re.findall(r"[0-9A-Za-zÀ-ÿ]+", text):
        nt = _normalize_word(tok)
        if not nt: continue
        for orig, nb in norm_blocked:
            if nt == nb: return orig
            if len(nb) >= 5 and nb in nt: return orig            # woord zit erin (compound)
            if len(nb) >= 6 and len(nt) >= 6 and _lev1(nt, nb):  # 1 typfout (lang woord)
                return orig
    return None

def _gain_to_alsa(gain_pct: int) -> int:
    return round(max(0, min(200, int(gain_pct))) / 200 * 255)

EDGE_TTS_BIN = "/usr/local/bin/edge-tts"
PIPER_BIN    = "/usr/local/bin/piper-tts"

def _amixer_run(args):
    try:
        return subprocess.run(["amixer", "-c", ALSA_CARD] + args,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=4)
    except Exception as e:
        return subprocess.CompletedProcess(args, 1, "", str(e))

def set_mixer(mixer, pct):    _amixer_run(["sset", mixer, f"{max(0,min(100,int(pct)))}%"])
def set_mixer_raw(mixer, v):  _amixer_run(["sset", mixer, str(max(0,min(255,int(v))))])
def get_mixer(mixer):
    p = _amixer_run(["sget", mixer])
    m = re.search(r"\[(\d{1,3})%\]", p.stdout or "")
    return (int(m.group(1)) if m else 0), ("Muted" if "off" in (p.stdout or "").lower() else "Unmuted")

def get_bg_volume_pct(): return get_mixer(MIXER_BG)[0]
def set_bg_volume(pct):  set_mixer(MIXER_BG, pct)
def set_pst_gain(g):     set_mixer_raw(MIXER_PST, _gain_to_alsa(g))

def bg_mute():
    global _bg_muted, _bg_vol_before
    with _bg_lock:
        if _bg_muted: return
        _bg_vol_before = get_bg_volume_pct(); set_bg_volume(0); _bg_muted = True
    _save_bg_volume(_bg_vol_before)

def bg_unmute():
    global _bg_muted, _bg_vol_before
    with _bg_lock:
        if not _bg_muted: return
        set_bg_volume(_bg_vol_before); _bg_muted = False

def bg_mute_toggle():
    if _bg_muted: bg_unmute(); return False
    bg_mute(); return True

def _apply_bg_volume(v):
    """Zet het PLUS Radio (BG)-volume, heft mute op en onthoudt de stand
    persistent (voor herstel na een herstart)."""
    global _bg_vol_before, _bg_muted
    with _bg_lock:
        _bg_vol_before = max(0, min(100, int(v)))
        _bg_muted = False
        set_bg_volume(_bg_vol_before)
    _save_bg_volume(_bg_vol_before)

# ── Automatiek: RCA (PLUS Radio) wijkt voor Spotify ──
RCA_AUTO_IDLE_SECS = 10    # zolang moet Spotify stil zijn voordat RCA terugkomt
RCA_AUTO_MAX_VOL   = 65    # bovengrens waarop RCA weer aangaat na Spotify
_RCA_AUTO = {"last_play": 0.0, "auto_off": False, "pref_vol": None}

def _rca_spotify_auto_tick():
    """Eén ronde van de Spotify→RCA-automatiek (los te testen).
    Spotify speelt → RCA uit (en de huidige stand onthouden). Spotify >30s
    niet gespeeld → RCA weer aan op de vorige stand, maar maximaal 65%.
    Grijpt alleen in op wat het zelf heeft uitgezet (respecteert handmatig uit)."""
    if not settings.get("rca_spotify_auto", True):
        return
    if _commercial_active and settings.get("commercial_duck_spotify", True):
        return                    # tijdens een reclame heeft die voorrang (RCA aan, Spotify uit)
    if _comm_playing:
        return                    # klaargezette commercial speelt (Spotify gepauzeerd) → RCA met rust
    _, np = pi_snapshot()
    # Speelt de lokale VM go-librespot (SPOT) óf de Pi? Beide tellen als "Spotify speelt".
    playing = _vm_spotify_playing() or bool(np and np.get("state") == "playing")
    now = time.time()
    if playing:
        _RCA_AUTO["last_play"] = now
        if rca_running():
            _RCA_AUTO["pref_vol"] = _bg_vol_before      # voorkeurstand onthouden
            rca_stop()
            _RCA_AUTO["auto_off"] = True
            log_action("Spotify speelt → RCA automatisch uit", source="rca")
    elif _RCA_AUTO["auto_off"] and (now - _RCA_AUTO["last_play"] > RCA_AUTO_IDLE_SECS):
        if not rca_running():
            pref = _RCA_AUTO.get("pref_vol")
            pref = _bg_vol_before if pref is None else int(pref)
            target = min(max(0, pref), RCA_AUTO_MAX_VOL)
            rca_start()
            _apply_bg_volume(target)
            log_action(f"Spotify >{RCA_AUTO_IDLE_SECS}s stil → RCA automatisch aan op {target}%", source="rca")
        _RCA_AUTO["auto_off"] = False

duck_lock        = threading.Lock()
_active_pst_proc = None
_active_pst_lock = threading.Lock()
_stop_requested  = False

def _omroep_bg_level() -> int:
    """Achtergrondniveau (0-100) tijdens een omroep — voor BEIDE bronnen:
    de lokale RCA PlusRadio (BG-mixer) én Spotify (Pi). 0 = volledig stil.
    Instelbaar via de slider in Beheer (settings.pi_duck_level)."""
    return max(0, min(100, int(settings.get("pi_duck_level", PI_DUCK_DEFAULT))))

_spot_vol_before = 80   # SPOT-stand (cast-volume) om na een omroep te herstellen

def _spot_duck():
    """Spotify (lokale VM go-librespot → SPOT softvol) op omroep-niveau zetten,
    zodat het tijdens preset/TTS/reclame óók gedempt wordt. Onthoudt de vorige
    (cast)stand voor herstel."""
    global _spot_vol_before
    try:
        cur = get_mixer(MIXER_SPOT)[0]
        lvl = _omroep_bg_level()
        if cur > lvl:
            _spot_vol_before = cur
        set_mixer(MIXER_SPOT, lvl)
    except Exception:
        pass

def _spot_unduck():
    try:
        set_mixer(MIXER_SPOT, _spot_vol_before)
    except Exception:
        pass

def _spot_hard_mute():
    """Volledig dempen via de SPOT-mute-switch (los van het volume, zodat een
    latere unduck de demping niet opheft) — het VM-equivalent van de vroegere
    Pi-ALSA-mute voor explicit-nummers."""
    try: _amixer_run(["sset", MIXER_SPOT, "mute"])
    except Exception: pass

def _spot_hard_unmute():
    try: _amixer_run(["sset", MIXER_SPOT, "unmute"])
    except Exception: pass

_DUCK_FADE_SECS = 0.45   # in-/uitfade (BG + SPOT) rond preset/TTS-omroepen

def _fade_ducking(bg_from, bg_to, spot_from, spot_to, secs=_DUCK_FADE_SECS,
                  do_bg=True, do_spot=True):
    """BG (PLUS Radio) én SPOT (Spotify) tegelijk geleidelijk faden, zodat een
    preset/TTS-omroep zacht in- en uitfadet i.p.v. abrupt te schakelen."""
    steps = max(1, int(secs / 0.03))
    for k in range(1, steps + 1):
        f = k / steps
        if do_bg:
            try: set_bg_volume(int(round(bg_from + (bg_to - bg_from) * f)))
            except Exception: do_bg = False
        if do_spot:
            try: set_mixer(MIXER_SPOT, int(round(spot_from + (spot_to - spot_from) * f)))
            except Exception: do_spot = False
        if not (do_bg or do_spot): break
        time.sleep(secs / steps)

def _duck_local(prev_bg: int):
    """Muziek zacht wegfaden vóór een omroep (preset/TTS)."""
    global _spot_vol_before
    lvl = _omroep_bg_level()
    try: cur_spot = get_mixer(MIXER_SPOT)[0]
    except Exception: cur_spot = _spot_vol_before
    if cur_spot > lvl:
        _spot_vol_before = cur_spot          # caststand onthouden voor herstel
    _fade_ducking(prev_bg, lvl, cur_spot, lvl,
                  do_bg=(not _bg_muted and prev_bg > lvl),
                  do_spot=(cur_spot > lvl))

def _unduck_local(prev_bg: int):
    """Muziek na de omroep weer zacht omhoog faden."""
    lvl = _omroep_bg_level()
    try: bg_now = get_bg_volume_pct()
    except Exception: bg_now = lvl
    try: spot_now = get_mixer(MIXER_SPOT)[0]
    except Exception: spot_now = lvl
    _fade_ducking(bg_now, prev_bg, spot_now, _spot_vol_before,
                  do_bg=(not _bg_muted),
                  do_spot=(_spot_vol_before > spot_now))

def _fade_bg(start, end, step=8, delay=0.02):
    s = step if end > start else -abs(step)
    for v in range(start, end, s):
        set_bg_volume(v); time.sleep(delay)
    set_bg_volume(end)

def _play_file_to_pst(fp, gain=1.0):
    global _active_pst_proc
    cmd = ["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-i", fp]
    if gain != 1.0:
        cmd += ["-filter:a", f"volume={gain}"]   # lineaire versterking (1.2 = +20%)
    cmd += ["-ar","48000","-ac","1","-f","alsa","pst"]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with _active_pst_lock: _active_pst_proc = proc
    proc.wait()
    with _active_pst_lock: _active_pst_proc = None

def _play_preroll():
    if os.path.exists(INTRO_WAV):
        _play_file_to_pst(INTRO_WAV)

def _play_outro():
    if os.path.exists(OUTRO_WAV):
        _play_file_to_pst(OUTRO_WAV)

def play_preset_async(preset_id: int, log_user: str = "", log_ip: str = ""):
    global _stop_requested
    _stop_requested = False
    with duck_lock:
        t_duck = None
        try:
            path = os.path.join(PRESETS, f"{preset_id}.wav")
            if not os.path.exists(path):
                log_action(f"Preset {preset_id} ontbreekt", source="preset",
                           user=log_user, ip=log_ip); return
            flag_obj    = preset_flags.get(str(preset_id)) or {}
            use_preroll = bool(flag_obj.get("preroll_enabled", True))
            use_outro   = bool(flag_obj.get("outro_enabled", True))
            gain_pct    = max(0, min(200, int(preset_vols.get(str(preset_id), DEFAULT_PRESET_GAIN))))
            prev_bg     = get_bg_volume_pct()
            log_action(f"Preset {preset_id} start (gain={gain_pct}%)", source="preset",
                       user=log_user, ip=log_ip)

            # SNELHEID: de Pi-duck (SSH naar de Pi) loopt nu CONCURRENT met
            # het afspelen. Voorheen wachtte het afspeelpad met t_duck.join()
            # op de SSH-roundtrip vóórdat er ook maar één sample klonk — dat
            # was de resterende klik-naar-geluid vertraging. De lokale duck
            # (amixer, instant) gebeurt nog steeds direct, dus het lokale
            # omroepkanaal wordt meteen goed gemengd. De Pi-duck-join staat
            # nu ná het afspelen (vóór unduck) zodat de race op _pi_vol_before
            # bij zeer korte presets voorkomen blijft.
            t_duck = threading.Thread(target=pi_duck, daemon=True)
            if PI_ENABLED:
                t_duck.start()
            _duck_local(prev_bg)          # lokale RCA PlusRadio: instant stil

            set_pst_gain(gain_pct)
            # Wacht (begrensd) tot Spotify écht stil is vóór de preroll begint,
            # zodat de muziek niet meer dóór de preroll heen loopt. Met een warme
            # SSH-verbinding is dit ~50ms; PI_DUCK_WAIT begrenst het worst-case
            # zodat de preset ook direct start als de Pi even traag is.
            if PI_ENABLED and t_duck is not None:
                t_duck.join(timeout=PI_DUCK_WAIT)
            if use_preroll and not _stop_requested: _play_preroll()
            if not _stop_requested: _play_file_to_pst(path)
            if use_outro and not _stop_requested: _play_outro()

            if PI_ENABLED and t_duck is not None:
                t_duck.join()             # afronden vóór unduck (beschermt _pi_vol_before)
            t_unduck = threading.Thread(target=pi_unduck, daemon=True)
            if PI_ENABLED:
                t_unduck.start()
            _unduck_local(prev_bg)
            if PI_ENABLED:
                t_unduck.join()

            log_action(f"Preset {preset_id} klaar", source="preset",
                       user=log_user, ip=log_ip)
        except Exception as e:
            log_action(f"Preset fout: {e}", source="preset", user=log_user, ip=log_ip)
            if PI_ENABLED:
                if t_duck is not None:
                    try: t_duck.join(timeout=8)
                    except Exception: pass
                threading.Thread(target=pi_unduck, daemon=True).start()
            try: _unduck_local(get_bg_volume_pct())
            except Exception: pass
        finally:
            _stop_requested = False

def _wpm_to_edge_rate(wpm):
    pct = round((wpm - 165) / 165 * 100)
    return f"+{pct}%" if pct >= 0 else f"{pct}%"

# ──────────────────────────────────────────────
# TTS preview cache
# ──────────────────────────────────────────────
_tts_cache: dict = {}
_tts_cache_lock  = threading.Lock()
TTS_CACHE_TTL    = 300

def _tts_cache_cleanup():
    now = time.time()
    with _tts_cache_lock:
        stale = [k for k, v in _tts_cache.items() if now - v["ts"] > TTS_CACHE_TTL]
        for k in stale:
            try: os.remove(_tts_cache[k]["path"])
            except Exception: pass
            del _tts_cache[k]

def _tts_generate_to_wav(text, voice, wpm):
    text = (text or "").strip()
    if not text:
        return None

    fd, tmpwav = tempfile.mkstemp(suffix=".wav", dir=APP_DIR)
    os.close(fd)

    engine  = (settings.get("tts_engine") or "edge").lower()
    success = False

    if engine == "edge":
        if not voice:
            voice = settings.get("tts_edge_voice") or "nl-NL-MaartenNeural"
        tmpmp3 = None
        try:
            fd2, tmpmp3 = tempfile.mkstemp(suffix=".mp3", dir=APP_DIR)
            os.close(fd2)
            r = subprocess.run(
                [EDGE_TTS_BIN, "--voice", voice, "--rate", _wpm_to_edge_rate(wpm),
                 "--text", text, "--write-media", tmpmp3],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            if r.returncode == 0:
                subprocess.run(
                    ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostdin",
                     "-i", tmpmp3,
                     "-ar", "48000", "-ac", "1", "-sample_fmt", "s16", tmpwav],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                success = os.path.exists(tmpwav) and os.path.getsize(tmpwav) > 0
        except Exception as e:
            log_action(f"TTS edge generate fout: {e}", source="tts")
        finally:
            if tmpmp3:
                try: os.remove(tmpmp3)
                except Exception: pass

    if not success:
        try:
            ev = "nl"
            if voice and not voice.endswith(".onnx") and "Neural" not in voice:
                ev = voice
            subprocess.run(
                ["espeak-ng", "-v", ev, "-s", str(wpm), "-w", tmpwav, text],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            success = os.path.exists(tmpwav) and os.path.getsize(tmpwav) > 0
        except Exception:
            pass

    if not success:
        try: os.remove(tmpwav)
        except Exception: pass
        return None

    return tmpwav


def tts_speak_async(text, voice="", wpm=165, gain_pct=DEFAULT_TTS_GAIN,
                    use_preroll=False, use_outro=False, save_token: str = "",
                    log_user: str = "", log_ip: str = ""):
    global _stop_requested
    _stop_requested = False
    text = (text or "").strip()
    if not text:
        return

    # Registreer de TTS-uitzending zodat traceerbaar is wie wat omriep.
    # (Een gewone TTS-say werd voorheen helemaal niet gelogd.)
    if not save_token:
        log_action(f"TTS afgespeeld: \"{text[:80]}\"", source="tts",
                   user=log_user, ip=log_ip)

    wav_result = [None]

    def _generate():
        wav_result[0] = _tts_generate_to_wav(text, voice, wpm)

    wav_path = None
    with duck_lock:
        prev_bg = get_bg_volume_pct()

        t_gen = threading.Thread(target=_generate, daemon=True)
        t_gen.start()

        t_duck = threading.Thread(target=pi_duck, daemon=True)
        if PI_ENABLED:
            t_duck.start()
        _duck_local(prev_bg)
        if PI_ENABLED:
            t_duck.join()

        t_gen.join()
        wav_path = wav_result[0]

        if not wav_path:
            t_unduck = threading.Thread(target=pi_unduck, daemon=True)
            if PI_ENABLED:
                t_unduck.start()
            _unduck_local(prev_bg)
            if PI_ENABLED:
                t_unduck.join()
            return

        if save_token:
            with _tts_cache_lock:
                _tts_cache[save_token] = {
                    "path": wav_path,
                    "text": text,
                    "ts":   time.time(),
                }

        set_pst_gain(max(0, min(200, int(gain_pct))))
        if use_preroll and not _stop_requested:
            _play_preroll()
        if not _stop_requested:
            _play_file_to_pst(wav_path)
        if use_outro and not _stop_requested:
            _play_outro()

        t_unduck = threading.Thread(target=pi_unduck, daemon=True)
        if PI_ENABLED:
            t_unduck.start()
        _unduck_local(prev_bg)
        if PI_ENABLED:
            t_unduck.join()

        _stop_requested = False

    if not save_token and wav_path:
        try: os.remove(wav_path)
        except Exception: pass


def tts_preview_async(text, voice="", wpm=165, save_token: str = ""):
    text = (text or "").strip()
    if not text or not save_token:
        return

    wav_path = _tts_generate_to_wav(text, voice, wpm)
    if wav_path:
        with _tts_cache_lock:
            _tts_cache[save_token] = {
                "path": wav_path,
                "text": text,
                "ts":   time.time(),
            }


# ──────────────────────────────────────────────
# Scheduler
# ──────────────────────────────────────────────
_schedules       = schedules
_sched_lock      = threading.RLock()
SCHED_LOCK_PATH  = "/tmp/omroepweb_scheduler.lock"
_scheduler_active = False
_sched_lockfile   = None

# ──────────────────────────────────────────────
# Automatiseringen (HA-achtig: triggers op tijd/dag → acties)
# ──────────────────────────────────────────────
_DAY_ORDER   = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_HA_DAY_MAP  = {"mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu",
                "fri": "Fri", "sat": "Sat", "sun": "Sun"}
_autom_lock       = threading.RLock()
_autom_running    = set()     # id's die nu draaien (mode single)
_autom_last_key   = {}        # id → "date|hm" (dedup per minuut)

def _save_automations():
    with _autom_lock: _save_json(AUTOM_JSON, automations)

def _new_autom_id():
    with _autom_lock:
        return (max([a.get("id", 0) for a in automations]) + 1) if automations else 1

def _seed_automations():
    """Bouw de eerste automations.json: migreer bestaande schema's + zet de twee
    HA-voorbeelden klaar. schedules.json blijft als backup ongewijzigd staan."""
    out, nid = [], 1
    for s in (schedules or []):
        pid = int(s.get("preset_id") or 0)
        if pid <= 0: continue
        if s.get("kind") == "at_times":
            trigs = [{"time": t, "days": list(s.get("days") or [])}
                     for t in (s.get("times_hm") or [])]
        else:
            continue                      # interval niet 1-op-1 migreerbaar → overslaan
        if not trigs: continue
        out.append({"id": nid, "name": f"Preset {pid} (gemigreerd)", "enabled": True,
                    "last_run": 0, "triggers": trigs,
                    "actions": [{"type": "preset_sequence", "presets": [pid],
                                 "intro": True, "outro": True}]})
        nid += 1
    # HA-voorbeeld 1: avondsluiting (preset 1 → 10)
    wk = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    out.append({"id": nid, "name": "Avond omroep sluit", "enabled": True, "last_run": 0,
                "triggers": [{"time": "20:50", "days": wk}, {"time": "20:55", "days": wk},
                             {"time": "18:50", "days": ["Sun"]}, {"time": "18:55", "days": ["Sun"]}],
                "actions": [{"type": "preset_sequence", "presets": [1, 10],
                             "intro": True, "outro": True}]}); nid += 1
    # HA-voorbeeld 2: ochtend RCA aan + volume 65
    out.append({"id": nid, "name": "Ochtend: PLUS Radio aan + volume", "enabled": True,
                "last_run": 0,
                "triggers": [{"time": "06:00", "days": wk}, {"time": "10:00", "days": ["Sun"]}],
                "actions": [{"type": "rca", "state": "on"}, {"type": "volume", "value": 65}]})
    return out

automations = _load_json(AUTOM_JSON, None)
if automations is None:               # eerste keer → migreren + voorbeelden
    automations = _seed_automations()
    _save_automations()
    _schedules.clear()                # oude scheduler inert maken (schedules.json blijft backup)

def run_preset_sequence(preset_ids, intro=True, outro=True, log_user="Automatisering"):
    """Speel presets vloeiend achter elkaar: intro alleen vóór de eerste, outro
    alleen ná de laatste, geen intro/outro ertussen. Eén keer duck/unduck. Alles
    binnen duck_lock → serialiseert met andere omroepen (nooit afgekapt)."""
    global _stop_requested
    _stop_requested = False
    ids = [int(p) for p in preset_ids
           if os.path.exists(os.path.join(PRESETS, f"{int(p)}.wav"))]
    if not ids:
        return
    with duck_lock:
        t_duck = None
        try:
            prev_bg = get_bg_volume_pct()
            log_action("Preset-reeks " + "→".join(map(str, ids)) + " start",
                       source="preset", user=log_user)
            t_duck = threading.Thread(target=pi_duck, daemon=True)
            if PI_ENABLED: t_duck.start()
            _duck_local(prev_bg)
            if PI_ENABLED and t_duck is not None: t_duck.join(timeout=PI_DUCK_WAIT)
            first_gain = max(0, min(200, int(preset_vols.get(str(ids[0]), DEFAULT_PRESET_GAIN))))
            set_pst_gain(first_gain)
            if intro and not _stop_requested: _play_preroll()
            for idx, pid in enumerate(ids):
                if _stop_requested: break
                if idx > 0:
                    time.sleep(1.0)   # 1s stilte tussen presets; muziek blijft geduckt (geen muziek in de gap)
                set_pst_gain(max(0, min(200, int(preset_vols.get(str(pid), DEFAULT_PRESET_GAIN)))))
                _play_file_to_pst(os.path.join(PRESETS, f"{pid}.wav"))
            if outro and not _stop_requested: _play_outro()
            if PI_ENABLED and t_duck is not None: t_duck.join()
            t_un = threading.Thread(target=pi_unduck, daemon=True)
            if PI_ENABLED: t_un.start()
            _unduck_local(prev_bg)
            if PI_ENABLED: t_un.join()
            log_action("Preset-reeks klaar", source="preset", user=log_user)
        except Exception as e:
            log_action(f"Preset-reeks fout: {e}", source="preset", user=log_user)
            try: _unduck_local(get_bg_volume_pct())
            except Exception: pass
        finally:
            _stop_requested = False

def _eval_one_condition(c) -> bool:
    t = c.get("type")
    if t == "rca":
        return rca_running() == (c.get("state") != "off")
    if t == "spotify":
        return _vm_spotify_playing() == (c.get("state") != "stopped")
    if t == "time_between":
        now = datetime.now().strftime("%H:%M")
        a, b = c.get("after", "00:00"), c.get("before", "23:59")
        return (a <= now <= b) if a <= b else (now >= a or now <= b)  # over middernacht
    if t == "day":
        return _DAY_ORDER[date.today().weekday()] in (c.get("days") or _DAY_ORDER)
    return True

def _eval_conditions(conds, mode="all") -> bool:
    """True als de voorwaarden kloppen. mode 'all' = alle, 'any' = minstens één."""
    conds = conds or []
    if not conds:
        return True
    res = [_eval_one_condition(c) for c in conds]
    return any(res) if mode == "any" else all(res)

def run_automation(a, test=False):
    """Voer de acties van een automatisering sequentieel uit."""
    name = a.get("name", "?")
    for act in (a.get("actions") or []):
        try:
            typ = act.get("type")
            if typ == "preset_sequence":
                run_preset_sequence(act.get("presets") or [], bool(act.get("intro", True)),
                                    bool(act.get("outro", True)), log_user=name)
            elif typ == "rca":
                rca_stop() if act.get("state") == "off" else rca_start()
            elif typ == "rca_auto":
                # De Spotify→RCA-automatiek aan/uit. UIT = RCA blijft uit, ook als
                # Spotify pauzeert (nodig bij 'winkel dicht', anders start RCA weer).
                settings["rca_spotify_auto"] = (act.get("state") != "off")
                try: _save_json(SETTINGS_JSON, settings)
                except Exception: pass
            elif typ == "volume":
                v = max(0, min(100, int(act.get("value", 65))))
                set_bg_volume(v)
                try: _save_bg_volume(v)
                except Exception: pass
            elif typ == "channel":
                lisa_set_channel(2 if int(act.get("channel", 1)) == 2 else 1)
            elif typ == "tts":
                txt = (act.get("text") or "").strip()
                if txt:
                    # tts_speak_async is synchroon (speelt vóór het teruggeeft), dus
                    # vervolg-acties (bijv. muziek stoppen) draaien ná de omroep.
                    tts_speak_async(txt, gain_pct=int(act.get("gain", DEFAULT_TTS_GAIN)),
                                    use_preroll=bool(act.get("intro", True)),
                                    use_outro=bool(act.get("outro", False)),
                                    log_user=name)
            elif typ == "spotify":
                cmd = act.get("command")
                if cmd == "volume":
                    set_mixer(MIXER_SPOT, max(0, min(100, int(act.get("value", 50)))))
                elif cmd in ("pause", "resume", "playpause", "next", "prev", "stop"):
                    _glr_post(f"/player/{cmd}")
            elif typ == "webhook":
                url = (act.get("url") or "").strip()
                if url:
                    method = (act.get("method") or "POST").upper()
                    body   = act.get("body") or ""
                    data   = body.encode("utf-8") if (method == "POST" and body) else None
                    hdrs   = {"Content-Type": "application/json"} if data else {}
                    try:
                        urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=hdrs), timeout=8)
                    except Exception as e:
                        log_action(f"Automatisering '{name}' webhook-fout: {e}", source="schedule")
            elif typ == "wait":
                time.sleep(max(0, min(600, int(act.get("seconds", 1)))))
        except Exception as e:
            log_action(f"Automatisering '{name}' actie-fout: {e}", source="schedule")
    log_action(f"Automatisering '{name}' uitgevoerd" + (" (test)" if test else ""),
               source="schedule", user="Planner")

def _fire_automation(a):
    """Start een automatisering in een thread (mode single)."""
    aid = a.get("id")
    if aid in _autom_running:
        return
    _autom_running.add(aid)
    def _runner():
        try: run_automation(a)
        finally: _autom_running.discard(aid)
    threading.Thread(target=_runner, daemon=True).start()

def _process_automations(now_ts, day, now_hm):
    fired_any = False
    with _autom_lock:
        auts = list(automations)
    for a in auts:
        if not a.get("enabled", True):
            continue
        match = any(t.get("type") != "webhook" and t.get("time") == now_hm
                    and (not t.get("days") or day in t["days"])
                    for t in (a.get("triggers") or []))
        if not match:
            continue
        # Voorwaarden (HA-stijl): alleen doorgaan als ze kloppen.
        if not _eval_conditions(a.get("conditions"), a.get("condition_mode", "all")):
            continue
        key = f"{date.today().isoformat()}|{now_hm}"
        if _autom_last_key.get(a.get("id")) == key:
            continue
        _autom_last_key[a["id"]] = key
        a["last_run"] = int(now_ts); fired_any = True
        _fire_automation(a)
    if fired_any:
        _save_automations()

def _save_schedules():
    with _sched_lock: _save_json(SCHED_JSON, _schedules)

def _now_day_tag(): return datetime.now().strftime("%a")

def _within_window(start_hm, end_hm):
    if not start_hm and not end_hm: return True
    now = datetime.now().strftime("%H:%M")
    if start_hm and now < start_hm: return False
    if end_hm   and now > end_hm:   return False
    return True

def _ensure_interval_next_ts(s):
    if not _within_window(s.get("start_hm"), s.get("end_hm")):
        s["next_ts"] = 0; return False
    if float(s.get("next_ts") or 0) <= 0: s["next_ts"] = time.time()
    return True

def scheduler_loop():
    while True:
        try:
            now_ts = time.time(); day = _now_day_tag()
            now_hm = datetime.now().strftime("%H:%M"); changed = False
            with _sched_lock:
                for s in _schedules:
                    pid  = int(s.get("preset_id") or 0)
                    days = s.get("days") or []
                    if days and day not in days:
                        if s.get("kind")=="interval" and s.get("next_ts",0)!=0:
                            s["next_ts"]=0; changed=True
                        continue
                    if s.get("kind") == "interval":
                        every = int(s.get("every_sec") or 0)
                        if every <= 0: continue
                        if not _within_window(s.get("start_hm"), s.get("end_hm")):
                            if s.get("next_ts",0)!=0: s["next_ts"]=0; changed=True
                            continue
                        if not _ensure_interval_next_ts(s): continue
                        if now_ts + 0.01 >= float(s.get("next_ts") or 0):
                            if pid > 0:
                                threading.Thread(target=play_preset_async,args=(pid,),kwargs={"log_user":"Planner"},daemon=True).start()
                                log_action(f"Schedule interval preset {pid}", source="schedule")
                            s["next_ts"] = now_ts + every; changed = True
                    elif s.get("kind") == "at_times":
                        times = s.get("times_hm") or []
                        if not times: continue
                        key = f"{date.today().isoformat()}|{now_hm}"
                        if now_hm in times and s.get("last_run_key") != key:
                            if pid > 0:
                                threading.Thread(target=play_preset_async,args=(pid,),kwargs={"log_user":"Planner"},daemon=True).start()
                                log_action(f"Schedule at_time preset {pid} @ {now_hm}", source="schedule")
                            s["last_run_key"] = key; changed = True
            if changed: _save_schedules()
            _process_automations(now_ts, day, now_hm)
        except Exception as e:
            log_action(f"Scheduler fout: {e}", source="system")
        time.sleep(0.5)

def start_scheduler_once():
    global _scheduler_active, _sched_lockfile
    if _scheduler_active: return
    if fcntl is None:
        threading.Thread(target=scheduler_loop, daemon=True).start()
        _scheduler_active = True; return
    try:
        _sched_lockfile = open(SCHED_LOCK_PATH, "w")
        fcntl.flock(_sched_lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _sched_lockfile.write(str(os.getpid())); _sched_lockfile.flush()
        threading.Thread(target=scheduler_loop, daemon=True).start()
        _scheduler_active = True
    except BlockingIOError:
        pass

set_mixer(MIXER_PCM, 100)
start_scheduler_once()
if PI_ENABLED or PI_LOCAL_GLR:
    threading.Thread(target=_pi_keepalive_loop, daemon=True).start()
    threading.Thread(target=explicit_guard_loop, daemon=True).start()

# ──────────────────────────────────────────────
# Preset helpers
# ──────────────────────────────────────────────
def list_preset_ids():
    ids = []
    for p in glob.glob(os.path.join(PRESETS, "*.wav")):
        m = re.search(r"(\d+)\.wav$", p)
        if m: ids.append(int(m.group(1)))
    return sorted(ids)

def next_preset_id():
    ids = list_preset_ids(); return (max(ids)+1) if ids else 1

def list_piper_models():
    return [{"path":p,"name":os.path.basename(p),
             "label":os.path.basename(p).replace("_"," ").replace(".onnx","")}
            for p in sorted(glob.glob(os.path.join(PIPER_DIR,"*.onnx")))]

def current_state():
    bg,_ = get_mixer(MIXER_BG); pst,_ = get_mixer(MIXER_PST)
    with _active_pst_lock:
        playing = _active_pst_proc is not None and _active_pst_proc.poll() is None
    return {"volume":bg,"mute_status":"Muted" if _bg_muted else "Unmuted",
            "muted":_bg_muted,"bg":bg,"bg_before":_bg_vol_before,"pst":pst,
            "rca_running":rca_running(),"playing":playing,
            "plusradio_title":lisa_current_title(),"plusradio_channel":lisa_current_channel(),
            **_pr_enrich_fields(),
            "ts":time.time()}

def _pr_enrich_fields():
    """Shazam-verrijkingsvelden voor de huidige PLUS Radio-titel (leeg = geen match).
    Bij een commercial tonen we het PLUS-blad als 'albumhoes'."""
    title = lisa_current_title()
    if _title_is_commercial(title):
        return {"plusradio_artist": "", "plusradio_full_title": "Commercial",
                "plusradio_album": "", "plusradio_cover": LEAF_LOGO}
    e = _lisa_enrich_for(title)
    return {"plusradio_artist": e.get("artist", ""),
            "plusradio_full_title": e.get("title", ""),
            "plusradio_album": e.get("album", ""),
            "plusradio_cover": e.get("cover", "")}

# ──────────────────────────────────────────────
# RCA
# ──────────────────────────────────────────────
RCA_GAIN    = 2.00
RCA_PID_FILE = os.path.join(APP_DIR, "rca_loop.pid")

# ── EQ (10-band, alleen Spotify + PLUS Radio → versterker; NIET presets/TTS) ──
# Spotify: alsaequal op het spot-pad (live via amixer). PLUS Radio: ffmpeg-EQ in
# de RCA-keten (toepassen = RCA-pipe herstarten). Dezelfde 10 frequenties.
_EQ_FREQS      = [31, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
_EQ_FLAT       = 50
_EQ_SPOT_CTL   = "eq_spot"     # ALSA-ctl (alsaequal)
_EQ_SPOT_BANDS = ["00. 31 Hz", "01. 63 Hz", "02. 125 Hz", "03. 250 Hz", "04. 500 Hz",
                  "05. 1 kHz", "06. 2 kHz", "07. 4 kHz", "08. 8 kHz", "09. 16 kHz"]

def _eq_get(which):
    v = settings.get("eq_spot" if which == "spot" else "eq_bg")
    if not isinstance(v, list) or len(v) != 10:
        v = [_EQ_FLAT] * 10
    return [max(0, min(100, int(x))) for x in v]

def _apply_eq_spot():
    """Spotify-EQ live zetten via alsaequal (amixer)."""
    for name, val in zip(_EQ_SPOT_BANDS, _eq_get("spot")):
        try:
            subprocess.run(["amixer", "-D", _EQ_SPOT_CTL, "sset", name, str(val)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except Exception:
            pass

def _eq_bg_af():
    """ffmpeg-filterketen voor de PLUS Radio-EQ (0-100 → -12..+12 dB)."""
    parts = [f"volume={RCA_GAIN}"]
    for f, val in zip(_EQ_FREQS, _eq_get("bg")):
        db = (val - _EQ_FLAT) / 50.0 * 12.0
        if abs(db) >= 0.3:
            parts.append(f"equalizer=f={f}:t=o:w=1:g={db:.1f}")
    return ",".join(parts)

def RCA_CMD():
    return ("arecord -D linein -f S16_LE -c 2 -r 48000 -t raw --buffer-size=16384 --period-size=1024 | "
            "ffmpeg -hide_banner -loglevel error -f s16le -ar 48000 -ac 2 -i pipe:0 "
            f"-filter:a {_eq_bg_af()} -ac 1 -f alsa bg")

# ── Server-side visualizer voor PLUS Radio (line-in FFT) ───────────────────
# De browser-Web-Audio-aanpak op de Icecast-stream bleek onbetrouwbaar; nu leest
# de server de line-in (dsnoop, naast RCA/ring) en rekent een spectrum uit dat de
# browser ophaalt via /api/viz/rca. Eigen arecord-signatuur (GEEN -q, -c 1 -r
# 22050) zodat _kill_ring_recorders/rca_stop 'm niet meepakken. On-demand: draait
# alleen zolang de pagina pollt.
try:
    import numpy as _np
    _HAVE_NP = True
except Exception:
    _HAVE_NP = False

_VIZ_BANDS     = 28
_viz_lock      = threading.Lock()
_viz_levels    = [0.0] * _VIZ_BANDS
_viz_last_poll = 0.0
_viz_thread    = None

def _viz_capture_loop():
    global _viz_levels, _viz_thread
    SR, N, K, SC = 22050, 1024, 80.0, 5.0
    proc = None
    try:
        if not _HAVE_NP:
            return
        proc = subprocess.Popen(
            ["arecord", "-D", "linein", "-f", "S16_LE", "-c", "1", "-r", str(SR), "-t", "raw"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        freqs = _np.fft.rfftfreq(N, 1.0 / SR)
        edges = _np.logspace(_np.log10(40), _np.log10(SR / 2), _VIZ_BANDS + 1)
        idx = [int(_np.searchsorted(freqs, e)) for e in edges]
        win = _np.hanning(N).astype(_np.float32)
        nbytes = N * 2
        while time.time() - _viz_last_poll < 3.0:
            raw = proc.stdout.read(nbytes)
            if not raw or len(raw) < nbytes:
                break
            x = _np.frombuffer(raw, dtype='<i2').astype(_np.float32) / 32768.0
            mag = _np.abs(_np.fft.rfft(x * win))
            out = _np.empty(_VIZ_BANDS, dtype=_np.float32)
            for b in range(_VIZ_BANDS):
                lo = idx[b]; hi = max(lo + 1, idx[b + 1])
                out[b] = mag[lo:hi].mean()
            lv = _np.clip(_np.log1p(out * K) / SC, 0.0, 1.0)
            with _viz_lock:
                _viz_levels = [round(float(z), 3) for z in lv]
    except Exception:
        pass
    finally:
        try:
            if proc: proc.terminate()
        except Exception: pass
        with _viz_lock:
            _viz_thread = None

def rca_running():
    # Robuust via het pidfile i.p.v. `pgrep -f "arecord -D linein"`. Die substring
    # matchte óók op andere/debug-commando's (en gaf zo een vals-positief), waardoor
    # rca_start() ten onrechte werd overgeslagen en RCA gestopt bleef. Nu checken we
    # of het proces uit het pidfile leeft én écht de RCA-opname is.
    try:
        with open(RCA_PID_FILE) as f:
            pid = int((f.read() or "0").strip())
    except Exception:
        return False
    if pid <= 0:
        return False
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cl = f.read()
    except Exception:
        return False
    return b"arecord" in cl and b"linein" in cl

def rca_start():
    if rca_running(): return
    proc = subprocess.Popen(RCA_CMD(), shell=True, preexec_fn=os.setsid,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(RCA_PID_FILE,"w") as f: f.write(str(proc.pid))
    log_action("RCA START", source="rca")

def rca_stop():
    if os.path.exists(RCA_PID_FILE):
        try:
            with open(RCA_PID_FILE,"r") as f: pid = int(f.read().strip())
            os.killpg(pid, signal.SIGTERM)
        except Exception: pass
        try: os.remove(RCA_PID_FILE)
        except Exception: pass
    # Specifiek patroon (het volledige RCA-opnamecommando) zodat losse/debug-
    # opnames op de line-in niet per ongeluk mee-gekilld worden. Ook de RCA-
    # ffmpeg apart killen: bij een snelle stop/start (bijv. EQ-wijziging) bleef
    # die soms als wees op 'bg' hangen (dubbel geluid). De '-i pipe:0'-signatuur
    # is uniek voor RCA (presets/reclames lezen een bestand, geen pipe).
    subprocess.run(["pkill","-f","arecord -D linein -f S16_LE -c 2 -r 48000"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["pkill","-f","f s16le -ar 48000 -ac 2 -i pipe:0"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log_action("RCA STOP", source="rca")

def rca_toggle():
    if rca_running(): rca_stop(); return False
    rca_start(); return True

# ──────────────────────────────────────────────
# PLUS logo (SVG data-URI) — één keer gedefinieerd en via een Jinja-global
# beschikbaar als {{ logo }} in alle templates (was voorheen 2x inline).
# ──────────────────────────────────────────────
PLUS_LOGO = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2MDkuMDkgMTEzLjUiIGZpbGw9IiNmZmZmZmYiPjxwYXRoIGQ9Ik01My4wMywyNi41NXYxNy42OGMwLDQuODgtMy45Niw4Ljg0LTguODQsOC44NGgtMTcuNjhDMTEuODcsNTMuMDYsMCw0MS4xOSwwLDI2LjU1UzExLjg3LjAzLDI2LjUyLjAzczI2LjUyLDExLjg3LDI2LjUyLDI2LjUyIi8+PHBhdGggZD0iTTUzLjAzLDg2Ljk1di0xNy42OGMwLTQuODgtMy45Ni04LjgzLTguODQtOC44M2gtMTcuNjhjLTE0LjY0LDAtMjYuNTIsMTEuODctMjYuNTIsMjYuNTFzMTEuODcsMjYuNTIsMjYuNTIsMjYuNTIsMjYuNTItMTEuODcsMjYuNTItMjYuNTIiLz48cGF0aCBkPSJNNjAuMzYsODYuOTZ2LTE3LjY4YzAtNC44OCwzLjk2LTguODQsOC44NC04Ljg0aDE3LjY4YzE0LjY0LDAsMjYuNTEsMTEuODcsMjYuNTEsMjYuNTFzLTExLjg3LDI2LjUyLTI2LjUxLDI2LjUyLTI2LjUyLTExLjg3LTI2LjUyLTI2LjUyIi8+PHBhdGggZD0iTTYwLjQxLDI2LjU1djE3LjY4YzAsNC44OCwzLjk2LDguODQsOC44NCw4Ljg0aDE3LjY4YzE0LjY1LDAsMjYuNTItMTEuODcsMjYuNTItMjYuNTFTMTAxLjU3LjAzLDg2LjkyLjAzcy0yNi41MSwxMS44Ny0yNi41MSwyNi41MiIvPjxwYXRoIGQ9Ik02MDIsMTVjMCw3LjI0LTUuODcsMTMuMTEtMTMuMSwxMy4xMS0uNzgsMC0xLjUzLS4wNy0yLjI4LS4xOS01LjQ0LS45Ni0xMS4xOS0xLjUtMTcuMTQtMS41LTYuNiwwLTE4LjA4LjE2LTE4LjA4LDcuMjMsMCwxNC4zLDU3LjY5Ljc5LDU3LjY5LDQzLjA3LDAsMjkuNC0yOS4wOCwzNi43OS01My40NSwzNi43OS0xMi4yOSwwLTIyLjk1LS45LTM0LjI1LTIuOTItNi4yNC0xLjAxLTExLjAzLTYuNDItMTEuMDMtMTIuOTV2LTE3Ljc2YzExLjMzLDQuNzIsMjUuMTYsNy4yMywzNy43Myw3LjIzLDkuOTEsMCwxOC44Ny0yLjA0LDE4Ljg3LTcuNTUsMC0xNC43OC01Ny42OS0xLjQxLTU3LjY5LTQ0LjAyLDAtMzAuMTgsMzEuNDQtMzUuNTIsNTYuNDQtMzUuNTIsMTEuNzksMCwyNC44NCwxLjQxLDM2LjMxLDMuNzd2MTEuMjNoLS4wMloiLz48cGF0aCBkPSJNMTQ4LjIyLDExMS40VjE0Ljc3YzAtNy4yNCw1Ljg3LTEzLjExLDEzLjExLTEzLjExaDU5LjM2YzE3LjEzLDAsNDAuMjUsOC4xNyw0MC4yNSwzNy43M3MtMTguMzksNDAuNC00MC40LDQwLjRoLTMwLjE4djE4LjQ5YzAsNy4yNC01Ljg3LDEzLjEtMTMuMSwxMy4xaC0yOS4wM1pNMTkwLjM1LDI3LjE0djI3LjJoOC4xN2MxMC4wNiwwLDIwLjI4LTEuODksMjAuMjgtMTQuMTVzLTEwLjIyLTEzLjA1LTIwLjQ0LTEzLjA1aC04LjAyWiIvPjxwYXRoIGQ9Ik00ODguMjMsNjYuMTJjMCwzNS41My0yMS44NSw0Ny4xNy01NS4wMiw0Ny4xNy0zMC42NiwwLTU0LjcxLTEyLjU4LTU0LjcxLTQ0Ljk3VjEuNjdoMjkuMDNjNy4yNCwwLDEzLjExLDUuODcsMTMuMTEsMTMuMTF2NTEuOThjMCwxMC4zOCwyLjk5LDE4LjI0LDEzLjA1LDE4LjI0LDExLDAsMTMuMzYtNy4zOSwxMy4zNi0xOC4wOFYxLjY3czI4LjA2LDAsMjguMDYsMGM3LjI1LDAsMTMuMTEsNS44NywxMy4xMSwxMy4xMWwuMDIsNTEuMzVaIi8+PHBhdGggZD0iTTI3OS40NywxMTEuNFYxLjY3czI5LjAyLDAsMjkuMDIsMGM3LjI0LDAsMTMuMTEsNS44NywxMy4xMSwxMy4xMXY2NC4yNGg0Mi4xNXYxOS4yOGMwLDcuMjQtNS44NiwxMy4xLTEzLjEsMTMuMWgtNzEuMThaIi8+PC9zdmc+"

app.jinja_env.globals["logo"] = PLUS_LOGO
LEAF_LOGO = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMTMuNSAxMTMuNSIgZmlsbD0iIzgwYmQxZCI+PHBhdGggZD0iTTUzLjAzLDI2LjU1djE3LjY4YzAsNC44OC0zLjk2LDguODQtOC44NCw4Ljg0aC0xNy42OEMxMS44Nyw1My4wNiwwLDQxLjE5LDAsMjYuNTVTMTEuODcuMDMsMjYuNTIuMDNzMjYuNTIsMTEuODcsMjYuNTIsMjYuNTIiLz48cGF0aCBkPSJNNTMuMDMsODYuOTV2LTE3LjY4YzAtNC44OC0zLjk2LTguODMtOC44NC04LjgzaC0xNy42OGMtMTQuNjQsMC0yNi41MiwxMS44Ny0yNi41MiwyNi41MXMxMS44NywyNi41MiwyNi41MiwyNi41MiwyNi41Mi0xMS44NywyNi41Mi0yNi41MiIvPjxwYXRoIGQ9Ik02MC4zNiw4Ni45NnYtMTcuNjhjMC00Ljg4LDMuOTYtOC44NCw4Ljg0LTguODRoMTcuNjhjMTQuNjQsMCwyNi41MSwxMS44NywyNi41MSwyNi41MXMtMTEuODcsMjYuNTItMjYuNTEsMjYuNTItMjYuNTItMTEuODctMjYuNTItMjYuNTIiLz48cGF0aCBkPSJNNjAuNDEsMjYuNTV2MTcuNjhjMCw0Ljg4LDMuOTYsOC44NCw4Ljg0LDguODRoMTcuNjhjMTQuNjUsMCwyNi41Mi0xMS44NywyNi41Mi0yNi41MVMxMDEuNTcuMDMsODYuOTIuMDNzLTI2LjUxLDExLjg3LTI2LjUxLDI2LjUyIi8+PC9zdmc+"
SPOTIFY_ICON = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9Ii0zMy40OTc0IC01NS44MjkgMjkwLjMxMDggMzM0Ljk3NCI+PHBhdGggZmlsbC1ydWxlPSJldmVub2RkIiBkPSJNMTc3LjcwNyA5OC45ODdjLTM1Ljk5Mi0yMS4zNzUtOTUuMzYtMjMuMzQtMTI5LjcxOS0xMi45MTItNS41MTkgMS42NzQtMTEuMzUzLTEuNDQtMTMuMDI0LTYuOTU4LTEuNjcyLTUuNTIxIDEuNDM5LTExLjM1MiA2Ljk2LTEzLjAyOSAzOS40NDMtMTEuOTcyIDEwNS4wMDgtOS42NiAxNDYuNDQzIDE0LjkzNiA0Ljk2NCAyLjk0NyA2LjU5IDkuMzU2IDMuNjQ5IDE0LjMxLTIuOTQ0IDQuOTYzLTkuMzU5IDYuNi0xNC4zMSAzLjY1M20tMS4xNzggMzEuNjU4Yy0yLjUyNSA0LjA5OC03Ljg4MyA1LjM4My0xMS45NzUgMi44NjctMzAuMDA1LTE4LjQ0NC03NS43NjItMjMuNzg4LTExMS4yNjItMTMuMDEyLTQuNjAzIDEuMzktOS40NjYtMS4yMDQtMTAuODY0LTUuOGE4LjcxNyA4LjcxNyAwIDAxNS44MDUtMTAuODU2YzQwLjU1My0xMi4zMDcgOTAuOTY4LTYuMzQ3IDEyNS40MzIgMTQuODMzIDQuMDkyIDIuNTIgNS4zOCA3Ljg4IDIuODY0IDExLjk2OG0tMTMuNjYzIDMwLjQwNGE2Ljk1NCA2Ljk1NCAwIDAxLTkuNTY5IDIuMzE2Yy0yNi4yMi0xNi4wMjUtNTkuMjIzLTE5LjY0NC05OC4wOS0xMC43NjZhNi45NTUgNi45NTUgMCAwMS04LjMzMS01LjIzMiA2Ljk1IDYuOTUgMCAwMTUuMjMzLTguMzM0YzQyLjUzMy05LjcyMiA3OS4wMTctNS41MzggMTA4LjQ0OCAxMi40NDZhNi45NiA2Ljk2IDAgMDEyLjMxIDkuNTdNMTExLjY1NiAwQzQ5Ljk5MiAwIDAgNDkuOTkgMCAxMTEuNjU2YzAgNjEuNjcyIDQ5Ljk5MiAxMTEuNjYgMTExLjY1NyAxMTEuNjYgNjEuNjY4IDAgMTExLjY1OS00OS45ODggMTExLjY1OS0xMTEuNjZDMjIzLjMxNiA0OS45OTEgMTczLjMyNiAwIDExMS42NTcgMCIgZmlsbD0iIzFlZDY2MCIvPjwvc3ZnPg=="
app.jinja_env.globals["leaf_logo"] = LEAF_LOGO
PLUS_WORDMARK = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 609.09 113.5" fill="currentColor" aria-hidden="true"><path d="M53.03,26.55v17.68c0,4.88-3.96,8.84-8.84,8.84h-17.68C11.87,53.06,0,41.19,0,26.55S11.87.03,26.52.03s26.52,11.87,26.52,26.52"/><path d="M53.03,86.95v-17.68c0-4.88-3.96-8.83-8.84-8.83h-17.68c-14.64,0-26.52,11.87-26.52,26.51s11.87,26.52,26.52,26.52,26.52-11.87,26.52-26.52"/><path d="M60.36,86.96v-17.68c0-4.88,3.96-8.84,8.84-8.84h17.68c14.64,0,26.51,11.87,26.51,26.51s-11.87,26.52-26.51,26.52-26.52-11.87-26.52-26.52"/><path d="M60.41,26.55v17.68c0,4.88,3.96,8.84,8.84,8.84h17.68c14.65,0,26.52-11.87,26.52-26.51S101.57.03,86.92.03s-26.51,11.87-26.51,26.52"/><path d="M602,15c0,7.24-5.87,13.11-13.1,13.11-.78,0-1.53-.07-2.28-.19-5.44-.96-11.19-1.5-17.14-1.5-6.6,0-18.08.16-18.08,7.23,0,14.3,57.69.79,57.69,43.07,0,29.4-29.08,36.79-53.45,36.79-12.29,0-22.95-.9-34.25-2.92-6.24-1.01-11.03-6.42-11.03-12.95v-17.76c11.33,4.72,25.16,7.23,37.73,7.23,9.91,0,18.87-2.04,18.87-7.55,0-14.78-57.69-1.41-57.69-44.02,0-30.18,31.44-35.52,56.44-35.52,11.79,0,24.84,1.41,36.31,3.77v11.23h-.02Z"/><path d="M148.22,111.4V14.77c0-7.24,5.87-13.11,13.11-13.11h59.36c17.13,0,40.25,8.17,40.25,37.73s-18.39,40.4-40.4,40.4h-30.18v18.49c0,7.24-5.87,13.1-13.1,13.1h-29.03ZM190.35,27.14v27.2h8.17c10.06,0,20.28-1.89,20.28-14.15s-10.22-13.05-20.44-13.05h-8.02Z"/><path d="M488.23,66.12c0,35.53-21.85,47.17-55.02,47.17-30.66,0-54.71-12.58-54.71-44.97V1.67h29.03c7.24,0,13.11,5.87,13.11,13.11v51.98c0,10.38,2.99,18.24,13.05,18.24,11,0,13.36-7.39,13.36-18.08V1.67s28.06,0,28.06,0c7.25,0,13.11,5.87,13.11,13.11l.02,51.35Z"/><path d="M279.47,111.4V1.67s29.02,0,29.02,0c7.24,0,13.11,5.87,13.11,13.11v64.24h42.15v19.28c0,7.24-5.86,13.1-13.1,13.1h-71.18Z"/></svg>'
app.jinja_env.globals["plus_wordmark"] = PLUS_WORDMARK

app.jinja_env.globals["spotify_icon"] = SPOTIFY_ICON
SPOTIFY_LOGO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJIAAAAoCAYAAAAVKqOdAAAACXBIWXMAAA1oAAANZwA6dqT2AAAQAElEQVR4nO1cCXhU1dnOzCSzZZbMTCYzmclkJixhTdhl3xLWRCAQwp6VEPaioMXfhVqr9dda1wJaW7WgYIVaKrgDKhVkERANMYEQZLPF7S9WQEGS//3OXXLnZmaydJL0kXzPc59J5p57lu+85/ve7ztnbkREGERl1drUqbF99GO8kww5yUWGGZ0W0Cf9T9/T/XC00yY/QYlqZ+5omp96i2P9+B0Je2d+kVhRWOM9WVzjPTWv9sL/9D3ddzw/fodpQeqtUe1jklu7723yXyCaXnED7KvTNnk+ybvkPc2D5VhRTWJ5QU3ipwEu+v4YgWxuDZX3lOZftq9N36zp6xjU2mNpk1YQlV3nsD047BmA4pr3FGdpAgKnvoss1ykGvmrbQ8OeU8Xpna09tjZpIdENTxjrfn/6KR8sSmJ5EwFUx1IVMgvl3j3jjG6kJ6O1x9gmzSzG3C6LYIV+9J6YGx4AyS5W7/GiH435XZe29ljbpJnEVJyy3PtZMeM4zQEi8SIOhXZMJam3tvaY2yTMEj25wxxv1dymc6GmcCe0Fz2lY15rj71NwiTqrrZUz8d5/4bLaRkQCRfaQzT4nbq7rWdr6+C/XpQKpUIXqWtIUYVaFaXQqNTN3SV/USmUzs0T9jGX1pIgEjjTyeIa58sTD0REKlVNHoMiIiIywejV9HEM1A5yjdL0cw6JSjJ3aHllNo9QcBK/NetD93vTqqz3DFqj0Kq0gcppB8QPt69J3+R6K7vc9Xb2sbhnx74endUht0U6aczruoSiKf8Iq4DliogYE8BYsvH0PP/ko/Ad+76YS05WFjXJNVJ0aCzotqyxfVfoo6JNc7vf7PzrxP2ej3K/IwvH+sxZuu9JoVD8anWqvW9z6K4lRGXT2RP2z/qa6Rv69f1zQY1pQepKeTnDtOS5uH9NKMcu/m91F2tqs3ZSaVQbgfIzDACChaC/MREJH8z8AhN00L46/WXrqgGPmxf3vBOgW2qY3qkYV5FhZuf5mMQVMcv73Ge7f8gfgf63XG9mV3gO535H3IdLXjaMc1Gb7l3TzypNanND+07Kcb0x5RPfmZIakduVSxYCcTBSJvUDUaJ5We+7m1GVYZHIRFOSXAcYZwqjHHwaxndmXo3twaHr/J7zmtp7juRd9ArUBOMXDEDSV4tqrPcOfqpZOw4wlEitESk+ftvkjzU3OIcoYzQWchmNEfLNkW5Dom54whjzz3qtcqwfv9NzcM4FwWKFAhX1wziny8KGtBPpik5wvz/jrNQdM0t0WmYlecVSOedfJuxrio5aSvRjfZNpTLQVJf1eEaWMdLyYudv3j/kMRLRodKMSJ0jLmJf0vIvuSRYRJX/XI4DKwwJa5diYsatZE8HUQbaahcmgToY5WaiKj3YjMsuNe3r0VhD6S7yFqAsktO186ca9DanT9ushf/CdLaldfQARgLKfrKMxv+sS0/zUlbbfDFvnfifnMwIRWS3Hhoz3wjmucAotOpZfKyv4MTLR6JPfV9m0sealve6Am35cNyxhrPy+fW36FmFR0Sf087T0vtKgNioNUcZm6TyQnwwe8YPUSpAr0o/zTQn2jEKtjELkoFfoI6MV2kgtiHqjCDIR4Jib+/wSbuw0s4RSQFE/SvOvRHWI6RyqDuaO/z79c+FZmoCYW/v+OmB/9VF6SmugfFX83yYdbExfW0KUZk0MQPAXQRfgeRdVdp1dVqxevxD3zNg3mMUnfcAS69ITJ4Yo3kg/U48YsjsWkA+Vh+OunTlVMLNTEP2km4q632T91aC1cX8Y8xpW/AFwknLcP4nrtGv71BPx27JKHRsz3499Im1TzMp+DximdsynYyQ02aHaJh6Aupcl7Jt1Xgom6o9hWqe5oZ6NTDAkksIZ8HDh70tKS+hjK6pYncMwNTmf/qaFAK632FSSuoIuuNP5QnSHur3mRT1us/8u7SX7U6O3WO4a8Aj0MLI+XdKi0o9PmgIu8qRj3fgdsKy7aXItt/d/SDvYlRboGXU3W0/Xm1OOitSCXFJp/lUsintJNyDUK2gRUNnoCe2m0/+meSnLYW2Xq5zRbnKB5oU9llNZBBUVopXHJzjUcwhelrDy/IVxrUA0OziojqzaWJS7GdcKtLHCOKtzCaUcdEPdozCvs6kvsIxykEdEWO8euLoOkPiOMLIscA7+eIj4nfSi707ykR3PS2hyYXHO2J8c9Vfj7C7zQQTbBes8wtVhaPOKQCSpLQA3JDHko5hvWPa9nPW32rys1yriZ6GeE5936N2JR/Ov+c6V1NBF0R7ApYme2H6W59Ccrxl5p/EIY8IY6fRDsECAqACCjFLGyU5xAQanl9rn4VZ3qjtbU4RnALpsuPkLLBiRu3i+XYrOXK9PqaDyCHo+8p1fwH2PT+gtDWH9rKSvFrLv5DsRYrAjuai++FeyjgSzRwDqbUlfcvVRvbGPjNio6WnvC0AuRVB1izG3ywLQhsV43r8GRFlvC+awzsXzDqYc6shnPHEtK6j2lOZd8ZTm/0Crh23ESsvxKQB28QqhaAKr8zVaVfKEGlkHRIdfsWMpvGt1rBu3sz4wOF7I2CUS7XJOca4dUythQR7VDXOPVpqDR38gna6EA7O/ZcpHu653ck4C8POIoIqLg3ijMDmon/gY2nyXiK+0LkSv8zDWapFnCnoTUiGipS2uAUi/gUUYyvq/btx2BozKAFyxkkthEKDjt2aVsfIbMvYIbdCnpp9jePSk9jOJgDNuJQ9ihDTICf9x0P+BLCQtQnibCtYfWtTHCq+pu9p66Md4swDakY7nx78HK74oelKH2UpYrtonlQoFOMNHQTdm0ZH41yYfBWH9ExFXfUZSDikBqyo1qr05GVdH4jLqlNg+2qHu0XAbhTDJ99t/P3oruT5hp5+bkCJOsZh4uMMKoPsmcAM20abilBV+Ckd/oLxPKEkaCkh0OkEArN8E8G0i+jkX++iIF8AVMsk8BwUSlEvpCkzyt2RNiDPCLX0Axb2b8OHsC9JAhMAE93CHUI+md9xAjPNqIrfAxBxa/JZJh0EF3iAaIE5kGQcA9+4ZnyMajrH8vN/9sDaHKEKGdfxRTFtgoULvpc4tkw7i81Dsw8M3MCBt9AeStr8zTTvEnYY2DlFZRMbfiqc08OnakXMSVuxDXAcS9sw8L4CJAB372Mg/y/WpH+2dJHIsfAqLWdPXMRgAWoixDoDFzjYWdvO3SMQJ4FePBVwRqMj2wNBnQk1kKAER1wNgvU0lKbdAAe8lluVfEcikkCSjnBEBhsv9FPqBAWCrBOfQ1NcOTPscTPaXLCSulB20o7b4lAOUuQ88R1yFfkASVir6BA64l3I2QrlIl8EDQO0UJ5DluqadRfRjoPtxfxq3Q4yU6N7uGWeJT4gdjFSqiJfBhV0U2iIrY7mj/yOSvrBkI7tPfO9I7qVIn8nHbipr5wvR9V4pkLCQMjllc/fRl7ekQEDAlCM8iyhvjKgfro2LlK+S6hIR9aviWLjnxYALgE0HR5oJfc+k6NF/skMBCZNORDzg7MFS4FkNuSiY+aiG8P+oTpZuMViBLO8jRGq86ZWfsmwMkEgw2Qkxt/S9lywduV7RCvpFosXs2AqUwcYkBxLf5nEQdmud+t0GD8D6f2LZE+RWnEOJlMOSXBUXAiwTXEZ6oD5SElecZALcu9POUEae9cWmi60DJI/RK68jKJB4iXturD+Qxninyp7fLfAx0hE45d3i/CRbumEsLHpnHuH1KZ+yuW2QcK7tSCDXRhMCs1uGzo4jkxezrPfdcBMb4Kd3wYp8DABWwnRWoUw5Zb4pOqHMqamw2zLa61FZZagVmkSoS9sZCXtmnAuUR2qMa5OLQqvS0FFeIt2IInfR9ggj/gKJ57ZMLmO1t4drifUDEtrUZyZNC1Y3goat4iTRIstJnqtL89woruB68l/E1zDm89zxZNZmNfEPuodosq5FCpBHqh9IMos0ttYikRA1kVpP8MmTAl+1/M8NDwmRI0sKFzZyqyoU2fYKkRt/7poRZ3nkViWJToR9N3SSDv7H/XHMqyxig8WQt0u5JIT9XwQ680R1kcto1EACCLVhXTXgUVi8q4LVI7diXtrrFwpDlElKtuGSvhDcVSBBdLtGiG693J7gzQBToah8ABZccn2o/jhfnnhQsMCkI+3AeOZqWwpIFCTEvzr5qGA4aD71433ZCrhfMSfHb4spgxiCoCJVUODIjTsvJG7Q8opAxHYVq/sKhdDcIf/a0J8BrLJI/A4k9l+xD49YT7vy0rZBJMsCulUu/H8yVL/J3RhmhM41iWP8xcAnpBlfEM2XYCEsANIFMX1QAbc0MH5EsDpifzv8BbEOAtLszov0me2mi+Ai8INjBHue3ARZcZGnALxEXuleSwGJBP1eIO2z/alRr1DeTzo2y+39H26IXv0kYEJSEv4jgriGAbxvubP/I7RRC9I1Wt09tndU+5jOlAyL6mjpRgqhEJGiL9qSAOpLiTv4RWynuDwHpfFpj4g2gPF/dUBLyBKSyaETkh6jD21csdx2wwPycLzOGGdCeYLlICA9PnKTH5AE17R5wl640zqMj/gg3ECVAHqqg/JGlEysBUZhDer7RuWMdgXqg7Z//DAKp8WyiAaFfS+VXRcnA9JlSrjK6wgHkGibhG3QH+f6TW3B5f5TTOyW5n+PSLxTKH0GFLZFUpr/Q6CNVLIulpX9Hmh0peA2IG9dKcR3brpxDwPSZ1ySUkgBBM1dNXCLhCwSZbb5PMthhKUzArkmttkpiboouou5qfc9fq5NMl7wwOcJONI6aOtF7C/Kew7nXqSsMo3T9TasjOAquBW+Rf48gSt+W5aYZqF2KEUi3IcbsYEKfCVYR+b2hrpHy8cSDiCRmJf0vLM2k14o5pjYInsibXMovYcU+aatqFhUbL1n0FpMhooy0yCXGXRYHxHS/dZfDlxtvW/wk5Y7BzwKzrEKIW6Bpp9jMMx0nLx+IsCwAi9CSfX+mKChm7YU1SCkvixEGdRXrLTTAMKLtAsOsrg8ZmW/B+O3Tf5EbLOCKY1IbipIv9UPSGUF1cIZcsqdUR0IHG5CEPGmt7I2siQgwk1vEPpBrkLccecnEBHPUfPinneQTgDC/6W8kahf6sPxomo6WSHUAY4SSVGSCLTjjAhXGed0WUwcE1b3oQiUkSckmwoksoRkPf34aS1vG9Eo8EhFfoxEbiFAxM5h9V/2S7nLD7bxxzXIRDteyHjHvLDHSri9LtJ2ND3t/ch6BOJF0rRDQ46RUEKPgMMmUUgfHK/NpIuXACKsPNoKEfI3/pntQg6Ej4/cKPBA8XnJ9gWNHy7pa/l2DzjXi1S3GB0KSVFeP+I+Itqh/mLh3SUfj+X2G37L6vhUMhY8S1lrgOoUImwVgLQ7HEBi7UEPLKL1X8Af1Kf30JPCHWw7HXCCuX2shp14lP26lvISiNy26UZ4xglt0UlMXxDQ8gfbzjX0YBu5P0R3b4gTJ2SQhbwOWSt+3iFJ1wAAAqhJREFUQuge8TLhWfkWCUUt+C7O/ru0zZS9FrdH+INx5EJR/rx2YN3NW4p6rPcOXsttE82r1Ve55HlOH5dMJSkBfzFDST4XLBmBic3DMWa5WCbdtSOHgKQETfiQ3Uff6HvwNL/dfdq+8Z2bz93/fD4isqTpQXVHeaOygqsi+LEAKbnbEL2HlIBHbf/Tq4JzFTSwuGfHvkm77bSXE+zHBb6m5C8iiMg6hyIye4yOiCTsm/U1ON8V1FcN1/c9FsgpWJoN2gH+JlsOJIS854XTCtRP1HWAkpDgQ/9278w5Yf3V4DVwp0kBOyD0A26BrBptVrOjOdSHI3mXXNunHkMUupomL9TzRAtoHHQ0GJzpS/IEzj9n7qKcFd233TfkaVj0/c6XJ+6PfyVrP23PSJ9HBP4YuNh+OpNFn7Q/Fqyt6OyOedJsPfpY1dAfFYSW5jz8X167Ex0MROE5/K9goTQiyk7gQSmRPlOHYLmhOkDaAyBZtBaxgFKhIC4BUp/QWAUTICmiZX1INCWxM1uNGYZapSYCjnpMjXmu4R1kiejDIpAoy72wx+1hq7+Vf450Ud3d1itsg6lH6gXST1go/SKSfy4V8a9gaYsmC/nJVvqBZH5YB1KP+AHpOO/arhMggVdul2731Jf8bbJcDz/ZpoNtlJmnKIouz6E5FwJt2P7UhHgcOynBnx2jRSTs+TWLGHO7Lm72l0gca72XSICHaPSjvBP0mUnZ+sx22ZQjo3xOa/SlJYX4Y/TE9lP1GUnZ0Te2y9ZKj7w0l/CvtTndbK+1GeEZ3+yDaBOphPfAf2Mk/C/aKqy2/WbYs20v2rpOhTZm7avT/7NX/61J3yw/AdAm16lIXka6vYEvI93Z9jLSNgkp7PXIKbF96ASl+Hrkaez1yFltr0e+PuT/AcuEG5vqCFxgAAAAAElFTkSuQmCC"
app.jinja_env.globals["spotify_logo"] = SPOTIFY_LOGO
THREECX_LOGO = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAG4AAAAoCAYAAAAfWs+KAAAACXBIWXMAAAAAAAAAAQCEeRdzAAAABGNJQ1ABBAABk7gAvQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAABGdBTUEAALGPC/xhBQAAEABJREFUeJzFXAlUW+eVBoQACSG0IQlJSCB2yWZfZMAsZt9sQCxCEggBNvtijBXw1h6nTTyZdOLJNmkdO2faNE0cZ/EkmdRp48R7HDs5ceJkOjnpTJamzcSTnrY5zmJINPc+JFeI956eADP3nP/Y4H+77/vv+t/fAQEMKESWlBCR29En2fLDh+TWB09E9//iomLro5flPYdPRxkPPCYoHdjFSSgsCQoThDOZb6UUFhrKUSqUGelpaV1lJSU/qq+te6S1xfh0m7H1OfwTfj5cVlK6Pz0t3ayIjl4fAkQ1F4vFCgIKCAwMJG1rQVRr475wf35PyE0qLpNZHvg3tePUV7F7Xndqdr/m1Ow679TMnvt7g98R/7brglM1evz3opqdd7AlcarVZo4dHBycnJRUtbmh4dC2vv4PpiYmv985tcPpbtPbp2429+8c0KDffH9v739UVVQe1Kg1+d7zymQyVZfF+gK0k1az+WWr2bKodVusL8VqYpeMWw2KUamyYN0T3mviProslpPdVuuL0XJ5HOMJWeEiflTrgSMLQF1wqm875VQ7XvXZNDNnCBBjpl++Flm8dQzO0oqZA2Fh52Rn9/faet5yAwJgOCfHxhk37I/jdkxud3Z2mF5KTEgs91xjQ75hfHang/h374bjhrYN/LdQKIxeMTMexOfzJXAA33e49uXdZh23OYsKCh2MJ2RHxasUg0ffRACYgEXabjvtjN17ySltv/uXQaHhwctlLiU5ubqvx/6mY8c0wYw/YFE1t1S2NDU/JhIKY9xrVVdW/QTXoRoDEnAKDhFrubx4EiiPQDxAeCjI1sN91NXUPsB4QhYvKlI5/NQVlLRlg+bREDxZ533HAoLYfjGGUlZTVf3PbimhkyJCTUIf/BnVp1tKHC71uX18gnT8zPROp6m94xX3mmhPOtranqf7mKCmH/aLEQqqra65n+qQ4PpmABXBZTxhVPs/PkYraaAyCRu3+6JTs+ciYd/UoB59gScsn9jLdA9CgUAKev8UGWMIwk4AA8EB1fkOgHt/VmamLS42tkSlVKUrFYr1arXaoEtNbS4u2rino7Xt38dHRv9MqCMv9YpzmE2dr3uuzePxBGAPr1IdFtwTqK8dfmC0hAx5+SMOisOB66L6RDXKeMJwXUUtnaQhYPDnN3Lbz06KG3bfL6513A128HHV+POfIJCUdhDUJjo3IfKUFF97EIvEqq19/VfJTj1KD0jUt02Nm/8VnIUCOJGMvC2wTfK83NxtqHI97SMBXIfpNe/+4IXqAOwvyOwoHhzYxxwcjHrGH9aDkhITK5AHMi2A602Mjv0FHJYM5jMGBgWAa/+qCxwS0C445fbDJ0OU63TeQ1nhkghB2egMAPTNAkgkUgdSLK6bOUi3hYiICGF/b98VBMj7Y+EJtZg6X1IplX4wtZjYbHYQODn24cHBT9wqGIC7QNZXn6prgH3MU31gAPZ/AeBUf9aXRknjR4eGP6M5EN+vX7eu1S+mQtWZGZqZs9+BZCwFDVx+jNuCwiJC6eaIyGzthL7fkQI/e9apHDz6XiCbQ+qooH0xtbW/4C1pboZKNhbvxj6rQZGRkdLWlpan0Gszm0wXqfoVFhRMU9khBB1U6jugWvlM1uRwOFx7t+0N70PpqYJLi0t2+82MoGxolty2gU2bOTsXpjVsYDKPzHzfc0T4QKYup1/+ki3WkMZ3G4uKZrw/EoKGaiUjLd3iN0MMCLzIgzZr11t0fRrrGx6mcyLAhh5ncqCMzc1PUjo98PumzVt+sSwmZOZ7nyf74IS02Q+fZTpPRL55Wyw4LWROjdrxyjxbmrBE1cplshRg4Lq3WsLTmZ2VZVsWQwxJr9PXs1gsSpcX1GswBMSn6CQFAvu76NbYVFp2O12YYevquhAK5PfmQX2xlYNP/A4kaylwAIKocvIOpnPx0hsaaYC7AcAleY+B03bU+zTizxWbyg/4zcwtIPBy5RCA/xeVp4l7RdtJNjYjPd28EJKQq9vhgcFPwCGLIRvrk4L5cgmR0tp7mXAiPFvc/qvOyELbKNO5IrKaLeTAnXbGbP/1NRZfJvbsr1Ao0kEdznlKGzLU09X9Bpz2VQl26SiII4wICuNzfPWL1WjyYG9fkjkr+DtoX2nj4gpd3Yn4S6NW5+KYqQm6MdqNy998GI/LN1iskQXd9iWtqNceqkpLZDpXlPHOR0lVLnir8p6HT3unwMDO3OstbXhCU5KSq5fNkB8EvGXLTAd/FRjsW1NlZmRYqOyUS3o+FolEhA0XgJQObt32e1opzcruveUMBjBIOvIymjo0M2dukHmmGIRHFvYsktywsDDuQP/WDz3dY2QUbMrZtcrKs+XJetybpOn2Q0z6+7JXsPcz4LWKOjtML9NlYKor6e3iahPp12RLtDGimpk7AbQ5sjgOHRzl6LMfsLhCnuc4CKILvU8keli52Tn9a8POAnAax6vfoZkQVU/f6as/Hihjc8sSm+wZ44HkfUqVBMdx7cZWRp7oqhJXV1EurJq6S1gxcZdkyw8PyW2HTqmnT35JlTkhrn1mzlznJpWVeM+1wWCY8jy9qPcnRse+kojFzK8xVkghC8DNE0lxsM2CkuFpX2OImMxGHZNR5UYxn9pn732bF84s9ltVEpaP7onb/87NPKVm9jxlqouQtJGn3+UklSwBDQkvPz1PLuYS7baed5imslaD/g7cKVce9oKTn2/2aXukUVLt6NDwn5heL2G/seGRa3K53Gfa75aQoHTQofF53UMAeV1cu2t/UFgEpWfY0db+G89Ti39vbTEeX0t+FgHn8n41s2dv8NLqm3yNTUxMLKfKO3pLIEjbXGpKSt1a8ERKzIAj2veqyRc/k3YePMaJ27Ak6xIEtqLbYr3oaeNQ+mqra46sJT9LgMM2g+Cd/5qTsLHY1/jcnNxBAO+GD2mbKzAYJtaCH0oSlA3Pxu57YyGFRTSam3FUPQvqdE5YPrbHc57ABeAuewMH4cGq3HcxJTLgiETE9G+/CFVn+Exos1isALBbV6lUJv5+a1//+xCTro2bTEV8g3UwZurEHyCY/hO0P4NanCPu5ojYjepa55Qzdt9lp7Bicp97HgTO0mk+4wncwq1007G15IdCVX7LTS2vYjK+YlP5HdM+bubx38H9/6dbzQstBbKC2UFcAY/FlwqgyULkScm89AajtP3uX6lnz85rqC5VCcP/2vecxOKbjkrzlqanPG0cgtht7bq8lq7yYuBgj2AG+AW2QSZjszIzu6nCArIwIDcnZ9ut5mdZxE2tqABp/JzqRpy40+s6dBIsHNF/U2npnZ6MoxEHz+uvAoFgVYty6MgTONed4d1MxsXFxm6A/S5JjNM5KKA2v06Ijyf1sP/fKXx9baNm13nSOzlC6mbOzIcq9Hrsq9fpjGTJ5XV6ffta7ReBg73NI2gy871PBwT5To8KhULF0MDAh1TpLLoamZHBoU8lYolmVTYfGMIJp2g8YMS/Cq1AVoCi/+eXMIajugnn55h6XR9ANT4yuihxi6qzzWh8flUYY0BsebIuFjSBYuCJN4PCRT6LebGICZyqM1TBN4Jjs3ZdoAzCYVxPV/fFMKAVb145dPQjaB97N9X4c5/w8ywD/s4nadz7U6raFcxOiComf+Tu225sfcHzI+D1B7rP6hh1zooZY0AhCn1WzPYXP2ZLk7VM+m9uaDxCVeiD2gLs9mPoaUK/R6j6OYh+W3654s2DdNxAF9i7oduPRUH+zieqmjqgIbvaQTsHHqikcd897r56nX6JukQgOztMJ1ahltYnsaUJCZyEwgImfYsKC3fSJZh7um2XQJCIK6LQ0NAQkLxzdBewJcXFjCvfSEk5+eL7Goo8Y7T9kXMBfmbqAewHidwlhcQJKyZ+7O6LBaZ9dvvb3nYBwTTkGxjfA95q0qXqNtMVD40MDf8xSiKJdXUnPphYJFINDwx+RGbzPIqD2pa9Kan1oROk1V0LLvLXIbKUJbfW1BQYEG0/co7Wxhksi9xtcEZayIqE4IN8lZiQULZsxhgQluKxgoJo7Tj00dOV68Hvv4F9lpKN1cZpC6i8T1c53l9VKlXmsjYvqhi/naoIFm2VZPMP/oXpXGGx+fmgZknv5NwXqmFaQ6H3uNYW41Pe4LnL4OK12qJlMeaD8vPyhi2mTtq7PyyQ3drb9y5lgSwRn+XS+gFYsEt3Abut388CWDeFxeUVUNVTEkHp7Ll5Xmarz3o/Fk/JV2x9/DKVtGFwrho7/mEQJ5LrPRZiN9nQtoElasV1yv+WkZ5u8psxCgphs1lVFZX/gCXoANxlSn7Ayehoa6ctSa+urLqHarwnVZaXH6CrFuv0t+R8YYchAdE0LvxCTvLM14KivvHAEC6pWgnT5hsUg0++SVqa56EmwXH5Mdl4JAxqJ4kajcUqyWUPnI31DQ9FRkZG+cfcYorXxhfbu22vud8VUBXEIlVVVlI+AiFK89raX0BwmRBmg9qMrc/QHQJ8T+A3Q7y0eqPPNwOgNpXDx94V183cw88zDfGyjf3CTaP75N0//S1I03eUwLukLWb7r/8nWKCQ0u0jOSmpHhi57l3n7/5YEMD+sbho4y6RUKhkyhve72m12lJQx8fcT5jcaoqsBB0pJzunn069gfp8LwLUqD/fODw8nNdn732LztPEdwX+zBmAToWs895nqNx4z8w5eozEQ8Y9rocfhJqlez+H6aRLzoicNiuTnSQkJJSPjYx8TsbglKscHWzfX/AE52bnDKljYgygalVcLlcAjc8L50VJpdKU1JSUzRXl5Xf12nquTE8uPK3yBoAMOLCpxZieoik//0IRrdD7+YEJkslkSaNDw59TOTqwp2/xfYFfkwbz5WLVyLPvrdYTq5s3A3svOUU1t/lVIymTypIhDjqPp5CqJA6BcD8KHBse+RJs5GfQPgUX/AvoM+frESTO3WW2XPJcVyIWq4cHh/5A82Hn9TrdZr8+rBfhmz+Y5wbVwcD3BXDw4hcNAgcqLj5xU4puXVtyqr4JwsXF5Q8hsiSNcujJKwtqk9krVErpnF2QTlHl9P7lMIhVxKUlJfvQOUEA6BK6hFvuaq6aRcq++HEQNLB1F8Gu3gy+IXgOxapiOlW2sbBo53J48aYNBsM4XTBvt/W8weVwbjpxKrUmPyM7rycnv2Aob0PRuG59+tL4j8WTREa13HEEHQ3NbubPiD0BQylTjR7/z/B19Ss6nUhw+hIb6up+BjHP39wvU5lm5b0lFA9Af2/f1eysrH7vglus33dMkX9M16PGwyvlxZPqa2sfpAIPNYmxufmoO1RJStE1KFQx+ZW1jffh3xNTdI2UE2ORj8z8wLNqxyvXbz7cJykOIuwegLzwgP+8E7zLtwUb+ydYXDGPcvJlkEQsiQPHZMbW1f06MPet56P9Ha4XqW6Jwp/dqhT7gPq51tLUfGydTt9M9j8w4IXo7pnZmy9cPdvMTgeq1NMwbNlPoskIb8XNps7f4MQRt4sAAADHSURBVPxk6+J+INwgLmDlCmV2Vq7BrorRZKRl5hh169JafC8gjY8HL7JP0nT7kWj74XMxUyc+AvCuA2gQaL96TTHw+BWp6Z5nhGWjuzjaDQWBbPKQYbUIXXCQwuT0tHQrxEc/AW/xuW6L9XVwQn4HjsMHoALfgw99vnlL0xMlxcX7wFOtgQCXMowQg10Dif55XU3to+CSL2p1NdhqD4tdFcqrTRDeyGGdQ7gO2doNdfWPRkkkRLmiJlZbmKpf3wQ2rgEOUfj/AYdYW2oLjP+rAAAAAElFTkSuQmCC"
app.jinja_env.globals["cat_logos"] = {
    "spotify": SPOTIFY_LOGO,
    "plusradio": LEAF_LOGO,
    "3cx": THREECX_LOGO,
}



# ──────────────────────────────────────────────
# CSS / Design — PLUS huisstijl
# ──────────────────────────────────────────────
from templates_py import (
    BASE_CSS, LAYOUT_TPL, LOGIN_TPL, NO_ACCESS_BODY, SSO_DONE_TPL,
    VOLUME_BODY, ONBOARDING_BODY, PRESETS_BODY, PRESET_EDIT_BODY, TTS_BODY, GEBRUIKERS_BODY,
    OIDC_BODY, BEHEER_BODY, PROFILE_BODY, LOGS_BODY, LOCKED_BODY,
)

# ──────────────────────────────────────────────
# Huisstijl / branding (white-label)
# ──────────────────────────────────────────────
# De app kan in verschillende winkelhuisstijlen draaien. Elk thema legt de
# kernpalet-kleuren, namen en het logo vast. De actieve keuze staat in
# settings["brand_theme"]; een per-thema geüpload logo staat in
# settings["brand_logo_overrides"]. Nieuw merk toevoegen (bijv. Jumbo) = één
# extra entry in BRAND_THEMES; de rest (CSS-vars, logo, context) volgt vanzelf.
#
# De PLUS-assets (wit logo, groen blad, wordmark) zijn al als jinja-globals
# gezet in templates_py.py; die hergebruiken we hier als het PLUS-thema.

# Officieel Albert Heijn-logo (door de winkel aangeleverd): de blauwe tegel met
# witte "ah". Zelfstandig gekleurd → op de gekleurde topbar tonen we 'm in een
# wit kader (logo_boxed).
_AH_LOGO_SVG = (
    '<svg width="24" height="24" fill="none" xmlns="http://www.w3.org/2000/svg">'
    '<path fill-rule="evenodd" clip-rule="evenodd" d="M23.218 11.471l-5.52-10.308a2.17 2.17 0 00-2.977-.887L4.618 5.924c-.454.26-.879.716-1.072 1.362l-2.711 9.44c-.325 1.13.31 2.314 1.42 2.645l15.925 4.542c1.108.332 2.27-.317 2.596-1.447l2.634-9.257c.171-.544.075-1.214-.192-1.738z" fill="#00ADE6"/>'
    '<path fill-rule="evenodd" clip-rule="evenodd" d="M13.379 6.035s-.009 4.29-.001 4.28l.202-.29c.841-1.207 1.657-2.321 3.092-2.321 1.716-.001 2.646 1.427 2.652 2.629v.532l-.008 7.163H17.39l-.009-7.284c0-1-.808-.998-.82-.998-.65 0-1.85 1.624-3.183 3.429v4.855l-1.947.002-.003-2.247s-1.288 2.248-3.217 2.25c-2.188 0-2.93-1.496-2.936-5.08-.003-3.415.484-5.242 2.83-5.244 1.783-.002 3.316 2.583 3.316 2.583V8.657l1.958-2.622zM8.132 9.74c-.896.002-.974.943-.971 3.212.003 2.27.126 3.155.969 3.155 1.144-.002 2.948-2.897 2.948-2.897s-1.79-3.47-2.946-3.47z" fill="#fff"/>'
    '</svg>'
)
_AH_LOGO_URI = "data:image/svg+xml;base64," + base64.b64encode(_AH_LOGO_SVG.encode("utf-8")).decode("ascii")

# Jumbo-woordmerk, geëxtraheerd uit het officiële Jumbo huisstijlhandboek
# (geel met zwarte slagschaduw). Geserveerd uit de static-map. Geel-op-geel zou
# onzichtbaar zijn → op de gele balk in een wit kader tonen (logo_boxed).
_JUMBO_LOGO_URI = "/static/jumbo_logo.png"

BRAND_THEMES = {
    "plus": {
        "key": "plus",
        "name": "PLUS",
        "radio_name": "PLUS Radio",
        "logo":     app.jinja_env.globals.get("logo"),          # wit volledig logo (topbar/login)
        "leaf":     app.jinja_env.globals.get("leaf_logo"),     # groen blad (kaart-chips, log)
        "wordmark": app.jinja_env.globals.get("plus_wordmark"), # inline svg, currentColor
        "logo_boxed": False,
        "colors": {
            "primary": "#80bd1d", "primary_dark": "#6aa018",
            "primary_glow": "rgba(128,189,29,0.30)",
            "heading": "#115013", "accent": "#227647",
            "accent_dim": "rgba(34,118,71,0.12)", "accent_soft": "#eaf4d8",
            "on_primary": "#ffffff",
            "btn_radius": "24px 24px 24px 4px",   # PLUS "spraakwolk"-knop
        },
    },
    "ah": {
        "key": "ah",
        "name": "Albert Heijn",
        "radio_name": "AH Radio",
        "logo":     _AH_LOGO_URI,
        "leaf":     _AH_LOGO_URI,
        "wordmark": _AH_LOGO_SVG,
        "logo_boxed": True,
        "colors": {
            "primary": "#00ade6", "primary_dark": "#007ea8",
            "primary_glow": "rgba(0,173,230,0.30)",
            "heading": "#00668d", "accent": "#ff7900",
            "accent_dim": "rgba(0,173,230,0.12)", "accent_soft": "#d9f2fb",
            "on_primary": "#ffffff",
            "btn_radius": "999px",                 # AH gebruikt volledige pills
        },
    },
    "jumbo": {
        "key": "jumbo",
        "name": "Jumbo",
        "radio_name": "Jumbo Radio",
        "logo":     _JUMBO_LOGO_URI,
        "leaf":     _JUMBO_LOGO_URI,
        "wordmark": '<img src="%s" alt="">' % _JUMBO_LOGO_URI,
        "logo_boxed": True,              # geel logo op gele balk → wit kader
        "colors": {
            # Jumbo geel standaard (C0 M28 Y100 K0) → ~#ffb800; koppen/tekst zwart.
            "primary": "#ffb800", "primary_dark": "#e0a200",
            "primary_glow": "rgba(255,184,0,0.30)",
            "heading": "#141414", "accent": "#141414",
            "accent_dim": "rgba(20,20,20,0.10)", "accent_soft": "#fff3cc",
            "on_primary": "#141414",               # donkere tekst op de gele balk
            "btn_radius": "999px",
        },
    },
}

def active_brand():
    """Het actieve thema als dict, met eventueel geüpload logo toegepast."""
    key = (settings.get("brand_theme") or "plus").strip().lower()
    theme = BRAND_THEMES.get(key) or BRAND_THEMES["plus"]
    b = dict(theme)
    b["colors"] = dict(theme["colors"])
    ov = (settings.get("brand_logo_overrides") or {}).get(key)
    if ov:
        b["logo"] = ov
        b["leaf"] = ov
        # lockup verwacht normaal een inline <svg>; bij een geüpload logo tonen we
        # een <img> (zie .pr-lockup img in branding_css).
        b["wordmark"] = '<img src="%s" alt="">' % ov
    return b

def branding_css(b=None):
    """<style>-blok dat de kern-CSS-vars naar het actieve thema overschrijft.
    Wordt ná BASE_CSS ingevoegd, dus deze :root-regels winnen."""
    b = b or active_brand()
    c = b["colors"]
    css = (
        '<style id="brandvars">:root{'
        f"--red:{c['primary']};--red-dark:{c['primary_dark']};--red-glow:{c['primary_glow']};"
        f"--gold:{c['accent']};--gold-dim:{c['accent_dim']};--green-dark:{c['heading']};"
        f"--btn-radius:{c['btn_radius']};--on-primary:{c['on_primary']};--accent-soft:{c['accent_soft']};"
        "}"
        # chip-selectie: gebruik de thema-tint i.p.v. de hardcoded groene
        f".chip:has(input:checked){{background:{c['accent_soft']}}}"
        ".pr-lockup img{height:.9em;width:auto;display:block}"
    )
    if b.get("logo_boxed"):
        # zelfstandig gekleurd tegel-logo leesbaar houden op de gekleurde balk
        css += ".topbar-logo img,.plus-login-header img{background:#fff;border-radius:8px;padding:4px;box-sizing:content-box}"
    css += "</style>"
    return css

@app.context_processor
def _brand_context():
    """Per-request de logo-/naam-globals overschrijven met het actieve thema."""
    b = active_brand()
    cats = dict(app.jinja_env.globals.get("cat_logos") or {})
    cats["plusradio"] = b["leaf"]
    return {
        "logo": b["logo"],
        "leaf_logo": b["leaf"],
        "plus_wordmark": b["wordmark"],
        "brand": b,
        "branding_style": Markup(branding_css(b)),
        "cat_logos": cats,
        "settings": settings,          # globaal beschikbaar in alle templates (ook sub-renders)
    }

# ──────────────────────────────────────────────
# Layout wrapper
# ──────────────────────────────────────────────

def render_layout(body_html, tab):
    ip = client_ip()
    pages, locks = effective_ui_for_ip(ip)
    vis = {
        "volume":  (bool(pages.get("volume"))  and _user_can_page("volume"))  or is_admin(),
        "presets": (bool(pages.get("presets")) and _user_can_page("presets")) or is_admin(),
        "tts":     (bool(pages.get("tts"))     and _user_can_page("tts"))     or is_admin(),
    }
    u = current_user()
    uname = current_username()
    display_name = u.get("display_name", uname) if u else ""
    return render_template_string(
        LAYOUT_TPL, body=body_html, tab=tab, admin=is_admin(),
        settings=settings, vis=vis,
        logged_in=is_logged_in(), display_name=display_name,
        my_username=uname, my_email=_user_email(uname, u),
        my_role=u.get("role", "user") if u else "user",
        my_source=u.get("source", "local") if u else "local",
        my_avatar=_avatar_url(uname) if uname else "",
        PRESETS_LOCK=locks.get("presets", False),
        TTS_LOCK=locks.get("tts", False),
        idle_redirect=bool(u.get("idle_redirect")) if u else False,
        idle_redirect_secs=int(u.get("idle_redirect_secs", 60)) if u else 60,
        sip_alert=bool(u.get("sip_alert")) if u else False,
    )

# ──────────────────────────────────────────────
# Login pagina
# ──────────────────────────────────────────────

def _build_oidc_providers() -> list:
    if not oidc_cfg.get("enabled") or not oidc_cfg.get("client_id"):
        return []
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    session["oidc_state"] = state
    session["oidc_nonce"] = nonce
    redirect_uri = oidc_cfg.get("redirect_uri") or url_for("sso_callback", _external=True)
    params = {
        "client_id":     oidc_cfg["client_id"],
        "response_type": "code",
        "scope":         oidc_cfg.get("scope", "openid email profile"),
        "redirect_uri":  redirect_uri,
        "state":         state,
        "nonce":         nonce,
    }
    meta     = _load_oidc_meta()
    auth_ep  = meta.get("authorization_endpoint", "")
    if not auth_ep:
        disc = oidc_cfg.get("discovery_url","")
        auth_ep = re.sub(r"/.well-known/openid-configuration.*$", "/authorize/", disc)
    if not auth_ep:
        return []
    return [{"name": oidc_cfg.get("provider_name","OpenID Connect"),
             "url":  auth_ep + "?" + urlencode(params)}]

def _default_warn():
    # Melding "standaardwachtwoord admin nog actief" is op verzoek verwijderd.
    return None

@app.route("/login", methods=["GET"])
def login_page():
    if is_logged_in():
        return redirect(url_for(_first_allowed_endpoint()))
    return render_template_string(LOGIN_TPL, error=None, warn=_default_warn(),
                                  prefill="", oidc_providers=_build_oidc_providers())

@app.route("/login", methods=["POST"])
def login_post():
    ip = client_ip()
    ua = (request.headers.get("User-Agent","") or "")[:120]
    if not _check_rate_limit(ip):
        log_action(f"Rate-limit: IP={ip} | gebruiker='{(request.form.get('username') or '').strip()}' | {ua[:60]}",
                   source="login")
        return render_template_string(LOGIN_TPL,
            error="Te veel mislukte pogingen. Wacht 5 minuten.",
            warn=None, prefill="", oidc_providers=_build_oidc_providers())
    username = (request.form.get("username") or "").strip().lower()
    password = (request.form.get("password") or "")
    if _verify_local_login(username, password):
        _clear_rate_limit(ip)
        session["username"] = username
        session.permanent   = True
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with _users_lock:
            if username in users:
                users[username]["last_login"]    = now_str
                users[username]["last_login_ip"] = ip
                users[username]["last_login_ua"] = ua[:80]
                _save_json(USERS_JSON, users)
        log_action(f"Ingelogd: {username} | IP: {ip} | {ua[:70]}", source="login")
        return redirect(url_for(_first_allowed_endpoint()))
    _record_failed_login(ip)
    attempts_used = len([t for t in _login_attempts.get(ip,[]) if time.time()-t < LOCKOUT_SECS])
    log_action(f"Mislukte login: gebruiker='{username}' | IP: {ip} | poging {attempts_used}/{MAX_ATTEMPTS} | {ua[:60]}",
               source="login")
    return render_template_string(LOGIN_TPL,
        error="Onjuiste gebruikersnaam of wachtwoord.",
        warn=_default_warn(), prefill=username,
        oidc_providers=_build_oidc_providers())

@app.route("/logout")
def logout():
    un = current_username()
    if un: log_action(f"Uitgelogd: {un} | IP: {client_ip()}", source="logout")
    session.clear()
    return redirect(url_for("login_page"))

# ──────────────────────────────────────────────
# Geen-toegang pagina (FIX voor de redirect-loop)
# Ingelogde gebruikers zonder enige paginarechten belandden voorheen in
# een oneindige /login → /login lus. Nu zien ze deze nette melding.
# ──────────────────────────────────────────────

@app.route("/geen-toegang")
def no_access_page():
    r = login_required()
    if r: return r
    u  = current_user()
    dn = u.get("display_name", current_username())
    return render_layout(render_template_string(NO_ACCESS_BODY, dn=dn), "")

# ──────────────────────────────────────────────
# OIDC callback
# ──────────────────────────────────────────────
@app.route("/auth/start")
def sso_popup_start():
    """
    Tussenstap voor de SSO-login: deze pagina draait op ons eigen
    domein (example.nl) en stuurt vervolgens direct door
    naar Authentik. Door de navigatie eerst hierheen te laten gaan in
    plaats van rechtstreeks naar het cross-origin Authentik-domein,
    behandelen WebKit/iOS deze als same-origin geopend, wat striktere
    iframe/popup-blokkades vermijdt.
    """
    providers = _build_oidc_providers()
    if not providers:
        return redirect(url_for("login_page"))
    return redirect(providers[0]["url"])

@app.route("/auth/callback")
def sso_callback():
    if request.args.get("error"):
        return redirect(url_for("login_page"))
    if request.args.get("state","") != session.get("oidc_state",""):
        log_action("SSO: ongeldige state", source="sso")
        return redirect(url_for("login_page"))
    code = request.args.get("code","")
    meta = _load_oidc_meta()
    token_url    = meta.get("token_endpoint","")
    userinfo_url = meta.get("userinfo_endpoint","")
    if not token_url:
        return redirect(url_for("login_page"))
    try:
        token_resp   = _oidc_post(token_url, {
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  oidc_cfg.get("redirect_uri", url_for("sso_callback", _external=True)),
            "client_id":     oidc_cfg["client_id"],
            "client_secret": oidc_cfg["client_secret"],
        })
        access_token = token_resp.get("access_token","")
        userinfo     = _oidc_get(userinfo_url, access_token)
        email  = (userinfo.get("email") or "").lower().strip()
        name   = userinfo.get("name") or userinfo.get("preferred_username") or email
        gclaim = oidc_cfg.get("group_claim", "groups")
        groups = userinfo.get(gclaim) or []
        if not email:
            return redirect(url_for("login_page"))
        _upsert_sso_user(email, name, groups)
        session["username"] = email
        session.permanent   = True
        log_action(f"SSO login: {email}", source="sso")
        return redirect(url_for(_first_allowed_endpoint()))
    except Exception as e:
        log_action(f"SSO callback fout: {e}", source="sso")
        return redirect(url_for("login_page"))

@app.route("/auth/logout")
def sso_logout():
    return redirect(url_for("logout"))

# ──────────────────────────────────────────────
# SSO done pagina — sluit popup en herlaadt iframe
# ──────────────────────────────────────────────

# ──────────────────────────────────────────────
# Manifest
# ──────────────────────────────────────────────
@app.route("/manifest.json")
def manifest():
    loc = (settings.get("location_name") or "").strip()
    name = f"PLUS {loc} Omroepsysteem" if loc else "PLUS Omroepsysteem"
    return jsonify({"name":name,"short_name":"PLUS","start_url":"/",
                    "display":"standalone","background_color":"#80bd1d","theme_color":"#80bd1d",
                    "icons":[{"src":"/static/icon.png","sizes":"312x312","type":"image/png","purpose":"any maskable"}]})

@app.route("/favicon.ico")
def favicon():
    icon_path = os.path.join(app.static_folder or os.path.join(HOME, "app", "static"), "icon.png")
    if os.path.exists(icon_path):
        return send_file(icon_path, mimetype="image/png")
    abort(404)

@app.route("/static/plus_logo.svg")
def serve_logo():
    logo_path = os.path.join(APP_DIR, "static", "plus_logo.svg")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            data = f.read()
        resp = make_response(data)
        resp.headers["Content-Type"] = "image/svg+xml"
        resp.headers["Cache-Control"] = "public, max-age=86400"
        return resp
    return "", 404

# ──────────────────────────────────────────────
# Hoofd pagina's
# ──────────────────────────────────────────────
@app.route("/")
def root():
    return redirect(url_for(_first_allowed_endpoint()))

# ─── Volume ───

@app.route("/volume")
def volume_page():
    r = login_required()
    if r: return r
    if not _user_can_page("volume") and not is_admin():
        return redirect(url_for(_first_allowed_endpoint()))
    return render_layout(render_template_string(VOLUME_BODY, vr=vol_rights_for()), "vol")


def _preset_cards_html():
    adm = is_admin(); ids = list_preset_ids(); cards = []
    for i in ids:
        flag_obj      = preset_flags.get(str(i)) or {}
        is_admin_only = bool(flag_obj.get("admin_only"))
        preroll_on    = bool(flag_obj.get("preroll_enabled", True))
        outro_on      = bool(flag_obj.get("outro_enabled", True))
        if (not adm) and is_admin_only: continue
        if not adm and not can_preset(i): continue
        nm       = preset_names.get(str(i), f"Preset {i}")
        gain_pct = max(0, min(200, int(preset_vols.get(str(i), DEFAULT_PRESET_GAIN))))
        icon     = (preset_icons.get(str(i)) or "").strip()
        # Icon HTML — toon boven de naam als er een icon ingesteld is
        icon_html = ""
        if icon:
            icon_html = f'''<div style="text-align:center;margin-bottom:8px">
              <span class="material-symbols-outlined" style="font-size:56px;color:#80bd1d">{Markup.escape(icon)}</span>
            </div>'''
        # Bepaal tegel-stijl: icon_only (geen label/knop-tekst) of normaal
        u_style = current_user().get("preset_style", "label")  # "icon_only" of "label"
        pencil = (f'<a class="tile-edit-btn" href="{url_for("edit_preset_page", preset_id=i)}" '
                  f'onclick="event.stopPropagation()" title="Preset bewerken"><span class="mi">edit</span></a>') if adm else ""
        if u_style == "icon_only" and icon:
            card = f"""<div class="card-item preset-tile-icon" onclick="playPreset({i})" title="{Markup.escape(nm)}"
              style="text-align:center;cursor:pointer;padding:20px 12px;transition:background .15s,transform .12s">
              {pencil}{icon_html}
              <div style="font-size:12px;color:var(--fg3);margin-top:4px;font-weight:600">{Markup.escape(nm)}</div>
            </div>"""
        else:
            card = f"""<div class="card-item" style="text-align:center">
              {pencil}<div class="label" style="text-align:left">Preset {i}</div>
              {icon_html}<div style="font-weight:700;margin-bottom:10px;text-align:left">{Markup.escape(nm)}</div>
              <button class="btn btn-primary" onclick="playPreset({i})"><span class="mi">play_arrow</span> Afspelen</button>
            </div>"""
        cards.append(card)
    if adm:
        cards.insert(0, f"""<div class="card-item new-preset-card">
          <div class="label" style="font-weight:700;margin-bottom:10px"><span class="mi">add</span> Nieuwe preset</div>
          <form method="post" action="{url_for('upload_preset_new')}" enctype="multipart/form-data">
            <div class="label">Naam</div><input class="input" name="name" placeholder="Naam" style="margin-bottom:6px">
            <div class="label">Bestand</div><input class="input" type="file" name="file" accept=".wav,.mp3,.m4a" required style="margin-bottom:8px">
            <button class="btn" type="submit"><span class="mi">add</span> Toevoegen</button>
          </form></div>""")
    return "".join(cards)


@app.route("/presets")
def presets_page():
    r = login_required()
    if r: return r
    ip = client_ip(); pages, locks = effective_ui_for_ip(ip)
    if not pages.get("presets",True) and not is_admin():
        return redirect(url_for(_first_allowed_endpoint()))
    if locks.get("presets") and not is_admin() and not session.get("presets_unlocked"):
        return redirect(url_for("locked_page"))
    meta = {i: {"name": preset_names.get(str(i), f"Preset {i}"),
                "icon": (preset_icons.get(str(i)) or "").strip()}
            for i in list_preset_ids()}
    return render_layout(render_template_string(
        PRESETS_BODY, cards=Markup(_preset_cards_html()), admin=is_admin(),
        preset_meta=Markup(json.dumps(meta, ensure_ascii=False)),
        show_popup=bool(settings.get("show_playing_popup", False))), "presets")

# ─── TTS ───
ALL_EDGE_VOICES = [
    {"value": "nl-NL-MaartenNeural", "label": "Maarten (man, NL)"},
    {"value": "nl-NL-ColetteNeural", "label": "Colette (vrouw, NL)"},
    {"value": "nl-BE-ArnaudNeural",  "label": "Arnaud (man, BE)"},
    {"value": "nl-BE-DenaNeural",    "label": "Dena (vrouw, BE)"},
]

def _tts_voice_options_html():
    u = current_user()
    allowed = u.get("tts_voices", "all") if u else "all"
    # allowed == "all" of een lijst van voice-values
    opts = ['<optgroup label="Edge TTS (Microsoft)">']
    for v in ALL_EDGE_VOICES:
        if allowed == "all" or v["value"] in (allowed or []):
            opts.append(f'<option value="{Markup.escape(v["value"])}">{Markup.escape(v["label"])}</option>')
    opts.append('</optgroup>')
    models = list_piper_models()
    if models:
        opts += ['<optgroup label="Piper (offline)">']
        for m in models:
            if allowed == "all" or m["name"] in (allowed or []):
                opts.append(f'<option value="{Markup.escape(m["name"])}">{Markup.escape(m["label"])}</option>')
        opts.append('</optgroup>')
    return "".join(opts)


@app.route("/tts")
def tts_page():
    r = login_required()
    if r: return r
    ip = client_ip(); pages, locks = effective_ui_for_ip(ip)
    if locks.get("tts") and not is_admin() and not session.get("tts_unlocked"):
        return redirect(url_for("locked_tts_page"))
    return render_layout(
        render_template_string(TTS_BODY, opts=Markup(_tts_voice_options_html()),
                               settings=settings, can_save_preset=can_save_preset_right(),
                               can_generate=can_generate_tts(),
                               outro_exists=os.path.exists(OUTRO_WAV),
                               show_popup=bool(settings.get("show_playing_popup", False)),
                               blocked_json=Markup(json.dumps(_blocked_words_list(), ensure_ascii=False)),
                               tts_prefill=settings.get("tts_prefill", ""),
                               quick_words=settings.get("tts_quick_words") or []),
        "tts",
    )

# ──────────────────────────────────────────────
# Gebruikers beheer
# ──────────────────────────────────────────────
def _gebruikers_table_html():
    def yn(v):
        return ('<span class="mi mi-sm" style="color:#4b7a12">check</span>'
                if v else '<span style="color:#c0c0c0">—</span>')
    cards = []
    for uname, u in sorted(users.items(), key=lambda kv: (kv[1].get("display_name") or kv[0]).lower()):
        role       = u.get("role", "user")
        presets    = u.get("can_presets", [])
        pstr       = "Alle" if presets == "all" else (", ".join(str(p) for p in presets) if presets else "Geen")
        source     = u.get("source", "local")
        groups     = _radio_groups(u.get("groups", []))   # alleen radio-* tonen
        last_login = u.get("last_login") or "—"
        dn         = u.get("display_name", uname)
        group_html = "".join(
            f'<span class="ugroup">{Markup.escape(g)}</span>' for g in groups)
        # zoektekst (naam + gebruikersnaam + groepen + rol) voor het filterveld
        search = Markup.escape(" ".join([dn, uname, role, source] + groups).lower())
        cards.append(f"""<div class="user-card" data-search="{search}">
          <div class="uc-head">
            <div style="min-width:0">
              <div class="uc-name">{Markup.escape(dn)}</div>
              <div class="uc-user mono">{Markup.escape(uname)}</div>
            </div>
            <span class="rbadge rbadge-{role}">{role}</span>
          </div>
          <div class="uc-meta">
            <span class="sbadge sbadge-{source}">{source}</span>{group_html}
          </div>
          <div class="uc-rights">
            <span>Volume {yn(u.get('can_volume'))}</span>
            <span>Text to Speech {yn(u.get('can_tts'))}</span>
            <span>Presets: <strong>{Markup.escape(pstr)}</strong></span>
          </div>
          <div class="uc-foot">
            <span class="help" style="font-size:12px">Laatste login: {last_login}</span>
            <div class="uc-actions">
              <a class="btn btn-sm btn-inline" href="{url_for('edit_user', uname=uname)}" style="width:auto"><span class="mi">edit</span> Bewerken</a>
              <form method="post" action="{url_for('delete_user', uname=uname)}" onsubmit="return confirm('Gebruiker {Markup.escape(uname)} verwijderen?')" style="margin:0">
                <button class="btn btn-sm btn-danger btn-inline" type="submit" title="Verwijderen" style="width:auto"><span class="mi">delete</span></button>
              </form>
            </div>
          </div>
        </div>""")
    return "".join(cards) or '<div class="help">Nog geen gebruikers.</div>'


@app.route("/gebruikers")
def gebruikers_page():
    admin_required()
    body = render_template_string(GEBRUIKERS_BODY,
                                  rows=Markup(_gebruikers_table_html()),
                                  create_err=None, create_ok=False)
    return render_layout(body, "gebruikers")

@app.route("/gebruikers/nieuw", methods=["POST"])
def create_user():
    admin_required()
    username     = (request.form.get("username") or "").strip().lower()
    display_name = (request.form.get("display_name") or "").strip()
    password     = (request.form.get("password") or "")
    role         = (request.form.get("role") or "user")
    err = None
    if not username:                    err = "Gebruikersnaam is verplicht."
    elif username in users:             err = f"Gebruikersnaam '{username}' bestaat al."
    elif len(password) < 6:             err = "Wachtwoord moet minimaal 6 tekens zijn."
    elif role not in DEFAULT_RIGHTS:    err = "Ongeldige rol."
    if err:
        body = render_template_string(GEBRUIKERS_BODY,
                                      rows=Markup(_gebruikers_table_html()),
                                      create_err=err, create_ok=False)
        return render_layout(body, "gebruikers")
    rights = dict(DEFAULT_RIGHTS[role])
    _create_local_user(username, password, display_name, role,
                        rights["can_volume"], rights["can_tts"], rights["can_presets"])
    log_action(f"Nieuwe gebruiker aangemaakt: {username} rol={role}", source="admin")
    return redirect(url_for("gebruikers_page"))

def _edit_user_html(uname, err=None, ok=None):
    u      = users.get(uname, {})
    role   = u.get("role", "user")
    allowed = u.get("can_presets", [])
    pid_list = list_preset_ids()
    voices_all = (u.get("tts_voices", "all") == "all")
    preset_chips = ""
    for pid in pid_list:
        nm      = preset_names.get(str(pid), f"Preset {pid}")
        checked = "checked" if (allowed == "all" or pid in (allowed or [])) else ""
        preset_chips += (f'<label class="chip"><input type="checkbox" name="preset_ids" '
                         f'value="{pid}" {checked}> {Markup.escape(nm)} '
                         f'<span class="mono" style="opacity:.6">#{pid}</span></label>')
    if not preset_chips:
        preset_chips = '<span class="help">Nog geen presets aangemaakt.</span>'
    voice_chips = "".join(
        f'<label class="chip"><input type="checkbox" name="tts_voice_ids" value="{Markup.escape(v["value"])}" '
        f'{"checked" if (voices_all or v["value"] in (u.get("tts_voices") or [])) else ""}> {Markup.escape(v["label"])}</label>'
        for v in ALL_EDGE_VOICES)
    # Fijnmazige volume-/Spotify-rechten (per subtab)
    _vr = vol_rights_for(u)
    def _ck(dom, cap):
        return "checked" if _vr.get(dom, {}).get(cap) else ""
    def _vol_card(dom, title, extra):
        d = _vr.get(dom, {})
        rows = (
            f'<label class="switch-row"><input type="checkbox" class="volcap" data-dom="{dom}" name="vol_{dom}_mute" value="1" {_ck(dom,"mute")}> <span>Muten (aan/uit)</span></label>'
            f'<label class="switch-row"><input type="checkbox" class="volcap volvol" data-dom="{dom}" name="vol_{dom}_volume" value="1" {_ck(dom,"volume")}> <span>Volume aanpassen</span></label>'
            f'<div class="vol-range" id="volRange_{dom}" style="display:flex;gap:10px;align-items:center;margin:2px 0 10px 34px;flex-wrap:wrap">'
            f'<span class="help" style="margin:0">Toegestaan bereik</span>'
            f'<input type="number" min="0" max="100" name="vol_{dom}_vmin" value="{d.get("vmin",0)}" style="width:72px" class="input"> '
            f'<span class="help" style="margin:0">t/m</span>'
            f'<input type="number" min="0" max="100" name="vol_{dom}_vmax" value="{d.get("vmax",100)}" style="width:72px" class="input"> '
            f'<span class="help" style="margin:0">%</span></div>')
        for cap, lbl in extra:
            rows += f'<label class="switch-row"><input type="checkbox" class="volcap" data-dom="{dom}" name="vol_{dom}_{cap}" value="1" {_ck(dom,cap)}> <span>{lbl}</span></label>'
        return (
            f'<div class="form-card voldom" data-dom="{dom}" style="margin-bottom:12px">'
            f'<label class="switch-row" style="font-weight:700"><input type="checkbox" class="volview" data-dom="{dom}" name="vol_{dom}_view" value="1" {_ck(dom,"view")}> <span>{title} — tab zien</span></label>'
            f'<div class="voldom-sub" data-dom="{dom}" style="margin-left:6px;padding-left:14px;border-left:2px solid var(--stroke-light);margin-top:8px">{rows}</div>'
            f'</div>')
    vol_rights_html = (
        _vol_card("omroep", "PLUS Radio", [("rca", "PLUS Radio aan/uit (RCA)"), ("nowplaying", "Huidige nummer + geschiedenis zien"), ("channel", "Kanaal wisselen (Plus Main / Plus Easy)"), ("commercial", "Commercials handmatig omroepen")]) +
        _vol_card("spotify", "Spotify", [("transport", "Speler bedienen (vorige / play / volgende / seek)"), ("restart", "Spotify herstarten"), ("history", "Afgespeelde nummers zien"), ("jam", "Jam meedoen tonen")]))

    source = u.get("source", "local")
    pw_block = (
        '<div class="form-card"><h3>Wachtwoord wijzigen</h3>'
        '<form method="post" action="' + url_for("change_password", uname=uname) + '">'
        '<div class="row"><div class="col"><div class="label">Nieuw wachtwoord (min. 6 tekens)</div>'
        '<input class="input" name="password" type="password" placeholder="Nieuw wachtwoord" required></div>'
        '<div class="col"><div class="label">Bevestiging</div>'
        '<input class="input" name="password2" type="password" placeholder="Herhaal wachtwoord" required></div></div>'
        '<div style="height:10px"></div>'
        '<button class="btn btn-inline" type="submit"><span class="mi">key</span> Wachtwoord wijzigen</button></form></div>'
        if source == "local" else
        '<div class="form-card"><div class="help">SSO-gebruiker: het wachtwoord wordt beheerd door de identity provider.</div></div>')
    return f"""
    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px">
      <a class="btn btn-inline btn-sm" href="{url_for('gebruikers_page')}" style="width:auto"><span class="mi">arrow_back</span> Terug</a>
      <h1 style="margin:0">Gebruiker bewerken</h1>
    </div>
    {'<div class="alert alert-err">' + err + '</div>' if err else ''}
    {'<div class="alert alert-ok">' + ok  + '</div>' if ok  else ''}
    <div style="max-width:720px">

      <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap">
        <strong style="font-size:16px;color:var(--green-dark)">{Markup.escape(u.get('display_name',uname))}</strong>
        <span class="mono" style="font-size:13px;color:var(--fg3)">{Markup.escape(uname)}</span>
        <span class="sbadge sbadge-{source}">{source}</span>
        <span class="rbadge rbadge-{role}">{role}</span>
      </div>

      <div class="subtabs" id="euTabs">
        <button type="button" class="subtab active" data-tab="account" onclick="euTab('account')"><span class="mi">person</span> Account</button>
        <button type="button" class="subtab" data-tab="rechten" onclick="euTab('rechten')"><span class="mi">verified_user</span> Rechten</button>
        <button type="button" class="subtab" data-tab="presets" onclick="euTab('presets')"><span class="mi">queue_music</span> Presets</button>
        <button type="button" class="subtab" data-tab="weergave" onclick="euTab('weergave')"><span class="mi">grid_view</span> Weergave</button>
        <button type="button" class="subtab" data-tab="ww" onclick="euTab('ww')"><span class="mi">key</span> Wachtwoord</button>
      </div>

      <form method="post" action="{url_for('save_user', uname=uname)}">
        <div class="subpanel active" data-panel="account">
          <div class="form-card">
            <h3>Account</h3>
            <div class="label">Weergavenaam</div>
            <input class="input" name="display_name" value="{Markup.escape(u.get('display_name',''))}" style="margin-bottom:14px">
            <div class="label">Rol</div>
            <select class="input" name="role" id="roleSel">
              {''.join(f'<option value="{r}" {"selected" if role==r else ""}>{r.capitalize()}</option>' for r in ["admin","operator","user","custom"])}
            </select>
            <div class="help" style="margin-top:6px">Admin/Operator/Gebruiker hebben vaste rechten. Kies <strong>Aangepast</strong> om per recht te bepalen (tabs Rechten &amp; Presets).</div>
          </div>
        </div>

        <div class="subpanel" data-panel="rechten">
          <div class="form-card" id="rightsCard">
            <h3>Rechten</h3>
            <div class="help" id="rightsHint" style="margin-bottom:10px">Deze rechten gelden bij rol <strong>Aangepast</strong>.</div>
            <div class="label" style="margin-bottom:6px">Volume &amp; Spotify</div>
            <div class="help" style="margin-bottom:10px">Per subtab bepalen wat deze gebruiker mag. Knoppen zonder recht worden verborgen én serverside geweigerd. Zet <strong>tab zien</strong> uit om een subtab volledig te verbergen.</div>
            {vol_rights_html}
            <div class="label" style="margin:14px 0 6px">Overig</div>
            <label class="switch-row"><input type="checkbox" name="can_tts" value="1" {"checked" if u.get("can_tts") else ""}> <span>Text to Speech gebruiken</span></label>
            <label class="switch-row" style="margin-bottom:12px"><input type="checkbox" name="can_tts_generate" value="1" {"checked" if u.get("can_tts_generate") else ""}> <span>Text to Speech genereren (download WAV/MP3)</span></label>
            <div class="label">Toegestane stemmen</div>
            <label class="switch-row"><input type="checkbox" name="tts_voices_all" id="voicesAll" value="1" {"checked" if voices_all else ""}> <span>Alle stemmen toestaan</span></label>
            <div class="chip-wrap" id="voiceChips">{voice_chips}</div>
          </div>
        </div>

        <div class="subpanel" data-panel="presets">
          <div class="form-card" id="presetsCard">
            <h3>Toegestane presets</h3>
            <div class="help" style="margin-bottom:10px">Geldt bij rol <strong>Aangepast</strong>.</div>
            <label class="switch-row"><input type="checkbox" name="presets_all" id="presetsAll" value="1" {"checked" if allowed=="all" else ""}> <span>Alle presets toestaan</span></label>
            <div class="chip-wrap" id="presetChips">{preset_chips}</div>
          </div>
        </div>

        <div class="subpanel" data-panel="weergave">
          <div class="form-card">
            <h3>Preset-weergave</h3>
            <div style="display:flex;gap:10px;flex-wrap:wrap">
              <label class="radio-card"><input type="radio" name="preset_style" value="label" {"checked" if u.get("preset_style","label")=="label" else ""}> <span><span class="mi mi-sm">play_arrow</span> Met knop &laquo;Afspelen&raquo;</span></label>
              <label class="radio-card"><input type="radio" name="preset_style" value="icon_only" {"checked" if u.get("preset_style","label")=="icon_only" else ""}> <span><span class="mi mi-sm">grid_view</span> Alleen icoon (klikbaar)</span></label>
            </div>
          </div>
          <div class="form-card">
            <h3>Inactiviteit</h3>
            <label class="switch-row"><input type="checkbox" name="idle_redirect" value="1" {"checked" if u.get("idle_redirect") else ""}> <span>Bij geen interactie automatisch terug naar de <strong>Muziek</strong>-pagina</span></label>
            <div class="help" style="margin:6px 0 10px">Handig voor een balie-tablet (bijv. servicebalie): staat de pagina te lang stil, dan gaat hij vanzelf terug naar Muziek. De timer reset bij elke aanraking, dus tijdens gebruik gebeurt er niets.</div>
            <div class="label">Na hoeveel seconden inactiviteit</div>
            <input class="input" type="number" name="idle_redirect_secs" min="15" max="3600" value="{int(u.get('idle_redirect_secs',60))}" style="max-width:140px">
          </div>
          <div class="form-card">
            <h3>Live omroep-melding</h3>
            <label class="switch-row"><input type="checkbox" name="sip_alert" value="1" {"checked" if u.get("sip_alert") else ""}> <span>Toon een <strong>volledige melding met stopknop</strong> zodra iemand live omroept via de telefoon</span></label>
            <div class="help" style="margin:6px 0 0">Handig aan de <strong>servicebalie</strong>: tijdens een live omroep (Beheer &rarr; Live omroep) verschijnt op elk scherm van deze gebruiker meteen wélk toestel omroept, met een knop om de omroep direct te stoppen.</div>
          </div>
        </div>

        <div id="euSave" style="margin-bottom:16px">
          <button class="btn btn-primary btn-inline" type="submit" style="min-width:160px"><span class="mi">save</span> Wijzigingen opslaan</button>
        </div>
      </form>

      <div class="subpanel" data-panel="ww">{pw_block}</div>
    </div>

    <script>
    (function(){{
      window.euTab=function(name){{
        document.querySelectorAll('#euTabs .subtab').forEach(function(b){{b.classList.toggle('active',b.dataset.tab===name);}});
        document.querySelectorAll('.subpanel').forEach(function(p){{p.classList.toggle('active',p.dataset.panel===name);}});
        var save=document.getElementById('euSave');
        if(save) save.style.display=(name==='ww')?'none':'block';
      }};
      var roleSel=document.getElementById('roleSel');
      function updRole(){{
        var custom=roleSel && roleSel.value==='custom';
        ['rightsCard','presetsCard'].forEach(function(id){{
          var el=document.getElementById(id); if(el) el.classList.toggle('dimmed',!custom);
        }});
      }}
      if(roleSel){{ roleSel.addEventListener('change',updRole); updRole(); }}
      function bindAll(allId, wrapId){{
        var a=document.getElementById(allId), w=document.getElementById(wrapId);
        if(!a||!w) return;
        function upd(){{ w.style.opacity=a.checked?'.45':'1'; w.querySelectorAll('input').forEach(function(i){{i.disabled=a.checked;}}); }}
        a.addEventListener('change',upd); upd();
      }}
      bindAll('voicesAll','voiceChips');
      bindAll('presetsAll','presetChips');
      // Volume-/Spotify-rechten: sub-blok volgt 'tab zien', bereik volgt 'volume'.
      document.querySelectorAll('.voldom').forEach(function(card){{
        var dom=card.dataset.dom;
        var view=card.querySelector('.volview');
        var sub=card.querySelector('.voldom-sub');
        var volChk=card.querySelector('.volvol');
        var range=card.querySelector('#volRange_'+dom);
        function updView(){{
          var on=view.checked;
          sub.style.opacity=on?'1':'.4';
          sub.querySelectorAll('input').forEach(function(i){{ if(i!==view) i.disabled=!on; }});
          if(on) updVol();
        }}
        function updVol(){{
          if(!range||!volChk) return;
          var on=volChk.checked && view.checked;
          range.style.display=on?'flex':'none';
        }}
        if(view){{ view.addEventListener('change',updView); }}
        if(volChk){{ volChk.addEventListener('change',updVol); }}
        updView();
      }});
    }})();
    </script>"""

@app.route("/gebruikers/<path:uname>/bewerken")
def edit_user(uname):
    admin_required()
    if uname not in users: abort(404)
    return render_layout(render_template_string(_edit_user_html(uname)), "gebruikers")

@app.route("/gebruikers/<path:uname>/opslaan", methods=["POST"])
def save_user(uname):
    admin_required()
    if uname not in users: abort(404)
    role         = (request.form.get("role") or "user").strip()
    display_name = (request.form.get("display_name") or "").strip()
    can_tts_f    = request.form.get("can_tts")    == "1"
    presets_all  = request.form.get("presets_all") == "1"
    preset_ids   = [int(x) for x in request.form.getlist("preset_ids") if x.isdigit()]
    preset_style      = request.form.get("preset_style") or "label"
    if preset_style not in ("label", "icon_only"): preset_style = "label"
    can_tts_generate  = request.form.get("can_tts_generate") == "1"
    tts_voices_all    = request.form.get("tts_voices_all") == "1"
    tts_voice_ids     = request.form.getlist("tts_voice_ids")
    # Fijnmazige volume-/Spotify-rechten uit het formulier lezen
    def _vform(dom):
        d = {cap: (request.form.get(f"vol_{dom}_{cap}") == "1") for cap in _VOL_CAPS[dom]}
        def _num(key, default):
            try:    return max(0, min(100, int(request.form.get(key, default))))
            except Exception: return default
        d["vmin"] = _num(f"vol_{dom}_vmin", 0)
        d["vmax"] = _num(f"vol_{dom}_vmax", 100)
        if d["vmax"] < d["vmin"]: d["vmax"] = d["vmin"]
        return d
    vol_rights = {dom: _vform(dom) for dom in VOL_DOMAINS}
    any_view = vol_rights["omroep"]["view"] or vol_rights["spotify"]["view"]
    if role == "admin":
        rights = dict(DEFAULT_RIGHTS["admin"])
    elif role == "operator":
        rights = dict(DEFAULT_RIGHTS["operator"])
    elif role == "custom":
        rights = {"role":"custom","can_volume":any_view,"can_tts":can_tts_f,
                  "can_presets":"all" if presets_all else preset_ids,
                  "vol_rights":vol_rights}
    else:
        rights = {"role":"user","can_volume":False,"can_tts":False,
                  "can_presets":"all" if presets_all else preset_ids}
    with _users_lock:
        users[uname].update(rights)
        if role != "custom":            # opgeslagen vol_rights gelden alleen bij 'custom'
            users[uname].pop("vol_rights", None)
        if display_name: users[uname]["display_name"] = display_name
        users[uname]["preset_style"]     = preset_style
        users[uname]["can_tts_generate"] = can_tts_generate
        users[uname]["tts_voices"]       = "all" if tts_voices_all else tts_voice_ids
        # Inactiviteit → terug naar de Muziek-pagina (per gebruiker aan/uit)
        users[uname]["idle_redirect"]    = request.form.get("idle_redirect") == "1"
        users[uname]["sip_alert"]        = request.form.get("sip_alert") == "1"
        try:    _irs = max(15, min(3600, int(request.form.get("idle_redirect_secs") or 60)))
        except Exception: _irs = 60
        users[uname]["idle_redirect_secs"] = _irs
        _save_json(USERS_JSON, users)
    log_action(f"Gebruiker bijgewerkt: {uname} rol={role} stijl={preset_style}", source="admin")
    return redirect(url_for("gebruikers_page"))

@app.route("/gebruikers/<path:uname>/wachtwoord", methods=["POST"])
def change_password(uname):
    admin_required()
    if uname not in users: abort(404)
    if users[uname].get("source") != "local": abort(400)
    pw  = (request.form.get("password")  or "")
    pw2 = (request.form.get("password2") or "")
    if pw != pw2:
        return render_layout(render_template_string(_edit_user_html(uname, err="Wachtwoorden komen niet overeen.")), "gebruikers")
    if len(pw) < 6:
        return render_layout(render_template_string(_edit_user_html(uname, err="Wachtwoord moet minimaal 6 tekens zijn.")), "gebruikers")
    with _users_lock:
        users[uname]["password_hash"] = generate_password_hash(pw)
        _save_json(USERS_JSON, users)
    log_action(f"Wachtwoord gewijzigd: {uname}", source="admin")
    return render_layout(render_template_string(_edit_user_html(uname, ok="Wachtwoord succesvol gewijzigd.")), "gebruikers")

# ──────────────────────────────────────────────
# Zelfbediening: eigen profiel (avatar, wachtwoord, rechten, eigen logs)
# ──────────────────────────────────────────────
def _user_email(uname, u=None):
    u = u if u is not None else users.get(uname, {})
    return (u.get("email") or (uname if "@" in (uname or "") else "")).strip()

def _avatar_base(uname):
    return re.sub(r"[^a-z0-9]", "_", (uname or "").lower())

def _avatar_file(uname):
    fn = (users.get(uname, {}) or {}).get("avatar")
    if fn:
        p = os.path.join(AVATARS, fn)
        if os.path.exists(p): return p
    return None

def _avatar_url(uname):
    return url_for("profile_photo", uname=uname) if _avatar_file(uname) else ""

app.jinja_env.globals["avatar_url_for"] = _avatar_url

@app.route("/profiel/foto/<path:uname>")
def profile_photo(uname):
    if not is_logged_in(): abort(401)
    p = _avatar_file(uname)
    if not p: abort(404)
    return send_file(p)

@app.route("/profiel")
def profile_page():
    r = login_required()
    if r: return r
    uname = current_username(); u = current_user()
    with _logs_lock:
        mine = [l for l in logs if l.get("user") == uname]
    mine = list(reversed(mine))[:150]
    log_rows = [{"time": it.get("time",""), "action": it.get("action",""),
                 "ip": it.get("ip","") or "—", "cat": it.get("cat","system"),
                 "label": _CAT_LABEL.get(it.get("cat","system"), it.get("cat",""))}
                for it in mine]
    ip = client_ip(); pages, _locks = effective_ui_for_ip(ip)
    is_adm = (u.get("role") == "admin")
    body = render_template_string(
        PROFILE_BODY, uname=uname, email=_user_email(uname, u),
        role=u.get("role","user"), acc_source=u.get("source","local"),
        display_name=u.get("display_name", uname), avatar_url=_avatar_url(uname),
        can_volume=is_adm or bool(u.get("can_volume")),
        can_tts=is_adm or bool(u.get("can_tts")),
        can_tts_generate=is_adm or bool(u.get("can_tts_generate")),
        presets_all=is_adm or (u.get("can_presets") == "all"),
        preset_list=[] if is_adm else [p for p in (u.get("can_presets") or []) if isinstance(p, int)],
        pages=pages, groups=_radio_groups(u.get("groups", [])),
        log_rows=log_rows, ok=request.args.get("ok"), err=request.args.get("err"))
    return render_layout(body, "profiel")

@app.route("/profiel/foto", methods=["POST"])
def profile_photo_upload():
    r = login_required()
    if r: return r
    uname = current_username()
    f = request.files.get("file")
    if not f or not f.filename:
        return redirect(url_for("profile_page", err="Geen bestand gekozen."))
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return redirect(url_for("profile_page", err="Kies een afbeelding (png/jpg/webp/gif)."))
    base = _avatar_base(uname); safe = base + ext
    try:
        for old in glob.glob(os.path.join(AVATARS, base + ".*")):
            try: os.remove(old)
            except Exception: pass
        f.save(os.path.join(AVATARS, safe))
        with _users_lock:
            if uname in users:
                users[uname]["avatar"] = safe; _save_json(USERS_JSON, users)
        log_action("Profielfoto bijgewerkt", source="login", user=uname)
    except Exception:
        return redirect(url_for("profile_page", err="Uploaden mislukt."))
    return redirect(url_for("profile_page", ok="Profielfoto opgeslagen."))

@app.route("/profiel/wachtwoord", methods=["POST"])
def profile_password():
    r = login_required()
    if r: return r
    uname = current_username(); u = users.get(uname, {})
    if u.get("source") != "local":
        return redirect(url_for("profile_page", err="SSO-account: wachtwoord wordt beheerd door de identity provider."))
    cur = request.form.get("current") or ""
    pw  = request.form.get("password") or ""
    pw2 = request.form.get("password2") or ""
    if not check_password_hash(u.get("password_hash", ""), cur):
        return redirect(url_for("profile_page", err="Huidig wachtwoord klopt niet."))
    if len(pw) < 6:
        return redirect(url_for("profile_page", err="Nieuw wachtwoord moet minstens 6 tekens zijn."))
    if pw != pw2:
        return redirect(url_for("profile_page", err="De nieuwe wachtwoorden komen niet overeen."))
    with _users_lock:
        users[uname]["password_hash"] = generate_password_hash(pw); _save_json(USERS_JSON, users)
    log_action("Eigen wachtwoord gewijzigd", source="login", user=uname)
    return redirect(url_for("profile_page", ok="Wachtwoord gewijzigd."))

@app.route("/gebruikers/<path:uname>/verwijderen", methods=["POST"])
def delete_user(uname):
    admin_required()
    admins = [n for n,u in users.items() if u.get("role")=="admin"]
    if uname == current_username() and len(admins) <= 1:
        return redirect(url_for("gebruikers_page"))
    with _users_lock:
        users.pop(uname, None)
        _save_json(USERS_JSON, users)
    log_action(f"Gebruiker verwijderd: {uname}", source="admin")
    return redirect(url_for("gebruikers_page"))

# ──────────────────────────────────────────────
# OIDC configuratiepagina
# ──────────────────────────────────────────────

def _redirect_uri_default() -> str:
    uri = url_for("sso_callback", _external=True)
    if uri.startswith("http://"):
        uri = "https://" + uri[7:]
    return uri

@app.route("/admin/oidc", methods=["GET"])
def oidc_page():
    admin_required()
    body = render_template_string(OIDC_BODY, cfg=oidc_cfg,
                                  redirect_uri_default=_redirect_uri_default(),
                                  meta={}, saved=False, test_result=None, test_ok=False)
    return render_layout(body, "oidc")

@app.route("/admin/oidc/opslaan", methods=["POST"])
def save_oidc():
    admin_required()
    global _oidc_meta_cache
    oidc_cfg.update({
        "enabled":       request.form.get("oidc_enabled") == "1",
        "provider_name": (request.form.get("provider_name") or "OIDC").strip(),
        "discovery_url": (request.form.get("discovery_url") or "").strip(),
        "client_id":     (request.form.get("client_id") or "").strip(),
        "client_secret": (request.form.get("client_secret") or "").strip(),
        "redirect_uri":  (request.form.get("redirect_uri") or "").strip(),
        "scope":         (request.form.get("scope") or "openid email profile").strip(),
        "group_claim":   (request.form.get("group_claim") or "groups").strip(),
        "group_admin":   (request.form.get("group_admin") or "").strip(),
        "group_operator":(request.form.get("group_operator") or "").strip(),
        "group_user":    (request.form.get("group_user") or "").strip(),
    })
    _save_json(OIDC_JSON, oidc_cfg)
    with _oidc_meta_lock: _oidc_meta_cache = {}
    log_action("OIDC-configuratie opgeslagen", source="admin")
    body = render_template_string(OIDC_BODY, cfg=oidc_cfg,
                                  redirect_uri_default=_redirect_uri_default(),
                                  meta={}, saved=True, test_result=None, test_ok=False)
    return render_layout(body, "oidc")

@app.route("/admin/oidc/test", methods=["POST"])
def test_oidc():
    admin_required()
    disc = (request.form.get("discovery_url") or "").strip()
    ok   = False; msg = ""
    if not disc:
        msg = "Geen discovery-URL ingevuld."
    else:
        try:
            req  = urllib.request.Request(disc, headers={
                "User-Agent": "OmroepwebOIDC/6.0 (discovery-test)",
                "Accept": "application/json",
            })
            resp = urllib.request.urlopen(req, timeout=8)
            data = json.loads(resp.read().decode())
            ep   = data.get("authorization_endpoint","")
            if ep:
                ok  = True
                msg = f"Discovery geslaagd. Authorization endpoint: {ep}"
            else:
                msg = "Discovery-URL bereikbaar maar bevat geen authorization_endpoint."
        except urllib.error.HTTPError as e:
            if e.code == 403:
                msg = f"HTTP 403 Forbidden — controleer of de provider publiek toegankelijk is."
            elif e.code == 404:
                msg = f"HTTP 404 — URL niet gevonden."
            else:
                msg = f"HTTP fout {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            msg = f"Verbindingsfout: {e.reason}"
        except Exception as e:
            msg = f"Fout: {e}"
    meta = _load_oidc_meta() if ok else {}
    body = render_template_string(OIDC_BODY, cfg=oidc_cfg,
                                  redirect_uri_default=_redirect_uri_default(),
                                  meta={k:v for k,v in meta.items() if not k.startswith("_")},
                                  saved=False, test_result=msg, test_ok=ok)
    return render_layout(body, "oidc")

# ──────────────────────────────────────────────
# Beheer pagina
# ──────────────────────────────────────────────
def _day_checks_html(prefix="days"):
    days   = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    labels = {"Mon":"Ma","Tue":"Di","Wed":"Wo","Thu":"Do","Fri":"Vr","Sat":"Za","Sun":"Zo"}
    return "<div class='days'>"+"".join(f"<label><input type='checkbox' name='{prefix}' value='{d}'>{labels[d]}</label>" for d in days)+"</div>"

def _schedule_rows_html():
    rows = []
    with _sched_lock:
        for s in _schedules:
            days    = ",".join(s.get("days") or ["All"])
            del_url = url_for("delete_schedule", sid=s["id"])
            if s.get("kind") == "interval":
                rows.append(f"<tr><td>{s['id']}</td><td>Interval</td><td>Preset {s.get('preset_id')}</td><td>elke {s.get('every_sec')}s</td><td>{days}</td><td>{s.get('start_hm','')}</td><td>{s.get('end_hm','')}</td><td>–</td><td><form method='post' action='{del_url}' onsubmit='return confirm(\"Verwijderen?\")'><button class='btn btn-sm btn-danger btn-inline' type='submit'><span class='mi'>close</span></button></form></td></tr>")
            else:
                rows.append(f"<tr><td>{s['id']}</td><td>Op tijden</td><td>Preset {s.get('preset_id')}</td><td>–</td><td>{days}</td><td>–</td><td>–</td><td>{','.join(s.get('times_hm') or [])}</td><td><form method='post' action='{del_url}' onsubmit='return confirm(\"Verwijderen?\")'><button class='btn btn-sm btn-danger btn-inline' type='submit'><span class='mi'>close</span></button></form></td></tr>")
    return "".join(rows) or "<tr><td colspan='9'>Geen schema's</td></tr>"


@app.route("/beheer")
def beheer_page():
    admin_required()
    pages = settings.get("pages") or {}
    class Pages:
        volume  = pages.get("volume",  True)
        presets = pages.get("presets", True)
        tts     = pages.get("tts",     True)
    brand_themes = []
    for _k, _t in BRAND_THEMES.items():
        _ov = (settings.get("brand_logo_overrides") or {}).get(_k)
        brand_themes.append({
            "key": _k, "name": _t["name"], "radio_name": _t["radio_name"],
            "primary": _t["colors"]["primary"], "heading": _t["colors"]["heading"],
            "accent": _t["colors"]["accent"], "accent_soft": _t["colors"]["accent_soft"],
            "on_primary": _t["colors"]["on_primary"],
            "logo": _ov or _t["logo"], "has_override": bool(_ov),
            "logo_boxed": bool(_t.get("logo_boxed")) or bool(_ov),
        })
    body = render_template_string(
        BEHEER_BODY,
        settings=type("S", (), {**settings, "pages": Pages()})(),
        brand_themes=brand_themes,
        active_theme=(settings.get("brand_theme") or "plus"),
        day_checks=Markup(_day_checks_html("days")),
        day_checks2=Markup(_day_checks_html("days")),
        sched_rows=Markup(_schedule_rows_html()),
        am_presets=Markup(json.dumps(
            [{"id": i, "name": (preset_names.get(str(i)) or f"Preset {i}")}
             for i in list_preset_ids()], ensure_ascii=False)),
        intro_exists=os.path.exists(INTRO_WAV),
        outro_exists=os.path.exists(OUTRO_WAV),
        ip_rules_json=json.dumps(settings.get("ip_rules") or {}, ensure_ascii=False),
        user_rules_json=json.dumps(settings.get("user_rules") or {}, ensure_ascii=False),
        blocked_words_json=Markup(json.dumps(_blocked_words_list(), ensure_ascii=False)),
        quick_words_json=Markup(json.dumps(settings.get("tts_quick_words") or [], ensure_ascii=False)),
        tts_prefill_val=settings.get("tts_prefill", ""),
        users_list=Markup(json.dumps(
            [{"u": un, "n": (u.get("display_name") or un)}
             for un, u in sorted(users.items(),
                                 key=lambda kv: (kv[1].get("display_name") or kv[0]).lower())
             if u.get("role") != "admin"],
            ensure_ascii=False)),
    )
    return render_layout(body, "beheer")

@app.route("/admin/save_settings", methods=["POST"])
def save_settings():
    admin_required()
    pages = settings.get("pages") or {}
    pages["volume"]  = request.form.get("page_volume")  == "1"
    pages["presets"] = request.form.get("page_presets") == "1"
    pages["tts"]     = request.form.get("page_tts")     == "1"
    try: pls = max(5, min(3600, int(request.form.get("presets_lock_seconds") or 30)))
    except: pls = 30
    try: tls = max(5, min(3600, int(request.form.get("tts_lock_seconds") or 30)))
    except: tls = 30
    try: tts_gain = max(0, min(200, int(request.form.get("tts_gain") or DEFAULT_TTS_GAIN)))
    except: tts_gain = DEFAULT_TTS_GAIN
    settings.update({
        "location_name":        (request.form.get("location_name") or "").strip(),
        "show_playing_popup":   request.form.get("show_playing_popup") == "1",
        "announcement_text":    (request.form.get("announcement_text") or "").strip(),
        "announcement_enabled": request.form.get("announcement_enabled") == "1",
        "announcement_id":      int(settings.get("announcement_id", 1)) + 1,
        "version":              (request.form.get("version") or settings.get("version") or "v6").strip(),
        "pages":                pages,
        "presets_lock_enabled": request.form.get("presets_lock_enabled") == "1",
        "presets_lock_seconds": pls,
        "tts_lock_enabled":     request.form.get("tts_lock_enabled") == "1",
        "tts_lock_seconds":     tls,
        "tts_engine":           (request.form.get("tts_engine") or "edge").strip().lower(),
        "tts_edge_voice":       (request.form.get("tts_edge_voice") or "nl-NL-MaartenNeural").strip(),
        "tts_preroll_enabled":  request.form.get("tts_preroll_enabled") == "1",
        "tts_outro_enabled":    request.form.get("tts_outro_enabled") == "1",
        "tts_gain":             tts_gain,
    })
    _save_json(SETTINGS_JSON, settings)
    log_action("Settings aangepast", source="admin")
    return redirect(url_for("beheer_page"))

@app.route("/admin/save_branding", methods=["POST"])
def save_branding():
    admin_required()
    theme = (request.form.get("brand_theme") or "plus").strip().lower()
    if theme not in BRAND_THEMES:
        theme = "plus"
    settings["brand_theme"] = theme
    overrides = dict(settings.get("brand_logo_overrides") or {})
    # 1) logo wissen voor dit thema
    if request.form.get("brand_logo_clear") == "1":
        overrides.pop(theme, None)
    # 2) geüpload logobestand → data-URI (max 512 kB)
    f = request.files.get("brand_logo_file")
    if f and f.filename:
        raw = f.read()
        if raw and len(raw) <= 512 * 1024:
            ext = (f.filename.rsplit(".", 1)[-1] if "." in f.filename else "").lower()
            mime = {"svg": "image/svg+xml", "png": "image/png", "jpg": "image/jpeg",
                    "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/png")
            overrides[theme] = "data:%s;base64,%s" % (mime, base64.b64encode(raw).decode("ascii"))
    # 3) losse logo-URL (alternatief voor upload)
    url = (request.form.get("brand_logo_url") or "").strip()
    if url:
        overrides[theme] = url
    settings["brand_logo_overrides"] = overrides
    _save_json(SETTINGS_JSON, settings)
    log_action("Huisstijl aangepast (%s)" % theme, source="admin")
    return redirect(url_for("beheer_page"))

# ──────────────────────────────────────────────
# Pi API endpoints
# ──────────────────────────────────────────────
@app.route("/api/pi/status")
def api_pi_status():
    if not is_logged_in(): abort(401)
    if PI_ENABLED or PI_LOCAL_GLR:
        vol, np = pi_snapshot()
    else:
        vol, np = -1, None
    commercial_next = bool(settings.get("commercial_replay") and _comm_pending.get("file")
                           and not _comm_playing)
    return jsonify(enabled=(PI_ENABLED or PI_LOCAL_GLR), volume=vol, host=PI_SSH_HOST,
                   nowplaying=np, control=spotify_control_on(),
                   explicit=explicit_blocked(), explicit_name=_explicit_name,
                   commercial_next=commercial_next,
                   jam_url=(pi_jam_join_url() if _vol_cap("spotify", "jam") else ""),
                   history=(_track_history_list() if _vol_cap("spotify", "history") else []))

# ── Spotify-transportbesturing (alleen in go-librespot-modus) ──
def _glr_post(path: str, body: str = "") -> bool:
    """POST naar de go-librespot besturings-API. V7: rechtstreeks lokaal
    (127.0.0.1:3678); anders via SSH-curl naar de Pi (rollback)."""
    if settings.get("demo_mode"):
        return False                      # demo: nooit echte Spotify aansturen
    if PI_LOCAL_GLR:
        try:
            data = body.encode("utf-8") if body else None
            req = urllib.request.Request(
                f"http://{VM_GLR_API}{path}", data=data, method="POST",
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=4) as r:
                return r.getcode() in (200, 204)
        except urllib.error.HTTPError as e:
            return e.code in (200, 204)
        except Exception:
            return False
    data = f"--data '{body}'" if body else ""
    rc, out = _pi_ssh(
        f"curl -s -m 4 -o /dev/null -w '%{{http_code}}' -X POST "
        f"-H 'Content-Type: application/json' {data} http://{GLR_API}{path}")
    code = (out or "").strip()[-3:]
    return code in ("200", "204")

def _spotify_control_guard():
    if not is_logged_in(): abort(401)
    if not _vol_cap("spotify", "transport"): abort(403)
    if not spotify_control_on(): abort(409)   # nog in raspotify-modus

# ──────────────────────────────────────────────
# Spotify Web API (huisaccount, Premium) — zoeken / afspelen / wachtrij
# OAuth Authorization Code. De callback loopt via de PUBLIEKE https-stream
# (stream.example.nl → nginx → deze app), want example.nl is
# intern/http en Spotify eist https. Daardoor kan de callback GEEN sessiecookie
# gebruiken → state wordt SERVERSIDE bijgehouden (zelfde proces bedient beide
# domeinen). Access-token wordt uit de refresh_token ververst + gecachet.
# ──────────────────────────────────────────────
SPOTIFY_SCOPES     = "user-read-playback-state user-modify-playback-state user-read-currently-playing streaming"
SPOTIFY_AUTH_URL   = "https://accounts.spotify.com/authorize"
SPOTIFY_TOK_URL    = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE   = "https://api.spotify.com/v1"
SPOTIFY_CALLBACK   = os.environ.get("SPOTIFY_CALLBACK", "")   # generiek; anders afgeleid van public_base_url
SPOTIFY_MARKET       = "NL"   # markt voor zoekresultaten (from_token vereist een scope die we niet vragen)
SPOTIFY_SEARCH_LIMIT = 10     # deze Spotify-app weigert limit > 10 (dev-mode): "Invalid limit" (400)

_sp_tok_lock  = threading.Lock()
_sp_tok_cache = {"access_token": "", "exp": 0.0}
_sp_dev_lock  = threading.Lock()
_sp_dev_cache = {"id": "", "ts": 0.0}
_sp_states    = {}          # state-token → aanmaaktijd (serverside, cross-domain)

def _sp_redirect_uri():
    base = (settings.get("public_base_url") or "").strip().rstrip("/")
    return ((spotify_cfg.get("redirect_uri") or "").strip()
            or SPOTIFY_CALLBACK
            or (base + "/spotify/callback" if base else ""))

def _sp_token(force=False):
    with _sp_tok_lock:
        if not force and _sp_tok_cache["access_token"] and time.time() < _sp_tok_cache["exp"]:
            return _sp_tok_cache["access_token"]
    cid = (spotify_cfg.get("client_id") or "").strip()
    sec = (spotify_cfg.get("client_secret") or "").strip()
    rt  = (spotify_cfg.get("refresh_token") or "").strip()
    if not (cid and sec and rt):
        return ""
    try:
        body = urlencode({"grant_type": "refresh_token", "refresh_token": rt}).encode()
        cred = base64.b64encode(f"{cid}:{sec}".encode()).decode()
        req  = urllib.request.Request(SPOTIFY_TOK_URL, data=body, headers={
            "Content-Type": "application/x-www-form-urlencoded", "Authorization": "Basic " + cred})
        d = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        tok = d.get("access_token", "")
        exp = time.time() + int(d.get("expires_in", 3600)) - 60
        if d.get("refresh_token"):
            spotify_cfg["refresh_token"] = d["refresh_token"]; _save_json(SPOTIFY_JSON, spotify_cfg)
        with _sp_tok_lock:
            _sp_tok_cache.update(access_token=tok, exp=exp)
        return tok
    except Exception as e:
        log_action(f"Spotify token-refresh mislukt: {e}", source="spotify"); return ""

def _sp_api(method, path, params=None, json_body=None, _retry=True):
    tok = _sp_token()
    if not tok:
        return 401, {}
    url = SPOTIFY_API_BASE + path
    if params:
        url += ("&" if "?" in url else "?") + urlencode(params)
    data = json.dumps(json_body).encode() if json_body is not None else None
    headers = {"Authorization": "Bearer " + tok}
    if data is not None: headers["Content-Type"] = "application/json"
    try:
        resp = urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=headers), timeout=10)
        raw = resp.read().decode() or ""
        return resp.getcode(), (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as e:
        if e.code == 401 and _retry:
            _sp_token(force=True); return _sp_api(method, path, params=params, json_body=json_body, _retry=False)
        try: body = json.loads(e.read().decode() or "{}")
        except Exception: body = {}
        return e.code, body
    except Exception:
        return 0, {}

def _sp_device_id(force=False):
    now = time.time()
    with _sp_dev_lock:
        if not force and _sp_dev_cache["id"] and now - _sp_dev_cache["ts"] < 30:
            return _sp_dev_cache["id"]
    local_name = local_id = ""
    try:
        s = json.loads(urllib.request.urlopen(f"http://{VM_GLR_API}/status", timeout=1.5).read().decode() or "{}")
        local_name = (s.get("device_name") or "").strip(); local_id = (s.get("device_id") or "").strip()
    except Exception: pass
    code, d = _sp_api("GET", "/me/player/devices")
    devs = (d or {}).get("devices", []) if code == 200 else []
    pick = ""
    for dev in devs:
        nm = dev.get("name") or ""
        _dm = (settings.get("spotify_device_name") or "").strip()
        if (_dm and _dm.lower() in nm.lower()) or (local_name and nm == local_name):
            pick = dev.get("id", ""); break
    if not pick and local_id:
        for dev in devs:
            if dev.get("id") == local_id: pick = dev.get("id", ""); break
    if not pick:
        for dev in devs:
            if dev.get("is_active"): pick = dev.get("id", ""); break
    if pick:
        with _sp_dev_lock: _sp_dev_cache.update(id=pick, ts=now)
    return pick

def _sp_simplify_track(t):
    if not t: return None
    imgs = ((t.get("album") or {}).get("images")) or []
    return {"uri": t.get("uri", ""), "name": t.get("name", ""),
            "artist": ", ".join(a.get("name", "") for a in (t.get("artists") or [])),
            "album": (t.get("album") or {}).get("name", ""),
            "cover": imgs[0]["url"] if imgs else "", "explicit": bool(t.get("explicit"))}

def _sp_web_guard():
    if not is_logged_in(): abort(401)
    if not _vol_cap("spotify", "transport"): abort(403)

@app.route("/spotify/auth")
def spotify_auth():
    admin_required()
    cid = (spotify_cfg.get("client_id") or "").strip()
    if not cid:
        return "Stel eerst de client_id/client_secret in.", 400
    state = secrets.token_urlsafe(16)
    now = time.time()
    _sp_states[state] = now
    for k, v in list(_sp_states.items()):     # opruimen (>10 min oud)
        if now - v > 600: _sp_states.pop(k, None)
    return redirect(SPOTIFY_AUTH_URL + "?" + urlencode({
        "client_id": cid, "response_type": "code", "redirect_uri": _sp_redirect_uri(),
        "scope": SPOTIFY_SCOPES, "state": state}))

@app.route("/spotify/callback")
def spotify_callback():
    # GEEN admin_required: komt via stream.example.nl zonder sessie. State
    # (serverside) is de beveiliging — alleen wie /spotify/auth startte heeft 'm.
    if request.args.get("error"):
        return f"Spotify weigerde de koppeling: {request.args.get('error')}", 400
    st = request.args.get("state", "")
    if st not in _sp_states:
        return "Ongeldige of verlopen state. Start opnieuw via Beheer.", 400
    _sp_states.pop(st, None)
    cid = (spotify_cfg.get("client_id") or "").strip()
    sec = (spotify_cfg.get("client_secret") or "").strip()
    try:
        body = urlencode({"grant_type": "authorization_code", "code": request.args.get("code", ""),
                          "redirect_uri": _sp_redirect_uri()}).encode()
        cred = base64.b64encode(f"{cid}:{sec}".encode()).decode()
        req  = urllib.request.Request(SPOTIFY_TOK_URL, data=body, headers={
            "Content-Type": "application/x-www-form-urlencoded", "Authorization": "Basic " + cred})
        d = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        rt = d.get("refresh_token", "")
        if not rt:
            return "Geen refresh_token ontvangen — verwijder de app-toestemming en probeer opnieuw.", 400
        spotify_cfg["refresh_token"] = rt; spotify_cfg["redirect_uri"] = _sp_redirect_uri()
        _save_json(SPOTIFY_JSON, spotify_cfg)
        with _sp_tok_lock:
            _sp_tok_cache.update(access_token=d.get("access_token", ""), exp=time.time() + int(d.get("expires_in", 3600)) - 60)
        log_action("Spotify Web API gekoppeld", source="spotify")
    except Exception as e:
        log_action(f"Spotify callback fout: {e}", source="spotify")
        return f"Koppelen mislukt: {e}", 400
    return ("<!doctype html><meta charset='utf-8'><body style='font-family:system-ui;padding:40px;color:#115013'>"
            "<h2>Spotify gekoppeld &#10004;</h2><p>Je kunt dit tabblad sluiten en terug naar het omroepsysteem.</p></body>")

@app.route("/api/spotify/admin/status")
def api_spotify_admin_status():
    admin_required()
    connected = bool((spotify_cfg.get("refresh_token") or "").strip())
    tok = _sp_token() if connected else ""
    return jsonify(
        has_creds=bool((spotify_cfg.get("client_id") or "").strip() and (spotify_cfg.get("client_secret") or "").strip()),
        client_id=(spotify_cfg.get("client_id") or ""), connected=connected, token_ok=bool(tok),
        device_id=(_sp_device_id() if tok else ""), redirect_uri=_sp_redirect_uri(),
        auth_url=url_for("spotify_auth"))

@app.route("/api/spotify/admin/save", methods=["POST"])
def api_spotify_admin_save():
    admin_required()
    j = request.get_json(silent=True) or {}
    cid = (j.get("client_id") or "").strip(); sec = (j.get("client_secret") or "").strip()
    if cid: spotify_cfg["client_id"] = cid
    if sec: spotify_cfg["client_secret"] = sec          # leeg = ongewijzigd
    _save_json(SPOTIFY_JSON, spotify_cfg)
    with _sp_tok_lock: _sp_tok_cache.update(access_token="", exp=0.0)
    log_action("Spotify Web API-config opgeslagen", source="spotify")
    return jsonify(ok=True)

@app.route("/api/spotify/search")
def api_spotify_search():
    _sp_web_guard()
    q = (request.args.get("q") or "").strip()
    if not q: return jsonify(results=[])
    # market=from_token vereist de user-read-private scope (die we niet vragen) → 403.
    # Vaste markt NL werkt zonder extra scope. LET OP: deze (dev-mode) Spotify-app
    # weigert een search-limit > 10 met "Invalid limit" (400) — dus max 10.
    code, d = _sp_api("GET", "/search", params={"q": q, "type": "track", "limit": SPOTIFY_SEARCH_LIMIT, "market": SPOTIFY_MARKET})
    if code != 200:
        return jsonify(results=[], error="spotify_api", code=code), (502 if code else 503)
    items = ((d.get("tracks") or {}).get("items")) or []
    return jsonify(results=[_sp_simplify_track(t) for t in items if t])

@app.route("/api/spotify/play", methods=["POST"])
def api_spotify_play():
    _sp_web_guard()
    if explicit_blocked(): return jsonify(ok=False, blocked=True)
    uri = ((request.get_json(silent=True) or {}).get("uri") or "").strip()
    if not uri: return jsonify(ok=False, error="no_uri"), 400
    # V7: rechtstreeks op de lokale go-librespot afspelen. Werkt ongeacht welk
    # account er cast (de huis-Web-API ziet het device niet als een gast host).
    if PI_LOCAL_GLR:
        ok = _glr_post("/player/play", json.dumps({"uri": uri}))
        log_action(f"Spotify: afspelen {uri}", source="spotify")
        return jsonify(ok=ok)
    dev = _sp_device_id()
    code, _ = _sp_api("PUT", "/me/player/play", params=({"device_id": dev} if dev else None), json_body={"uris": [uri]})
    log_action(f"Spotify Web: afspelen {uri}", source="spotify")
    return jsonify(ok=code in (200, 202, 204), code=code, device_id=dev)

# ── App-beheerde Spotify-wachtrij ──────────────────────────────────────────
# go-librespot geeft zijn eigen wachtrij niet vrij en de huis-Web-API ziet een
# gast-cast niet, dus houden we de "binnenkort"-lijst zélf bij: zichtbaar,
# herschikbaar en verwijderbaar. De app zet het bovenste nummer ~12s vóór het
# einde in de go-librespot-queue (speelt vóór autoplay); is de lijst leeg, dan
# zorgt autoplay dat Spotify vanzelf verder gaat.
SP_QUEUE_JSON  = os.path.join(APP_DIR, "sp_queue.json")
_sp_queue      = []
_sp_queue_lock = threading.Lock()
_sp_committed  = {"uri": ""}

def _sp_queue_load():
    global _sp_queue
    try:
        with open(SP_QUEUE_JSON) as f:
            d = json.load(f); _sp_queue = d if isinstance(d, list) else []
    except Exception:
        _sp_queue = []
_sp_queue_load()

def _sp_queue_save():
    try:
        with open(SP_QUEUE_JSON, "w") as f: json.dump(_sp_queue, f)
    except Exception: pass

def _sp_queue_public():
    with _sp_queue_lock:
        return [dict(t) for t in _sp_queue]

def _sp_queue_tick():
    """Houdt de app-wachtrij synchroon met wat er speelt en zorgt dat het
    volgende nummer op tijd gaat spelen. Alleen in local-modus."""
    if not PI_LOCAL_GLR:
        return
    d = _vm_glr_status(2.0)
    t = d.get("track") or {}
    cur = (t.get("uri") or "")
    with _sp_queue_lock:
        idx = next((i for i, x in enumerate(_sp_queue) if x.get("uri") == cur), -1)
        if idx >= 0:                                  # huidig nummer + alles ervóór weg
            del _sp_queue[:idx + 1]; _sp_queue_save()
            if _sp_committed["uri"] == cur: _sp_committed["uri"] = ""
        head = _sp_queue[0] if _sp_queue else None
        committed = _sp_committed["uri"]
    if not head:
        return
    if d.get("stopped"):                              # niets speelt → meteen starten
        if _glr_post("/player/play", json.dumps({"uri": head["uri"]})):
            with _sp_queue_lock: _sp_committed["uri"] = head["uri"]
        return
    try:    pos, dur = int(t.get("position") or 0), int(t.get("duration") or 0)
    except Exception: pos = dur = 0
    # bijna klaar → het volgende nummer in de native queue zetten (vóór autoplay)
    if dur > 0 and head["uri"] not in (committed, cur) and (dur - pos) <= 12000:
        if _glr_post("/player/add_to_queue", json.dumps({"uri": head["uri"]})):
            with _sp_queue_lock: _sp_committed["uri"] = head["uri"]

@app.route("/api/spotify/queue", methods=["POST"])
def api_spotify_queue_add():
    _sp_web_guard()
    j = request.get_json(silent=True) or {}
    uri = (j.get("uri") or "").strip()
    if not uri: return jsonify(ok=False, error="no_uri"), 400
    by = (current_user().get("display_name") or current_username() or "").strip()
    with _sp_queue_lock:
        _sp_queue.append({"uri": uri, "name": j.get("name", ""), "artist": j.get("artist", ""),
                          "cover": j.get("cover", ""), "explicit": bool(j.get("explicit")),
                          "added_by": by})
        _sp_queue_save()
    log_action(f"Spotify: in wachtrij {j.get('name', '') or uri}", source="spotify")
    return jsonify(ok=True, queue=_sp_queue_public())

@app.route("/api/spotify/queue", methods=["GET"])
def api_spotify_queue_get():
    _sp_web_guard()
    try: _sp_queue_tick()
    except Exception: pass
    np = _glr_np_from_status(_vm_glr_status(2.0)) if PI_LOCAL_GLR else None
    cur = None
    if np:
        cur = {"name": np.get("name", ""), "artist": np.get("artist", ""),
               "cover": np.get("cover", ""), "uri": np.get("uri", ""),
               "explicit": bool(np.get("is_explicit"))}
    return jsonify(current=cur, next=_sp_queue_public())

@app.route("/api/spotify/queue/reorder", methods=["POST"])
def api_spotify_queue_reorder():
    _sp_web_guard()
    order = (request.get_json(silent=True) or {}).get("order") or []
    with _sp_queue_lock:
        pos = {u: i for i, u in enumerate(order)}
        _sp_queue.sort(key=lambda t: pos.get(t.get("uri"), 1e9))
        _sp_queue_save()
    return jsonify(ok=True, queue=_sp_queue_public())

@app.route("/api/spotify/queue/remove", methods=["POST"])
def api_spotify_queue_remove():
    _sp_web_guard()
    uri = (request.get_json(silent=True) or {}).get("uri", "")
    with _sp_queue_lock:
        _sp_queue[:] = [t for t in _sp_queue if t.get("uri") != uri]; _sp_queue_save()
    return jsonify(ok=True, queue=_sp_queue_public())

@app.route("/api/spotify/queue/clear", methods=["POST"])
def api_spotify_queue_clear():
    _sp_web_guard()
    with _sp_queue_lock:
        _sp_queue[:] = []; _sp_queue_save()
    return jsonify(ok=True, queue=[])

@app.route("/api/pi/spotify/playpause", methods=["POST"])
def api_pi_sp_playpause():
    _spotify_control_guard()
    ok = _glr_post("/player/playpause")
    log_action("Spotify play/pause", source="admin")
    return jsonify(ok=ok)

@app.route("/api/pi/spotify/next", methods=["POST"])
def api_pi_sp_next():
    _spotify_control_guard()
    # Staat er iets in de app-wachtrij? Speel dáár het volgende nummer van, i.p.v.
    # go-librespot's eigen next (autoplay). Is de kop al in de native queue gezet
    # (commit vlak voor het einde), dan doet /player/next precies datzelfde nummer.
    head = committed = None
    if PI_LOCAL_GLR:
        with _sp_queue_lock:
            head = _sp_queue[0] if _sp_queue else None
            committed = _sp_committed.get("uri")
    if head and head.get("uri") != committed:
        ok = _glr_post("/player/play", json.dumps({"uri": head["uri"]}))
    else:
        ok = _glr_post("/player/next")
    log_action("Spotify volgende", source="admin")
    return jsonify(ok=ok)

@app.route("/api/pi/spotify/prev", methods=["POST"])
def api_pi_sp_prev():
    _spotify_control_guard()
    ok = _glr_post("/player/prev")
    log_action("Spotify vorige", source="admin")
    return jsonify(ok=ok)

@app.route("/api/pi/spotify/seek", methods=["POST"])
def api_pi_sp_seek():
    _spotify_control_guard()
    pos = max(0, int((request.get_json(silent=True) or {}).get("position_ms", 0)))
    ok = _glr_post("/player/seek", json.dumps({"position": pos}))
    return jsonify(ok=ok)

@app.route("/api/pi/volume", methods=["POST"])
def api_pi_volume():
    vr = _require_vol("spotify", "volume")
    if explicit_blocked():
        return jsonify(ok=False, blocked=True, reason="explicit")
    v = _clamp_vol("spotify", (request.get_json(silent=True) or {}).get("volume", 50), vr)
    pi_set_volume(v)
    log_action(f"Pi volume handmatig → {v}%", source="admin")
    return jsonify(ok=True)

@app.route("/api/pi/mute", methods=["POST"])
def api_pi_mute():
    _require_vol("spotify", "mute")
    if PI_LOCAL_GLR: _spot_hard_mute()
    else:            _pi_ssh(f"amixer sset {PI_MIXER} mute")
    log_action("Spotify gemutet", source="admin")
    return jsonify(ok=True)

@app.route("/api/pi/unmute", methods=["POST"])
def api_pi_unmute():
    _require_vol("spotify", "mute")
    if explicit_blocked():
        return jsonify(ok=False, blocked=True, reason="explicit")
    if PI_LOCAL_GLR: _spot_hard_unmute()
    else:            _pi_ssh(f"amixer sset {PI_MIXER} unmute")
    log_action("Spotify ongemutet", source="admin")
    return jsonify(ok=True)

@app.route("/api/pi/restart_raspotify", methods=["POST"])
def api_pi_restart_raspotify():
    _require_vol("spotify", "restart")
    ok = pi_raspotify_restart()
    return jsonify(ok=ok)

@app.route("/api/pi/spotify/set_mode", methods=["POST"])
def api_pi_sp_set_mode():
    admin_required()
    on = bool((request.get_json(silent=True) or {}).get("control"))
    settings["spotify_control"] = on
    _save_json(SETTINGS_JSON, settings)
    log_action(f"Spotify-bediening (go-librespot) → {'aan' if on else 'uit'}", source="admin")
    return jsonify(ok=True, control=on)

@app.route("/api/pi/save_duck", methods=["POST"])
def api_pi_save_duck():
    admin_required()
    v = max(0, min(100, int((request.get_json(silent=True) or {}).get("duck_level", PI_DUCK_DEFAULT))))
    settings["pi_duck_level"] = v
    _save_json(SETTINGS_JSON, settings)
    log_action(f"Pi duck-niveau ingesteld op {v}%", source="admin")
    return jsonify(ok=True)

@app.route("/admin/save_streamer", methods=["POST"])
def save_streamer():
    """PLUS Radio-streamer + Icecast-metadata instellen (voor multi-store deploy)."""
    admin_required()
    f = request.form
    settings["lisa_enabled"]            = f.get("lisa_enabled") == "1"
    settings["lisa_host"]               = (f.get("lisa_host") or "").strip()
    try:    settings["lisa_port"]       = max(1, min(65535, int(f.get("lisa_port") or 23)))
    except Exception: settings["lisa_port"] = 23
    # commercial_duck_spotify / commercial_replay: horen bij het Spotify-tabblad
    # (los opgeslagen via /api/spotify/comm_toggle), niet meer in dit formulier.
    settings["shazam_enabled"]          = f.get("shazam_enabled") == "1"
    settings["icecast_meta_enabled"]    = f.get("icecast_meta_enabled") == "1"
    settings["icecast_admin_url"]       = (f.get("icecast_admin_url") or "").strip()
    settings["icecast_mount"]           = (f.get("icecast_mount") or "/rca").strip()
    settings["icecast_admin_user"]      = (f.get("icecast_admin_user") or "admin").strip()
    pw = f.get("icecast_admin_pass")
    if pw:                              # leeg = wachtwoord ongewijzigd laten
        settings["icecast_admin_pass"] = pw
    # TuneIn now-playing
    settings["tunein_enabled"]     = f.get("tunein_enabled") == "1"
    settings["tunein_partner_id"]  = (f.get("tunein_partner_id") or "").strip()
    settings["tunein_station_id"]  = (f.get("tunein_station_id") or "").strip()
    tk = f.get("tunein_partner_key")
    if tk:                              # leeg = key ongewijzigd laten
        settings["tunein_partner_key"] = tk.strip()
    _save_json(SETTINGS_JSON, settings)
    _comm_ring_ensure()               # commercial-replay: opname aan/uit volgens setting
    with _lisa_conn.lock:              # verbinding resetten → nieuw IP/poort gaat meteen in
        _lisa_conn._drop()
    log_action("PLUS Radio-streamer instellingen aangepast", source="admin")
    return redirect(url_for("beheer_page"))

@app.route("/api/spotify/comm_toggle", methods=["POST"])
def api_spotify_comm_toggle():
    """Reclame-over-Spotify-schakelaars (duck + replay) los opslaan vanuit het
    Spotify-beheertabblad."""
    admin_required()
    data = request.get_json(silent=True) or {}
    key = data.get("key")
    if key not in ("commercial_duck_spotify", "commercial_replay"):
        return jsonify(ok=False), 400
    settings[key] = bool(data.get("on"))
    _save_json(SETTINGS_JSON, settings)
    if key == "commercial_replay":
        _comm_ring_ensure()           # ringbuffer-opname aan/uit volgens setting
    log_action("Spotify-reclame-instelling aangepast: " + key, source="admin")
    return jsonify(ok=True, on=settings[key])

# ── EQ (Spotify + PLUS Radio, 10-band) ──────────────────────────────────────
_EQ_DOMAIN = {"spot": ("spotify", "transport"), "bg": ("omroep", "channel")}

@app.route("/api/eq/<which>", methods=["GET", "POST"])
def api_eq(which):
    """10-band EQ lezen/zetten. spot = Spotify (live via alsaequal),
    bg = PLUS Radio (ffmpeg-EQ, RCA-pipe herstart bij wijziging)."""
    if which not in ("spot", "bg"):
        abort(404)
    if not is_logged_in():
        abort(401)
    if request.method == "GET":
        return jsonify(freqs=_EQ_FREQS, bands=_eq_get(which), flat=_EQ_FLAT)
    dom, cap = _EQ_DOMAIN[which]
    _require_vol(dom, cap)                       # bedienen (servicebalie = alleen kijken)
    data = request.get_json(silent=True) or {}
    key = "eq_spot" if which == "spot" else "eq_bg"
    if data.get("reset"):
        settings[key] = [_EQ_FLAT] * 10
    elif isinstance(data.get("bands"), list) and len(data["bands"]) == 10:
        settings[key] = [max(0, min(100, int(x))) for x in data["bands"]]
    elif "index" in data and "value" in data:
        b = _eq_get(which); i = int(data["index"])
        if 0 <= i < 10:
            b[i] = max(0, min(100, int(data["value"]))); settings[key] = b
    else:
        return jsonify(ok=False, error="geen geldige EQ-data"), 400
    _save_json(SETTINGS_JSON, settings)
    if which == "spot":
        _apply_eq_spot()                         # live
    elif rca_running():
        rca_stop(); rca_start()                  # PLUS Radio met nieuwe EQ herstarten
    return jsonify(ok=True, bands=_eq_get(which))

@app.route("/api/viz/rca")
def api_viz_rca():
    """Live spectrum van de PLUS Radio line-in voor de visualizer (on-demand)."""
    global _viz_last_poll, _viz_thread
    if not is_logged_in():
        abort(401)
    _viz_last_poll = time.time()
    with _viz_lock:
        if _viz_thread is None or not _viz_thread.is_alive():
            _viz_thread = threading.Thread(target=_viz_capture_loop, daemon=True)
            _viz_thread.start()
        lv = list(_viz_levels)
    live = (sum(lv) / len(lv) > 0.05) if lv else False
    return jsonify(bands=lv, live=live)

APP_GIT_DIR = os.path.dirname(os.path.abspath(__file__))

def _git(*args, timeout=30):
    return subprocess.run(["git", "-C", APP_GIT_DIR, *args],
                          capture_output=True, text=True, timeout=timeout)

def _onboarding_or_admin():
    """Toegang tijdens de eerste-keer-wizard (nog geen admin) óf voor een admin."""
    if not settings.get("onboarded") or is_admin():
        return
    abort(403)

def _alsa_devs(cmd):
    devs = []
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=8).stdout
    except Exception:
        return devs
    for line in out.splitlines():
        m = re.match(r"card (\d+): (\S+) \[([^\]]+)\], device (\d+): (.+?)\s*\[", line) \
            or re.match(r"card (\d+): (\S+) \[([^\]]+)\], device (\d+): (.+)", line)
        if m:
            devs.append({"card": int(m.group(1)), "id": m.group(2), "name": m.group(3).strip(),
                         "device": int(m.group(4)),
                         "hw": "plughw:%s,%s" % (m.group(1), m.group(4))})
    return devs

@app.route("/api/audio/devices")
def api_audio_devices():
    _onboarding_or_admin()
    return jsonify(playback=_alsa_devs(["aplay", "-l"]),
                   capture=_alsa_devs(["arecord", "-l"]),
                   have_np=_HAVE_NP)

_AUDIO_DEV_RE = re.compile(r"^(default|plughw:\d+,\d+|hw:\d+,\d+)$")

@app.route("/api/audio/test-out", methods=["POST"])
def api_audio_test_out():
    _onboarding_or_admin()
    dev = (request.get_json(silent=True) or {}).get("device", "default")
    if not _AUDIO_DEV_RE.match(dev):
        return jsonify(ok=False, error="ongeldig apparaat"), 400
    try:
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
             "-i", "sine=frequency=440:duration=1.3", "-af", "volume=0.35",
             "-ar", "48000", "-ac", "2", "-f", "alsa", dev],
            capture_output=True, text=True, timeout=8)
        if r.returncode != 0:
            return jsonify(ok=False, error=(r.stderr or "afspelen mislukt")[:200]), 500
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)[:200]), 500

@app.route("/api/audio/test-in", methods=["POST"])
def api_audio_test_in():
    _onboarding_or_admin()
    dev = (request.get_json(silent=True) or {}).get("device", "default")
    if not _AUDIO_DEV_RE.match(dev):
        return jsonify(ok=False, error="ongeldig apparaat"), 400
    try:
        p = subprocess.run(
            ["arecord", "-D", dev, "-f", "S16_LE", "-c", "1", "-r", "22050", "-d", "2", "-t", "raw"],
            capture_output=True, timeout=8)
        raw = p.stdout or b""
        if not raw:
            return jsonify(ok=False, error=(p.stderr.decode("utf-8", "replace") or "opname mislukt")[:200]), 500
        if _HAVE_NP:
            x = _np.frombuffer(raw, dtype='<i2').astype(_np.float32) / 32768.0
            rms = float(_np.sqrt(_np.mean(x ** 2))) if x.size else 0.0
            db = round(20 * _np.log10(rms + 1e-9), 1)
            return jsonify(ok=True, rms=round(rms, 4), db=db, signal=rms > 0.002)
        return jsonify(ok=True, rms=0, db=-99, signal=False)
    except Exception as e:
        return jsonify(ok=False, error=str(e)[:200]), 500

def _render_asound(play_card, cap_card):
    """Genereer een asound.conf voor de gekozen kaart(en): dmix-uitgang met de
    softvol-mixers BG/SPOT/PST (+ eq_spot voor de Spotify-EQ) en een dsnoop-line-in.
    Werkt zo op willekeurige hardware (USB-codec, Pi, laptop)."""
    pc, cc = int(play_card), int(cap_card)
    return f"""# Gegenereerd door de Omroepweb-onboarding.
pcm.hwout {{ type hw; card {pc}; device 0 }}
ctl.hwout {{ type hw; card {pc} }}
pcm.dmixed {{ type dmix; ipc_key 5678293; ipc_perm 0666;
  slave {{ pcm "hwout"; rate 48000; channels 2; period_size 1024; buffer_size 8192 }} }}
pcm.dac {{ type plug; slave.pcm "dmixed" }}
ctl.dac {{ type hw; card {pc} }}
pcm.!default {{ type plug; slave.pcm "dac" }}
ctl.!default {{ type hw; card {pc} }}
pcm.linein_shared {{ type dsnoop; ipc_key 5678294; ipc_perm 0666;
  slave {{ pcm "hw:{cc},0"; rate 48000; channels 2; period_size 1024; buffer_size 8192 }} }}
pcm.linein {{ type plug; slave.pcm "linein_shared" }}
pcm.bg  {{ type softvol; slave.pcm "dac"; control {{ name "BG";  card {pc} }}; min_dB -51.0; max_dB 0.0 }}
ctl.bg  {{ type hw; card {pc} }}
pcm.pst {{ type softvol; slave.pcm "dac"; control {{ name "PST"; card {pc} }}; min_dB -51.0; max_dB 0.0 }}
ctl.pst {{ type hw; card {pc} }}
pcm.eq_spot {{ type equal; controls "{HOME}/.eq_spot.bin"; slave.pcm "dac" }}
ctl.eq_spot {{ type equal; controls "{HOME}/.eq_spot.bin" }}
pcm.eq_spot_plug {{ type plug; slave.pcm "eq_spot" }}
pcm.spot {{ type softvol; slave.pcm "eq_spot_plug"; control {{ name "SPOT"; card {pc} }}; min_dB -51.0; max_dB 0.0 }}
ctl.spot {{ type hw; card {pc} }}
pcm.null_sink {{ type null }}
pcm.null_src {{ type plug; slave {{ pcm {{ type null }} }} }}
"""

@app.route("/api/audio/apply", methods=["POST"])
def api_audio_apply():
    """Stel de gekozen audio-apparaten in (schrijf asound.conf via de root-helper)."""
    _onboarding_or_admin()
    d = request.get_json(silent=True) or {}
    try:
        pc = int(d.get("play_card", 0)); cc = int(d.get("cap_card", pc))
    except Exception:
        return jsonify(ok=False, error="ongeldige kaart"), 400
    cfg = _render_asound(pc, cc)
    stage = "/tmp/omroepweb-asound.conf"
    try:
        with open(stage, "w") as f:
            f.write(cfg)
    except Exception as e:
        return jsonify(ok=False, error=str(e)[:150]), 500
    if not shutil.which("omroepweb-apply-audio"):
        return jsonify(ok=False, staged=True, config=cfg,
                       error="Helper niet geïnstalleerd; config staat klaar in " + stage), 200
    try:
        r = subprocess.run(["sudo", "-n", "omroepweb-apply-audio"], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return jsonify(ok=False, error=(r.stderr or "toepassen mislukt")[:200]), 500
    except Exception as e:
        return jsonify(ok=False, error=str(e)[:200]), 500
    log_action(f"Audio-apparaten ingesteld (uit=card{pc}, in=card{cc})", source="admin")
    return jsonify(ok=True)

# ── Onboarding (eerste-keer-wizard) ─────────────────────────────────────────
@app.route("/onboarding")
def onboarding_page():
    if settings.get("onboarded") and not is_admin():
        return redirect(url_for("_first_allowed_endpoint") if False else url_for("login_page"))
    has_admin = any(u.get("role") == "admin" for u in users.values())
    return render_layout(render_template_string(
        ONBOARDING_BODY, has_admin=has_admin,
        brands=[{"key": k, "name": v.get("name", k)} for k, v in BRAND_THEMES.items()]), "")

@app.route("/api/onboarding/admin", methods=["POST"])
def api_onboarding_admin():
    if settings.get("onboarded"):
        abort(403)
    if any(u.get("role") == "admin" for u in users.values()):
        return jsonify(ok=False, error="Er bestaat al een beheerder."), 400
    d = request.get_json(silent=True) or {}
    uname = (d.get("username") or "").strip().lower()
    pw = d.get("password") or ""
    disp = (d.get("display_name") or "").strip()
    if not uname or len(pw) < 6:
        return jsonify(ok=False, error="Gebruikersnaam + wachtwoord (min. 6 tekens) vereist."), 400
    r = dict(DEFAULT_RIGHTS.get("admin", {}))
    _create_local_user(uname, pw, disp, "admin",
                       r.get("can_volume", True), r.get("can_tts", True), r.get("can_presets", True))
    log_action("Onboarding: beheerder aangemaakt: " + uname, source="onboarding")
    return jsonify(ok=True)

@app.route("/api/onboarding/save", methods=["POST"])
def api_onboarding_save():
    _onboarding_or_admin()
    d = request.get_json(silent=True) or {}
    for key in ("location_name", "brand_theme", "lisa_host", "lisa_port", "lisa_enabled",
                "icecast_admin_url", "icecast_mount", "icecast_admin_user", "demo_mode"):
        if key in d:
            settings[key] = d[key]
    _save_json(SETTINGS_JSON, settings)
    return jsonify(ok=True)

@app.route("/api/onboarding/finish", methods=["POST"])
def api_onboarding_finish():
    _onboarding_or_admin()
    settings["onboarded"] = True
    _save_json(SETTINGS_JSON, settings)
    log_action("Onboarding afgerond", source="onboarding")
    return jsonify(ok=True)

@app.route("/api/system/version")
def api_system_version():
    """Huidige versie + of er een update klaarstaat op GitHub."""
    admin_required()
    cur = settings.get("version", "")
    latest = cur; avail = False; is_git = os.path.isdir(os.path.join(APP_GIT_DIR, ".git"))
    try:
        if is_git:
            _git("fetch", "--tags", "--quiet", "origin", timeout=20)
            r = _git("describe", "--tags", "--abbrev=0", "origin/main")
            if r.returncode == 0 and r.stdout.strip():
                latest = r.stdout.strip()
            loc = _git("rev-parse", "HEAD").stdout.strip()
            rem = _git("rev-parse", "origin/main").stdout.strip()
            avail = bool(loc and rem and loc != rem)
    except Exception:
        pass
    return jsonify(current=cur, latest=latest, update_available=avail, is_git=is_git)

@app.route("/api/system/update", methods=["POST"])
def api_system_update():
    """Laatste versie van GitHub binnenhalen + herstarten (losgekoppeld, overleeft
    de app-herstart). Zo hoeft een winkel na de eerste install nooit meer de console in."""
    admin_required()
    if not os.path.isdir(os.path.join(APP_GIT_DIR, ".git")):
        return jsonify(ok=False, error="Geen git-installatie — gebruik het install-commando."), 400
    log_action("Systeem-update gestart via Beheer", source="admin", user=current_username())
    if shutil.which("omroepweb-update"):
        cmd = "omroepweb-update"
    else:
        cmd = ("git -C {d} fetch --quiet origin && git -C {d} reset --hard --quiet origin/main && "
               "{d}/venv/bin/pip install -q -r {d}/requirements.txt && "
               "sudo systemctl restart omroepweb").format(d=APP_GIT_DIR)
    subprocess.Popen(["setsid", "bash", "-c", "sleep 1; " + cmd + " > /tmp/omroepweb-update.log 2>&1"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return jsonify(ok=True)

@app.route("/api/spotify/analysis")
def api_spotify_analysis():
    """Audio-analyse (beats + segment-loudness) van het nu spelende Spotify-nummer,
    voor de visualizer. Per track gecachet."""
    if not is_logged_in():
        abort(401)
    d = _vm_glr_status(1.0)
    t = d.get("track") or {}
    uri = t.get("uri") or ""
    tid = uri.split(":")[-1] if uri.startswith("spotify:track:") else ""
    if not tid:
        return jsonify(ok=False, beats=[], segments=[], duration=0)
    now = time.time()
    with _sp_analysis_lock:
        c = _sp_analysis_cache.get(tid)
        if c and now - c["ts"] < 3600:
            return jsonify(ok=True, **c["data"])
    out = {"beats": [], "segments": [], "duration": (t.get("duration") or 0) / 1000.0}
    try:
        a = _sp_api("GET", f"/audio-analysis/{tid}")
        if isinstance(a, dict):
            out["beats"] = [round(b.get("start", 0), 3) for b in (a.get("beats") or [])]
            out["segments"] = [[round(s.get("start", 0), 3), round(s.get("loudness_max", -60), 1)]
                               for s in (a.get("segments") or [])]
            tr = a.get("track") or {}
            if tr.get("duration"):
                out["duration"] = round(tr["duration"], 3)
    except Exception:
        pass
    with _sp_analysis_lock:
        _sp_analysis_cache[tid] = {"ts": now, "data": out}
    return jsonify(ok=True, **out)

@app.route("/api/stream/commercial_pct", methods=["POST"])
def api_stream_commercial_pct():
    """Commercial-volume op de online stream (% van normaal) — +/- vanuit beheer."""
    admin_required()
    body = request.get_json(silent=True) or {}
    if body.get("delta") is not None:
        pct = int(settings.get("commercial_stream_pct", 50)) + int(body["delta"])
    else:
        pct = int(body.get("pct", 50))
    pct = max(0, min(100, pct))
    settings["commercial_stream_pct"] = pct
    _save_json(SETTINGS_JSON, settings)
    # meteen toepassen als er nu een reclame speelt
    if _commercial_active:
        _stream_set_volume(STREAM_NORMAL_GAIN * pct / 100.0)
    log_action(f"Commercial-streamvolume → {pct}%", source="admin")
    return jsonify(ok=True, pct=pct)

@app.route("/admin/save_ip_rules", methods=["POST"])
def save_ip_rules():
    admin_required()
    def _clean(raw):
        obj = json.loads(raw) if (raw or "").strip() else {}
        if not isinstance(obj, dict): raise ValueError("geen object")
        out = {}
        for k, rule in obj.items():
            if not isinstance(k, str) or not isinstance(rule, dict): continue
            k = k.strip()
            if not k: continue
            p = rule.get("pages") or {}; l = rule.get("locks") or {}
            out[k] = {
                "pages": {"volume":  bool(p.get("volume", True)),
                          "presets": bool(p.get("presets", True)),
                          "tts":     bool(p.get("tts", True))},
                "locks": {"presets": bool(l.get("presets", False)),
                          "tts":     bool(l.get("tts", False))}
            }
        return out
    try:
        ip_clean   = _clean(request.form.get("ip_rules_json"))
        user_clean = _clean(request.form.get("user_rules_json"))
        # gebruiker-regels: alleen bestaande gebruikers bewaren
        user_clean = {u: r for u, r in user_clean.items() if u in users}
        settings["ip_rules"]   = ip_clean
        settings["user_rules"] = user_clean
        _save_json(SETTINGS_JSON, settings)
        log_action(f"Toegangsregels bijgewerkt ({len(ip_clean)} IP, {len(user_clean)} gebruiker)", source="admin")
    except Exception as e:
        log_action(f"Toegangsregels fout: {e}", source="admin")
    return redirect(url_for("beheer_page"))

@app.route("/admin/save_blocked_words", methods=["POST"])
def save_blocked_words():
    admin_required()
    raw = request.form.get("blocked_words_json") or "[]"
    try:
        arr = json.loads(raw)
        if not isinstance(arr, list): raise ValueError()
        seen, cleaned = set(), []
        for w in arr:
            w = str(w or "").strip().lower()
            if w and w not in seen:
                seen.add(w); cleaned.append(w)
        settings["blocked_words"] = cleaned
        _save_json(SETTINGS_JSON, settings)
        log_action(f"Woordfilter bijgewerkt ({len(cleaned)} woorden)", source="admin")
    except Exception as e:
        log_action(f"Woordfilter fout: {e}", source="admin")
    return redirect(url_for("beheer_page"))

@app.route("/admin/save_quick_words", methods=["POST"])
def save_quick_words():
    admin_required()
    prefill = request.form.get("tts_prefill")
    raw = request.form.get("quick_words_json") or "[]"
    try:
        arr = json.loads(raw)
        if not isinstance(arr, list): raise ValueError()
        seen, cleaned = set(), []
        for w in arr:
            w = str(w or "").strip()
            if w and w.lower() not in seen:
                seen.add(w.lower()); cleaned.append(w)      # hoofdletters behouden
        settings["tts_quick_words"] = cleaned
        if prefill is not None:
            settings["tts_prefill"] = prefill
        _save_json(SETTINGS_JSON, settings)
        log_action(f"Snel-invoegwoorden bijgewerkt ({len(cleaned)})", source="admin")
    except Exception as e:
        log_action(f"Snel-invoegwoorden fout: {e}", source="admin")
    return redirect(url_for("beheer_page"))

# ──────────────────────────────────────────────
# Logs
# ──────────────────────────────────────────────
_CAT_LABEL = {
    "login":    "Login",
    "logout":   "Logout",
    "sso":      "SSO",
    "preset":   "Preset",
    "tts":      "Text to Speech",
    "admin":    "Beheer",
    "system":   "Systeem",
    "schedule": "Schema",
    "ha":       "HA",
    "rca":      "RCA",
    "3cx":      "3CX",
    "volume":   "Volume",
    "spotify":  "Spotify",
    "plusradio": "PLUS Radio",
}


@app.route("/logs")
def logs_page():
    admin_required()
    try:
        from collections import Counter
        with _logs_lock:
            safe_logs = list(logs)
        for entry in safe_logs:
            if "cat" not in entry:
                src = (entry.get("ip") or "").lower()
                entry["cat"] = src if src in _CAT_LABEL else "system"
        reversed_logs = list(reversed(safe_logs))[:1000]
        counts = Counter(it.get("cat","system") for it in reversed_logs)
        stats  = [{"cat": k, "label": _CAT_LABEL.get(k, k), "count": counts[k]}
                  for k in sorted(counts.keys(), key=lambda x: -counts[x]) if counts[k] > 0]
        cats   = [(cat, _CAT_LABEL.get(cat, cat))
                  for cat in sorted(set(it.get("cat","system") for it in reversed_logs))]
        def _clean_ip(v):
            # Oude regels (vóór de fix) hadden de categorie in het IP-veld
            # staan i.p.v. een echt adres — die tonen we niet als "IP".
            return "" if (v or "").lower() in _CAT_LABEL else (v or "")
        rows   = [{"time":   it.get("time",""),
                   "action": it.get("action",""),
                   "user":   it.get("user","") or "—",
                   "ip":     _clean_ip(it.get("ip","")) or "—",
                   "cat":    it.get("cat","system"),
                   "label":  _CAT_LABEL.get(it.get("cat","system"), it.get("cat",""))}
                  for it in reversed_logs]
        body = render_template_string(LOGS_BODY, rows=rows, stats=stats, cats=cats)
        return render_layout(body, "logs")
    except Exception as e:
        import traceback
        err_html = f"<h1>Logboek</h1><div class='alert alert-err'>Fout bij laden logs: {Markup.escape(str(e))}</div><pre style='font-size:12px;color:var(--fg3)'>{Markup.escape(traceback.format_exc())}</pre>"
        return render_layout(err_html, "logs")

@app.route("/clear_logs", methods=["POST"])
def clear_logs():
    admin_required()
    with _logs_lock:
        logs.clear()
    _save_json(LOGS_JSON, [])
    return redirect(url_for("logs_page"))

# ──────────────────────────────────────────────
# Locked pages
# ──────────────────────────────────────────────

PRESET_CODE = os.environ.get("PRESET_CODE", "2546")
TTS_CODE    = os.environ.get("TTS_CODE",    "2546")

@app.route("/locked")
def locked_page():
    return render_layout(render_template_string(
        LOCKED_BODY, title="Presets vergrendeld",
        unlock_url=url_for("unlock_presets"), dest_url=url_for("presets_page"), section="presets"), "presets")

@app.route("/locked_tts")
def locked_tts_page():
    return render_layout(render_template_string(
        LOCKED_BODY, title="TTS vergrendeld",
        unlock_url=url_for("unlock_tts"), dest_url=url_for("tts_page"), section="tts"), "tts")

@app.route("/unlock", methods=["POST"])
def unlock_presets():
    code = (request.get_json(silent=True) or {}).get("code","").strip()
    if code == PRESET_CODE: session["presets_unlocked"] = True; return jsonify(ok=True)
    return jsonify(ok=False)

@app.route("/unlock_tts", methods=["POST"])
def unlock_tts():
    code = (request.get_json(silent=True) or {}).get("code","").strip()
    if code == TTS_CODE: session["tts_unlocked"] = True; return jsonify(ok=True)
    return jsonify(ok=False)

# ──────────────────────────────────────────────
# API endpoints — algemeen
# ──────────────────────────────────────────────
@app.route("/events")
def events():
    # SSE vereist nu login: elke open verbinding houdt een serverthread
    # vast, dus anonieme clients mogen die niet onbeperkt claimen.
    if not is_logged_in():
        abort(401)
    def gen():
        try:
            while True: yield f"data: {json.dumps(current_state())}\n\n"; time.sleep(1)
        except GeneratorExit: pass
    return Response(gen(), mimetype="text/event-stream")

@app.route("/api/settings")
def api_settings():
    resp = make_response(jsonify({
        "announcement_enabled": bool(settings.get("announcement_enabled")),
        "announcement_text":    settings.get("announcement_text") or "",
        "announcement_id":      int(settings.get("announcement_id") or 1),
        "version":              settings.get("version") or "",
    }))
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp

@app.route("/api/status")
def api_status(): return jsonify(current_state())

@app.route("/api/plusradio")
def api_plusradio():
    """Huidige PLUS Radio-titel + afgespeelde nummers (achter het nowplaying-recht)."""
    if not is_logged_in(): abort(401)
    if not _vol_cap("omroep", "nowplaying"):
        return jsonify(title="", history=[], channel=0)
    # Commercials in de geschiedenis het PLUS-blad als hoes geven.
    hist = []
    for h in _lisa_history_list():
        h2 = dict(h)
        if _title_is_commercial(h.get("title", "")) and not h2.get("cover"):
            h2["cover"] = LEAF_LOGO
        hist.append(h2)
    return jsonify(title=lisa_current_title(), history=hist,
                   channel=lisa_current_channel(), **_pr_enrich_fields())

@app.route("/api/nowplaying")
def api_nowplaying():
    """Publiek now-playing-JSON voor een externe webplayer (bijv. example.nl/radio/).
    Bevat titel/artiest/album/cover zodat die pagina het compleet kan tonen — iets
    wat NIET via de Icecast-streammetadata kan (die kent alleen één titelregel).
    CORS open zodat een andere (sub)domein-pagina het mag ophalen."""
    resp = jsonify(_nowplaying_dict())
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Cache-Control"] = "no-store"
    return resp

@app.route("/api/plusradio/channel", methods=["POST"])
def api_plusradio_channel():
    """Wissel PLUS Radio-kanaal (1=Plus Main, 2=Plus Easy). Achter het channel-recht."""
    if not is_logged_in(): abort(401)
    if not _vol_cap("omroep", "channel"): abort(403)
    n = 2 if int((request.get_json(silent=True) or {}).get("channel", 1)) == 2 else 1
    ok = lisa_set_channel(n)
    log_action(f"PLUS Radio kanaal → {'Plus Easy' if n==2 else 'Plus Main'}",
               source="plusradio", user=current_username())
    return jsonify(ok=ok, channel=lisa_current_channel())

@app.route("/api/plusradio/restart", methods=["POST"])
def api_plusradio_restart():
    """Herstart de Streamit-streamer (bewuste, verstorende actie → alleen admin).
    Het 'restart'-commando verbreekt de telnet-sessie; de playlist begint na de
    reboot opnieuw vanaf het begin. De verbinding reconnect vanzelf bij de poll."""
    admin_required()
    try:
        _lisa_conn.send("restart", wait=1.0)
    except Exception:
        pass
    try:
        _lisa_conn._drop()               # forceer nette reconnect na de reboot
    except Exception:
        pass
    with _lisa_com_lock:                 # commercial-cache leegmaken (kaart herlaadt)
        _lisa_com_cache.update(ts=0.0)
    log_action("PLUS Radio streamer herstart — playlist begint opnieuw",
               source="plusradio", user=current_username())
    return jsonify(ok=True)

@app.route("/api/commercials/recorded")
def api_commercials_recorded():
    """Lijst van de laatst opgenomen reclames (mp3) voor download door de beheerder."""
    admin_required()
    items = []
    try:
        for p in sorted(glob.glob(os.path.join(COMM_ARCHIVE_DIR, "reclame_*.mp3")), reverse=True):
            try: st = os.stat(p)
            except Exception: continue
            name = os.path.basename(p)
            items.append({
                "name": name,
                "size_kb": int(st.st_size / 1024),
                "mtime": st.st_mtime,
                "when": time.strftime("%d-%m-%Y %H:%M", time.localtime(st.st_mtime)),
                "url": url_for("download_recorded_commercial", name=name),
            })
    except Exception:
        pass
    return jsonify(items=items)

@app.route("/commercials/recorded/<name>")
def download_recorded_commercial(name):
    """Download één opgenomen reclame (alleen admin, alleen uit het archief)."""
    admin_required()
    safe = os.path.basename(name)
    if not (safe.startswith("reclame_") and safe.endswith(".mp3")):
        abort(404)
    p = os.path.join(COMM_ARCHIVE_DIR, safe)
    if not os.path.exists(p):
        abort(404)
    return send_file(p, as_attachment=True, download_name=safe, mimetype="audio/mpeg")

# Beheer-console: commando's naar de Lisa sturen (alleen admins).
_LISA_BLOCKED_CMDS = ("loglev", "reset", "restart", "quit", "ereset", "eeprom")
@app.route("/api/lisa/command", methods=["POST"])
def api_lisa_command():
    admin_required()
    cmd = ((request.get_json(silent=True) or {}).get("cmd") or "").strip()
    if not cmd:
        return jsonify(ok=False, resp="", history=_lisa_conn.history[-40:])
    # Commando's die de telnet-sessie verbreken of het apparaat resetten weren.
    if cmd.split()[0].lower() in _LISA_BLOCKED_CMDS:
        return jsonify(ok=False, resp=f"'{cmd.split()[0]}' is geblokkeerd (zou de verbinding/het apparaat verstoren).",
                       history=_lisa_conn.history[-40:])
    resp = _lisa_conn.send(cmd, wait=2.5, log=True)
    log_action(f"Lisa-commando: {cmd}", source="plusradio", user=current_username())
    return jsonify(ok=True, resp=resp, history=_lisa_conn.history[-40:])

@app.route("/api/set_volume", methods=["POST"])
def api_set_volume():
    global _bg_vol_before
    vr = _require_vol("omroep", "volume")
    v = _clamp_vol("omroep", (request.get_json(silent=True) or {}).get("volume", 0), vr)
    global _bg_muted
    with _bg_lock:
        changed = (v != _bg_vol_before) or _bg_muted
        _bg_vol_before = v
        _bg_muted = False          # elke volume-wijziging heft mute op
        set_bg_volume(v)
    _save_bg_volume(v)             # onthouden voor herstel na herstart
    if changed:
        log_action(f"PLUS Radio volume → {v}%", source="volume")
    return jsonify(ok=True, volume=v, muted=False)

@app.route("/api/step", methods=["POST"])
def api_step():
    global _bg_vol_before, _bg_muted
    vr = _require_vol("omroep", "volume")
    d = int((request.get_json(silent=True) or {}).get("delta", 0))
    with _bg_lock:
        # Baseer op de opgeslagen doelwaarde (niet op de mixer, die bij mute 0
        # leest) — voorkomt de 0%-bug. Elke +/- heft mute op. Klem op bereik.
        nv = _clamp_vol("omroep", _bg_vol_before + d, vr)
        _bg_vol_before = nv
        _bg_muted = False
        set_bg_volume(nv)
    _save_bg_volume(nv)            # onthouden voor herstel na herstart
    log_action(f"PLUS Radio volume → {nv}%", source="volume")
    return jsonify(ok=True, volume=nv, muted=False)

@app.route("/api/mute/toggle", methods=["POST"])
def api_mute_toggle():
    _require_vol("omroep", "mute")
    now_muted = bg_mute_toggle()
    return jsonify(ok=True, muted=now_muted)

@app.route("/api/stop", methods=["POST"])
def api_stop():
    global _active_pst_proc, _stop_requested
    # Stop is laag-risico en wordt ook vanaf de preset-/TTS-pagina gebruikt;
    # daarom login/HA i.p.v. het fijnmazige omroep.stop-recht (dat verbergt
    # enkel de knop op de volume-tab).
    if not is_logged_in() and not _ha_auth_ok(): abort(401)
    _stop_requested = True; stopped = False
    with _active_pst_lock:
        if _active_pst_proc and _active_pst_proc.poll() is None:
            try: _active_pst_proc.terminate(); stopped = True
            except Exception: pass
            _active_pst_proc = None
    if not _bg_muted: set_bg_volume(_bg_vol_before)
    log_action("Preset/TTS gestopt", source="preset")
    return jsonify(ok=True, stopped=stopped)

@app.route("/api/rca/toggle", methods=["POST"])
def api_rca_toggle():
    _require_vol("omroep", "rca")
    running = rca_toggle()
    return jsonify(ok=True, running=running)

@app.route("/api/play_preset/<int:preset_id>", methods=["POST"])
def api_play_preset(preset_id):
    if not is_logged_in() and not _ha_auth_ok(): abort(401)
    if not can_preset(preset_id) and not _ha_auth_ok(): abort(403)
    _u, _ip = current_username(), client_ip()
    threading.Thread(target=play_preset_async, args=(preset_id,),
                     kwargs={"log_user": _u, "log_ip": _ip}, daemon=True).start()
    return jsonify(ok=True)

# ──────────────────────────────────────────────
# TTS API endpoints
# ──────────────────────────────────────────────
@app.route("/api/tts/say", methods=["POST"])
def api_tts_say():
    if not is_logged_in() and not _ha_auth_ok(): abort(401)
    data        = request.get_json(silent=True) or {}
    text        = (data.get("text") or "").strip()
    voice       = (data.get("voice") or "").strip()
    try:    rate = int(data.get("rate") or 165)
    except: rate = 165
    gain_pct    = max(0, min(200, int(settings.get("tts_gain") or DEFAULT_TTS_GAIN)))
    use_preroll = bool(data.get("preroll", settings.get("tts_preroll_enabled", True)))
    use_outro   = bool(data.get("outro",   settings.get("tts_outro_enabled",   False)))
    _hit = _blocked_hit(text)
    if _hit:
        log_action(f"TTS geblokkeerd (woord '{_hit}'): \"{text[:60]}\"", source="tts")
        return jsonify(ok=False, blocked=True, word=_hit,
                       error=f"Geblokkeerd woord: '{_hit}'"), 400
    if voice.endswith(".onnx") and not os.path.isabs(voice):
        voice = os.path.join(PIPER_DIR, voice)
    _u, _ip = current_username(), client_ip()
    threading.Thread(
        target=tts_speak_async,
        args=(text, voice, rate, gain_pct, use_preroll, use_outro, ""),
        kwargs={"log_user": _u, "log_ip": _ip},
        daemon=True,
    ).start()
    return jsonify(ok=True)

@app.route("/api/tts/preview", methods=["POST"])
def api_tts_preview():
    if not is_logged_in(): abort(401)
    data        = request.get_json(silent=True) or {}
    text        = (data.get("text") or "").strip()
    voice       = (data.get("voice") or "").strip()
    try:    rate = int(data.get("rate") or 165)
    except: rate = 165
    if not text:
        return jsonify(ok=False, error="Tekst is verplicht"), 400
    _hit = _blocked_hit(text)
    if _hit:
        log_action(f"TTS-genereren geblokkeerd (woord '{_hit}')", source="tts")
        return jsonify(ok=False, blocked=True, word=_hit,
                       error=f"Geblokkeerd woord: '{_hit}'"), 400
    if voice.endswith(".onnx") and not os.path.isabs(voice):
        voice = os.path.join(PIPER_DIR, voice)
    token = secrets.token_urlsafe(16)
    _tts_cache_cleanup()
    threading.Thread(
        target=tts_preview_async,
        args=(text, voice, rate, token),
        daemon=True,
    ).start()
    return jsonify(ok=True, token=token)

@app.route("/api/tts/status/<token>")
def api_tts_status(token):
    if not is_logged_in(): abort(401)
    with _tts_cache_lock:
        entry = _tts_cache.get(token)
    if not entry:
        return jsonify(ready=False)
    ready = os.path.exists(entry["path"]) and os.path.getsize(entry["path"]) > 0
    return jsonify(ready=ready)

@app.route("/api/tts/download/<token>/<fmt>")
def api_tts_download(token, fmt):
    if not is_logged_in(): abort(401)
    fmt = fmt.lower()
    if fmt not in ("wav", "mp3"):
        abort(400)
    with _tts_cache_lock:
        entry = _tts_cache.get(token)
    if not entry or not os.path.exists(entry["path"]):
        abort(404)
    wav_path = entry["path"]
    if fmt == "wav":
        with open(wav_path, "rb") as f:
            data = f.read()
        resp = make_response(data)
        resp.headers["Content-Type"]        = "audio/wav"
        resp.headers["Content-Disposition"] = 'attachment; filename="tts_opname.wav"'
        resp.headers["Content-Length"]      = str(len(data))
        return resp
    fd, tmpmp3 = tempfile.mkstemp(suffix=".mp3", dir=APP_DIR)
    os.close(fd)
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-i", wav_path, "-codec:a", "libmp3lame", "-q:a", "2", tmpmp3],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        if r.returncode != 0:
            try: os.remove(tmpmp3)
            except Exception: pass
            abort(500)
        with open(tmpmp3, "rb") as f:
            data = f.read()
        resp = make_response(data)
        resp.headers["Content-Type"]        = "audio/mpeg"
        resp.headers["Content-Disposition"] = 'attachment; filename="tts_opname.mp3"'
        resp.headers["Content-Length"]      = str(len(data))
        return resp
    except Exception:
        abort(500)
    finally:
        try: os.remove(tmpmp3)
        except Exception: pass

@app.route("/api/tts/save_preset/<token>", methods=["POST"])
def api_tts_save_preset(token):
    if not is_logged_in(): abort(401)
    if not can_save_preset_right():
        abort(403)
    with _tts_cache_lock:
        entry = _tts_cache.get(token)
    if not entry or not os.path.exists(entry["path"]):
        return jsonify(ok=False, error="Text to Speech-opname niet meer beschikbaar (verlopen na 5 minuten)."), 404
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        name = entry.get("text", "TTS preset")[:40]
    pid = next_preset_id()
    dst = os.path.join(PRESETS, f"{pid}.wav")
    try:
        shutil.copy2(entry["path"], dst)
    except Exception as e:
        return jsonify(ok=False, error=f"Kopiëren mislukt: {e}"), 500
    with _preset_names_lock:
        preset_names[str(pid)] = name
        _save_json(NAMES_JSON, preset_names)
    log_action(f"TTS opgeslagen als preset {pid}: \"{name[:40]}\"", source="tts")
    return jsonify(ok=True, preset_id=pid, name=name)

# ──────────────────────────────────────────────
# Audio-uploads: gedeelde helper met ffmpeg-validatie.
# Voorheen werd niet gecontroleerd of de conversie slaagde — een corrupt
# of niet-ondersteund bestand leverde dan stilletjes een lege/kapotte
# wav op. Nu wordt de returncode én de bestandsgrootte gecontroleerd.
# ──────────────────────────────────────────────
def _convert_upload_to_wav(file_obj, dst: str) -> str:
    """Converteert een geüpload audiobestand naar 48kHz mono s16 wav.
    Geeft '' terug bij succes, anders een foutmelding."""
    if not file_obj or file_obj.filename == "":
        return "Geen bestand ontvangen."
    fd, tmp = tempfile.mkstemp(dir=APP_DIR); os.close(fd)
    try:
        file_obj.save(tmp)
        r = subprocess.run(
            ["ffmpeg","-y","-hide_banner","-loglevel","error","-nostdin","-i",tmp,
             "-ar","48000","-ac","1","-sample_fmt","s16",dst],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=60)
        if r.returncode != 0 or not os.path.exists(dst) or os.path.getsize(dst) == 0:
            try:
                if os.path.exists(dst) and os.path.getsize(dst) == 0:
                    os.remove(dst)
            except Exception: pass
            return "Conversie mislukt — is dit een geldig audiobestand (wav/mp3/m4a)?"
        return ""
    except subprocess.TimeoutExpired:
        return "Conversie duurde te lang (timeout)."
    except Exception as e:
        return f"Uploadfout: {e}"
    finally:
        try: os.remove(tmp)
        except Exception: pass

# ──────────────────────────────────────────────
# Preset upload/beheer
# ──────────────────────────────────────────────
def _handle_preset_upload(pid, file_obj, new_name):
    dst = os.path.join(PRESETS, f"{pid}.wav")
    err = _convert_upload_to_wav(file_obj, dst)
    if err:
        log_action(f"Preset {pid} upload mislukt: {err}", source="preset")
        return err, 400
    if (new_name or "").strip():
        with _preset_names_lock:
            preset_names[str(pid)] = new_name.strip()
            _save_json(NAMES_JSON, preset_names)
    log_action(f"Preset {pid} geüpload", source="preset")
    return redirect(url_for("presets_page"))

@app.route("/upload_preset/<int:preset_id>", methods=["POST"])
def upload_preset(preset_id):
    admin_required()
    return _handle_preset_upload(preset_id, request.files.get("file"), request.form.get("name"))

@app.route("/upload_preset_new", methods=["POST"])
def upload_preset_new():
    admin_required()
    return _handle_preset_upload(next_preset_id(), request.files.get("file"), request.form.get("name"))

@app.route("/rename_preset/<int:preset_id>", methods=["POST"])
def rename_preset(preset_id):
    admin_required()
    name = (request.form.get("name") or "").strip()
    if name:
        with _preset_names_lock:
            preset_names[str(preset_id)] = name
            _save_json(NAMES_JSON, preset_names)
    return redirect(url_for("presets_page"))

@app.route("/set_preset_volume/<int:preset_id>", methods=["POST"])
def set_preset_volume(preset_id):
    admin_required()
    try:
        v = max(0, min(200, int(request.form.get("volume","100"))))
        with _preset_vols_lock:
            preset_vols[str(preset_id)] = v
            _save_json(PVOL_JSON, preset_vols)
    except Exception as e: log_action(f"Preset gain fout: {e}", source="preset")
    return redirect(url_for("presets_page"))

@app.route("/set_preset_flags/<int:preset_id>", methods=["POST"])
def set_preset_flags(preset_id):
    admin_required()
    key = str(preset_id); current = preset_flags.get(key) or {}
    current["admin_only"]      = request.form.get("admin_only")      == "1"
    current["preroll_enabled"] = request.form.get("preroll_enabled") == "1"
    current["outro_enabled"]   = request.form.get("outro_enabled")   == "1"
    preset_flags[key] = current
    _save_json(PFLAGS_JSON, preset_flags)
    return redirect(url_for("presets_page"))

@app.route("/delete_preset/<int:preset_id>", methods=["POST"])
def delete_preset(preset_id):
    admin_required()
    wav = os.path.join(PRESETS, f"{preset_id}.wav")
    try:
        if os.path.exists(wav): os.remove(wav)
    except Exception as e:
        log_action(f"Preset {preset_id} verwijder fout: {e}", source="admin")
        return redirect(url_for("presets_page"))
    with _preset_names_lock:
        preset_names.pop(str(preset_id), None)
        _save_json(NAMES_JSON, preset_names)
    with _preset_vols_lock:
        preset_vols.pop(str(preset_id), None)
        _save_json(PVOL_JSON, preset_vols)
    with _preset_icons_lock:
        preset_icons.pop(str(preset_id), None)
        _save_json(PICONS_JSON, preset_icons)
    preset_flags.pop(str(preset_id), None)
    _save_json(PFLAGS_JSON, preset_flags)
    log_action(f"Preset {preset_id} verwijderd", source="admin")
    return redirect(url_for("presets_page"))

@app.route("/set_preset_icon/<int:preset_id>", methods=["POST"])
def set_preset_icon(preset_id):
    admin_required()
    icon = (request.form.get("icon") or "").strip()
    # Basisvalidatie: alleen lowercase letters, underscores, cijfers toegestaan
    if icon and not re.match(r"^[a-z0-9_]{1,60}$", icon):
        icon = ""
    with _preset_icons_lock:
        if icon:
            preset_icons[str(preset_id)] = icon
        else:
            preset_icons.pop(str(preset_id), None)
        _save_json(PICONS_JSON, preset_icons)
    log_action(f"Preset {preset_id} icon → '{icon}'", source="admin")
    return redirect(url_for("presets_page"))

@app.route("/presets/<int:preset_id>/bewerken")
def edit_preset_page(preset_id):
    admin_required()
    if not os.path.exists(os.path.join(PRESETS, f"{preset_id}.wav")):
        abort(404)
    flag_obj = preset_flags.get(str(preset_id)) or {}
    ctx = dict(
        pid=preset_id,
        nm=preset_names.get(str(preset_id), f"Preset {preset_id}"),
        icon=(preset_icons.get(str(preset_id)) or "").strip(),
        gain=max(0, min(200, int(preset_vols.get(str(preset_id), DEFAULT_PRESET_GAIN)))),
        admin_only=bool(flag_obj.get("admin_only")),
        preroll_on=bool(flag_obj.get("preroll_enabled", True)),
        outro_on=bool(flag_obj.get("outro_enabled", True)),
        ok=request.args.get("ok") == "1",
        icons_json=Markup(json.dumps(PRESET_ICON_SUGGESTIONS)),
    )
    return render_layout(render_template_string(PRESET_EDIT_BODY, **ctx), "presets")

@app.route("/presets/<int:preset_id>/opslaan", methods=["POST"])
def save_preset_all(preset_id):
    """Sla naam, icoon, gain én opties in één keer op (i.p.v. losse formulieren)."""
    admin_required()
    if not os.path.exists(os.path.join(PRESETS, f"{preset_id}.wav")):
        abort(404)
    key = str(preset_id)
    name = (request.form.get("name") or "").strip()
    icon = (request.form.get("icon") or "").strip()
    if icon and not re.match(r"^[a-z0-9_]{1,60}$", icon):
        icon = ""
    try:    gain = max(0, min(200, int(request.form.get("gain", "100"))))
    except: gain = 100
    if name:
        with _preset_names_lock:
            preset_names[key] = name; _save_json(NAMES_JSON, preset_names)
    with _preset_icons_lock:
        if icon: preset_icons[key] = icon
        else:    preset_icons.pop(key, None)
        _save_json(PICONS_JSON, preset_icons)
    with _preset_vols_lock:
        preset_vols[key] = gain; _save_json(PVOL_JSON, preset_vols)
    cur = preset_flags.get(key) or {}
    cur["admin_only"]      = request.form.get("admin_only")      == "1"
    cur["preroll_enabled"] = request.form.get("preroll_enabled") == "1"
    cur["outro_enabled"]   = request.form.get("outro_enabled")   == "1"
    preset_flags[key] = cur; _save_json(PFLAGS_JSON, preset_flags)
    log_action(f"Preset {preset_id} bijgewerkt (naam/icoon/gain/opties)", source="admin")
    return redirect(url_for("edit_preset_page", preset_id=preset_id, ok=1))

# ──────────────────────────────────────────────
# Preroll (intro) upload/verwijder
# ──────────────────────────────────────────────
@app.route("/admin/intro/upload", methods=["POST"])
def upload_intro():
    admin_required()
    err = _convert_upload_to_wav(request.files.get("file"), INTRO_WAV)
    if err:
        log_action(f"Preroll upload mislukt: {err}", source="preset")
        return err, 400
    log_action("Preroll geüpload", source="preset")
    return redirect(url_for("beheer_page"))

@app.route("/admin/intro/delete", methods=["POST"])
def delete_intro():
    admin_required()
    try:
        if os.path.exists(INTRO_WAV): os.remove(INTRO_WAV)
        log_action("Preroll verwijderd", source="preset")
    except Exception as e: log_action(f"Preroll fout: {e}", source="preset")
    return redirect(url_for("beheer_page"))

# ──────────────────────────────────────────────
# Outro upload/verwijder (NIEUW in v6.3.0)
# ──────────────────────────────────────────────
@app.route("/admin/outro/upload", methods=["POST"])
def upload_outro():
    admin_required()
    err = _convert_upload_to_wav(request.files.get("file"), OUTRO_WAV)
    if err:
        log_action(f"Outro upload mislukt: {err}", source="preset")
        return err, 400
    log_action("Outro geüpload", source="preset")
    return redirect(url_for("beheer_page"))

@app.route("/admin/outro/delete", methods=["POST"])
def delete_outro():
    admin_required()
    try:
        if os.path.exists(OUTRO_WAV): os.remove(OUTRO_WAV)
        log_action("Outro verwijderd", source="preset")
    except Exception as e: log_action(f"Outro fout: {e}", source="preset")
    return redirect(url_for("beheer_page"))

# ──────────────────────────────────────────────
# Schema beheer
# ──────────────────────────────────────────────
def _new_sched_id():
    with _sched_lock:
        return (max([s.get("id",0) for s in _schedules])+1) if _schedules else 1

def _extract_days():
    return [v for v in request.form.getlist("days") if v in ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]]

@app.route("/admin/schedule/add_interval", methods=["POST"])
def add_schedule_interval():
    admin_required()
    try:
        s = {"id": _new_sched_id(), "kind": "interval",
             "preset_id": int(request.form.get("preset_id") or 0),
             "every_sec": int(request.form.get("every_sec") or 0),
             "days": _extract_days(),
             "start_hm": (request.form.get("start_hm") or "").strip(),
             "end_hm":   (request.form.get("end_hm") or "").strip(),
             "next_ts": 0}
        with _sched_lock: _schedules.append(s); _save_schedules()
    except Exception as e: log_action(f"Schedule fout: {e}", source="schedule")
    return redirect(url_for("beheer_page"))

@app.route("/admin/schedule/add_attimes", methods=["POST"])
def add_schedule_attimes():
    admin_required()
    try:
        s = {"id": _new_sched_id(), "kind": "at_times",
             "preset_id": int(request.form.get("preset_id") or 0),
             "times_hm": [t.strip() for t in request.form.getlist("times_hm") if t.strip()],
             "days": _extract_days(), "last_run_key": ""}
        with _sched_lock: _schedules.append(s); _save_schedules()
    except Exception as e: log_action(f"Schedule fout: {e}", source="schedule")
    return redirect(url_for("beheer_page"))

@app.route("/admin/schedule/delete/<int:sid>", methods=["POST"])
def delete_schedule(sid):
    admin_required()
    with _sched_lock:
        _schedules[:] = [s for s in _schedules if s.get("id") != sid]
        _save_schedules()
    return redirect(url_for("beheer_page"))

# ── Automatiseringen: API + beheer-endpoints ──
def _sanitize_automation(data, aid=None):
    name    = (str(data.get("name") or "")).strip() or "Naamloos"
    enabled = bool(data.get("enabled", True))
    trigs = []
    for t in (data.get("triggers") or []):
        if t.get("type") == "webhook":
            tok = (str(t.get("token") or "")).strip() or base64.urlsafe_b64encode(os.urandom(9)).decode().rstrip("=")
            trigs.append({"type": "webhook", "token": tok})
            continue
        tm = str(t.get("time") or "").strip()
        if not re.match(r"^\d{2}:\d{2}$", tm):
            continue
        trigs.append({"time": tm, "days": [d for d in (t.get("days") or []) if d in _DAY_ORDER]})
    conds = []
    for c in (data.get("conditions") or []):
        ct = c.get("type")
        if ct == "rca":
            conds.append({"type": "rca", "state": "off" if c.get("state") == "off" else "on"})
        elif ct == "spotify":
            conds.append({"type": "spotify", "state": "stopped" if c.get("state") == "stopped" else "playing"})
        elif ct == "time_between":
            a2 = str(c.get("after") or "").strip(); b2 = str(c.get("before") or "").strip()
            if re.match(r"^\d{2}:\d{2}$", a2) and re.match(r"^\d{2}:\d{2}$", b2):
                conds.append({"type": "time_between", "after": a2, "before": b2})
        elif ct == "day":
            conds.append({"type": "day", "days": [d for d in (c.get("days") or []) if d in _DAY_ORDER]})
    cond_mode = "any" if data.get("condition_mode") == "any" else "all"
    acts = []
    for a in (data.get("actions") or []):
        typ = a.get("type")
        try:
            if typ == "preset_sequence":
                ids = [int(p) for p in (a.get("presets") or []) if str(p).isdigit()]
                if ids:
                    acts.append({"type": "preset_sequence", "presets": ids,
                                 "intro": bool(a.get("intro", True)), "outro": bool(a.get("outro", True))})
            elif typ == "rca":
                acts.append({"type": "rca", "state": "off" if a.get("state") == "off" else "on"})
            elif typ == "rca_auto":
                acts.append({"type": "rca_auto", "state": "off" if a.get("state") == "off" else "on"})
            elif typ == "volume":
                acts.append({"type": "volume", "value": max(0, min(100, int(a.get("value", 65))))})
            elif typ == "channel":
                acts.append({"type": "channel", "channel": 2 if int(a.get("channel", 1)) == 2 else 1})
            elif typ == "tts":
                txt = (str(a.get("text") or "")).strip()
                if txt:
                    acts.append({"type": "tts", "text": txt[:500],
                                 "gain": max(0, min(200, int(a.get("gain", DEFAULT_TTS_GAIN)))),
                                 "intro": bool(a.get("intro", True)),
                                 "outro": bool(a.get("outro", False))})
            elif typ == "wait":
                acts.append({"type": "wait", "seconds": max(0, min(600, int(a.get("seconds", 1))))})
            elif typ == "spotify":
                cmd = a.get("command")
                if cmd == "volume":
                    acts.append({"type": "spotify", "command": "volume",
                                 "value": max(0, min(100, int(a.get("value", 50))))})
                elif cmd in ("pause", "resume", "playpause", "next", "prev", "stop"):
                    acts.append({"type": "spotify", "command": cmd})
            elif typ == "webhook":
                url = (str(a.get("url") or "")).strip()
                if url.startswith("http"):
                    acts.append({"type": "webhook", "url": url[:500],
                                 "method": "GET" if str(a.get("method", "")).upper() == "GET" else "POST",
                                 "body": str(a.get("body") or "")[:1000]})
        except Exception:
            continue
    return {"id": aid, "name": name, "enabled": enabled, "last_run": 0,
            "triggers": trigs, "conditions": conds, "condition_mode": cond_mode, "actions": acts}

@app.route("/api/automations")
def api_automations():
    admin_required()
    with _autom_lock:
        return jsonify(automations=list(automations))

@app.route("/admin/automation/save", methods=["POST"])
def automation_save():
    admin_required()
    data = request.get_json(silent=True) or {}
    aid  = data.get("id")
    with _autom_lock:
        if aid:
            aid = int(aid)
            existing = next((a for a in automations if a.get("id") == aid), None)
            if not existing:
                return jsonify(ok=False, error="niet gevonden"), 404
            clean = _sanitize_automation(data, aid)
            clean["last_run"] = existing.get("last_run", 0)
            existing.clear(); existing.update(clean)
        else:
            clean = _sanitize_automation(data, _new_autom_id())
            automations.append(clean); aid = clean["id"]
        _save_automations()
    log_action(f"Automatisering opgeslagen: {clean['name']}", source="admin")
    return jsonify(ok=True, id=aid)

@app.route("/admin/automation/delete/<int:aid>", methods=["POST"])
def automation_delete(aid):
    admin_required()
    with _autom_lock:
        automations[:] = [a for a in automations if a.get("id") != aid]
        _save_automations()
    return jsonify(ok=True)

@app.route("/admin/automation/toggle/<int:aid>", methods=["POST"])
def automation_toggle(aid):
    admin_required()
    with _autom_lock:
        a = next((x for x in automations if x.get("id") == aid), None)
        if not a:
            return jsonify(ok=False), 404
        a["enabled"] = not a.get("enabled", True); _save_automations(); st = a["enabled"]
    log_action(f"Automatisering '{a.get('name')}' {'aan' if st else 'uit'}", source="admin")
    return jsonify(ok=True, enabled=st)

@app.route("/admin/automation/run/<int:aid>", methods=["POST"])
def automation_run(aid):
    admin_required()
    with _autom_lock:
        a = next((x for x in automations if x.get("id") == aid), None)
    if not a:
        return jsonify(ok=False), 404
    threading.Thread(target=run_automation, args=(a,), kwargs={"test": True}, daemon=True).start()
    return jsonify(ok=True)

@app.route("/hook/automation/<token>", methods=["POST", "GET"])
def hook_automation(token):
    """Webhook-trigger: een externe aanroep (bijv. Home Assistant) start de
    automatisering met deze geheime token. Voorwaarden worden gerespecteerd."""
    token = (token or "").strip()
    target = None
    with _autom_lock:
        for a in automations:
            if any(t.get("type") == "webhook" and t.get("token") == token
                   for t in (a.get("triggers") or [])):
                target = a; break
    if not target or not token:
        abort(404)
    if not target.get("enabled", True):
        return jsonify(ok=False, reason="uitgeschakeld"), 200
    if not _eval_conditions(target.get("conditions"), target.get("condition_mode", "all")):
        return jsonify(ok=False, reason="voorwaarden niet voldaan"), 200
    _fire_automation(target)
    log_action(f"Automatisering '{target.get('name')}' via webhook gestart", source="schedule")
    return jsonify(ok=True)

# ──────────────────────────────────────────────
# Home Assistant endpoints
# ──────────────────────────────────────────────
@app.route("/ha/state")
def ha_state():
    ha_required(); st = current_state()
    return jsonify({"volume": int(st.get("volume") or 0), "muted": bool(st.get("muted")),
                    "rca_running": bool(st.get("rca_running")), "playing": bool(st.get("playing"))})

@app.route("/ha/volume", methods=["POST"])
def ha_volume_set():
    ha_required()
    global _bg_vol_before
    data = request.get_json(silent=True) or {}
    v = max(0, min(100, int(data.get("value", data.get("volume", 0)) or 0)))
    with _bg_lock:
        changed = (v != _bg_vol_before)
        _bg_vol_before = v
        if not _bg_muted: set_bg_volume(v)
    _save_bg_volume(v)             # onthouden voor herstel na herstart
    # Als er een ingelogde web-sessie is (iemand bedient het via de site,
    # niet via een HA-automatisering/token), schrijf het dan op naam van die
    # gebruiker onder 'Volume' i.p.v. generiek 'Home Assistant'. Alleen loggen
    # bij een echte wijziging — voorkomt spam van HA die dezelfde stand herhaalt.
    if changed:
        if is_logged_in():
            log_action(f"BG volume → {v}%", source="volume")
        else:
            log_action(f"HA BG volume → {v}%", source="ha")
    return jsonify(ok=True, volume=v)

@app.route("/ha/mute", methods=["POST"])
def ha_mute_set():
    ha_required()
    state = (request.get_json(silent=True) or {}).get("state","toggle").strip().lower()
    if state in ("toggle","t"):         now = bg_mute_toggle(); return jsonify(ok=True, muted=now)
    if state in ("on","mute","1","true"):
        if not _bg_muted: bg_mute()
        return jsonify(ok=True, muted=True)
    if state in ("off","unmute","0","false"):
        if _bg_muted: bg_unmute()
        return jsonify(ok=True, muted=False)
    return jsonify(ok=False, error="invalid_state"), 400

@app.route("/ha/rca", methods=["POST"])
def ha_rca_set():
    ha_required()
    state = (request.get_json(silent=True) or {}).get("state","toggle").strip().lower()
    running = rca_running()
    if state in ("toggle","t"):         running = rca_toggle(); return jsonify(ok=True, rca_running=running)
    if state in ("on","start","1","true"):
        if not running: rca_start()
        return jsonify(ok=True, rca_running=True)
    if state in ("off","stop","0","false"):
        if running: rca_stop()
        return jsonify(ok=True, rca_running=False)
    return jsonify(ok=False, error="invalid_state"), 400

@app.route("/ha/stop", methods=["POST"])
def ha_stop():
    ha_required()
    global _active_pst_proc, _stop_requested
    _stop_requested = True; stopped = False
    with _active_pst_lock:
        if _active_pst_proc and _active_pst_proc.poll() is None:
            try: _active_pst_proc.terminate(); stopped = True
            except Exception: pass
            _active_pst_proc = None
    if not _bg_muted: set_bg_volume(_bg_vol_before)
    log_action("Preset/TTS gestopt via HA", source="ha")
    return jsonify(ok=True, stopped=stopped)

@app.route("/ha/tts", methods=["POST"])
def ha_tts():
    ha_required()
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text: return jsonify(ok=False, error="text is verplicht"), 400
    _hit = _blocked_hit(text)
    if _hit:
        log_action(f"HA TTS geblokkeerd (woord '{_hit}')", source="ha")
        return jsonify(ok=False, blocked=True, word=_hit, error=f"Geblokkeerd woord: '{_hit}'"), 400
    voice       = (data.get("voice") or settings.get("tts_edge_voice") or "nl-NL-MaartenNeural").strip()
    try:    rate = int(data.get("rate") or 165)
    except: rate = 165
    use_preroll = bool(data.get("preroll", True))
    use_outro   = bool(data.get("outro",   settings.get("tts_outro_enabled", False)))
    gain_pct    = max(0, min(200, int(data.get("gain") or settings.get("tts_gain") or DEFAULT_TTS_GAIN)))
    if voice.endswith(".onnx") and not os.path.isabs(voice): voice = os.path.join(PIPER_DIR, voice)
    log_action(f"HA TTS: '{text[:60]}' gain={gain_pct}%", source="ha")
    threading.Thread(target=tts_speak_async, args=(text, voice, rate, gain_pct, use_preroll, use_outro, ""),
                     kwargs={"log_user": "Home Assistant", "log_ip": client_ip()}, daemon=True).start()
    return jsonify(ok=True)

# ──────────────────────────────────────────────
# 3CX webhook
# ──────────────────────────────────────────────
BASE_EXT = 700

@app.route("/hook/<int:ext>", methods=["POST"])
def hook_from_3cx(ext: int):
    try:
        preset_id = ext - BASE_EXT
        if preset_id < 1: return jsonify(ok=False, error="Extensie buiten bereik"), 400
        path = os.path.join(PRESETS, f"{preset_id}.wav")
        if not os.path.exists(path):
            return jsonify(ok=False, error="Preset bestaat niet"), 404
        # Home Assistant gebruikt dezelfde webhook maar krijgt zijn eigen
        # categorie (op basis van het IP), zodat de logs klopppen.
        ip = client_ip()
        is_ha = ip == (settings.get("ha_webhook_ip") or "")
        src   = "ha" if is_ha else "3cx"
        actor = "Home Assistant" if is_ha else "3CX"
        log_action(f"{actor} webhook → extensie {ext} → preset {preset_id}", source=src)
        threading.Thread(target=play_preset_async, args=(preset_id,),
                         kwargs={"log_user": actor, "log_ip": ip}, daemon=True).start()
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

# ──────────────────────────────────────────────
def _startup_audio():
    """Bij opstart van de service/VM: het laatst ingestelde PLUS Radio-volume
    terugzetten en RCA automatisch aanzetten. Best-effort met korte wachttijd
    zodat de ALSA-devices klaar zijn na een verse boot."""
    if settings.get("demo_mode"):
        return                            # demo: geen hardware-audio aanraken
    try:
        time.sleep(5)
    except Exception:
        pass
    # 1. Laatst ingestelde volume herstellen — alléén als er echt een stand is
    #    opgeslagen (bg_state.json). Anders de mixer met rust laten (geen sprong
    #    naar de default) en de huidige stand overnemen als vertrekpunt.
    global _bg_vol_before
    try:
        if os.path.exists(BG_STATE_JSON):
            set_bg_volume(_bg_vol_before)
            log_action(f"PLUS Radio volume hersteld na opstart → {_bg_vol_before}%", source="volume")
        else:
            _bg_vol_before = get_bg_volume_pct()
            _save_bg_volume(_bg_vol_before)
    except Exception:
        pass
    # 2. RCA automatisch aan
    if settings.get("rca_autostart", True):
        try:
            if not rca_running():
                rca_start()
                log_action("RCA automatisch gestart bij opstart", source="rca")
        except Exception:
            pass
    # 3. Opgeslagen Spotify-EQ live zetten (alsaequal; PLUS Radio-EQ zit al in RCA_CMD)
    try:
        _apply_eq_spot()
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════
# Live omroep via SIP (3CX / SBC)
# Bel het ingestelde extensienummer vanaf een 3CX-toestel → de app neemt op,
# speelt de intro, laat de stem van de beller LIVE over de winkelspeakers
# horen (via dezelfde `pst`-uitgang + duck als presets/TTS) en speelt na het
# ophangen de outro. Eenrichting: de winkel hoort de beller; de beller hoort
# de winkel niet (stilte-bron) → geen rondzingen. baresip draait als kind-
# proces van de app en wordt bestuurd via ctrl_tcp (JSON-netstrings).
# ══════════════════════════════════════════════════════════════════════
SIP_DIR       = os.path.join(APP_DIR, "baresip")
SIP_SILENCE   = os.path.join(SIP_DIR, "silence.wav")
SIP_LOG       = os.path.join(SIP_DIR, "baresip.log")
SIP_CTRL_HOST = "127.0.0.1"
SIP_CTRL_PORT = 4444
SIP_SIP_PORT  = 5062

_sip_proc       = None
_sip_proc_lock  = threading.Lock()
_sip_sock       = None
_sip_send_lock  = threading.Lock()
_sip_call_ended = threading.Event()
_sip_state = {"running": False, "registered": False, "in_call": False,
              "last_event": "", "last_peer": "", "caller_ext": "", "since": 0.0}

def _sip_peer_ext(peer):
    """Haal het extensienummer/gebruikersdeel uit een SIP-URI, bijv.
    'sip:104@pluskoelhuis.my3cx.nl' → '104' (voor logging + de melding)."""
    if not peer:
        return ""
    m = re.search(r"sip:([^@;>\s]+)@", peer) or re.search(r'"?([^"<]+?)"?\s*<sip:', peer)
    return (m.group(1).strip() if m else str(peer).strip())

def _sip_cfg_ok():
    """Alle vereiste velden ingevuld én ingeschakeld (en niet in demo)?"""
    s = settings
    if s.get("demo_mode"):
        return False
    return bool(s.get("sip_enabled") and s.get("sip_extension") and
                s.get("sip_registrar_host") and s.get("sip_sbc_host") and
                s.get("sip_auth_id") and s.get("sip_auth_pass"))

def _render_sip_config():
    """Schrijf baresip's accounts+config uit de instellingen + een stilte-bron
    (zo lang als de max-omroepduur, zodat de eenrichtings-bron nooit opraakt)."""
    os.makedirs(SIP_DIR, exist_ok=True)
    s = settings
    ext  = str(s.get("sip_extension") or "").strip()
    reg  = str(s.get("sip_registrar_host") or "").strip()
    try:    regp = int(s.get("sip_registrar_port") or 5060)
    except Exception: regp = 5060
    sbc  = str(s.get("sip_sbc_host") or "").strip()
    try:    sbcp = int(s.get("sip_sbc_port") or 5060)
    except Exception: sbcp = 5060
    aid  = str(s.get("sip_auth_id") or "").strip()
    pwd  = str(s.get("sip_auth_pass") or "")
    reg_uri = "sip:%s@%s%s" % (ext, reg, (":%d" % regp if regp and regp != 5060 else ""))
    acc = ('<%s>;auth_user=%s;auth_pass=%s;outbound="sip:%s:%d;transport=udp";'
           'regint=600;answermode=manual;ptime=20\n' % (reg_uri, aid, pwd, sbc, sbcp))
    with open(os.path.join(SIP_DIR, "accounts"), "w") as f:
        f.write(acc)
    try: os.chmod(os.path.join(SIP_DIR, "accounts"), 0o600)   # wachtwoord → alleen radio
    except Exception: pass
    cfg = ("module_path      /usr/lib/baresip/modules\n"
           "sip_listen       0.0.0.0:%d\n"
           "module           account.so\n"
           "module           g711.so\n"
           "module           g722.so\n"
           "module           stun.so\n"
           "module           alsa.so\n"
           "module           menu.so\n"
           "module           ctrl_tcp.so\n"
           "ctrl_tcp_listen  %s:%d\n"
           "audio_player     alsa,pst\n"
           "audio_source     alsa,null_src\n"    # eenrichting: stilte op elke codec-rate
           "audio_alert      alsa,null_sink\n"   # beltoon niet naar de speakers
           "audio_buffer     20-40\n"            # kleinere afspeelbuffer → minder vertraging
           "jitter_buffer_delay  2-4\n"          # kleinere jitterbuffer (LAN) → minder vertraging
           % (SIP_SIP_PORT, SIP_CTRL_HOST, SIP_CTRL_PORT))
    with open(os.path.join(SIP_DIR, "config"), "w") as f:
        f.write(cfg)

def _sip_start_proc():
    global _sip_proc
    if settings.get("demo_mode"):
        return
    with _sip_proc_lock:
        if _sip_proc and _sip_proc.poll() is None:
            return
        try:
            _render_sip_config()
            logf = open(SIP_LOG, "w")
            _sip_proc = subprocess.Popen(
                ["baresip", "-f", SIP_DIR],
                stdout=logf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                env={**os.environ, "HOME": HOME})
            _sip_state["running"] = True
            log_action("Live omroep (SIP): baresip gestart", source="sip")
        except Exception as e:
            _sip_proc = None
            log_action("Live omroep (SIP): starten mislukt: %s" % e, source="sip")

def _sip_stop_proc():
    global _sip_proc, _sip_sock
    with _sip_proc_lock:
        p = _sip_proc
        _sip_proc = None
    if p and p.poll() is None:
        try: p.terminate()
        except Exception: pass
        try: p.wait(timeout=4)
        except Exception:
            try: p.kill()
            except Exception: pass
    _sip_state.update({"running": False, "registered": False, "in_call": False})
    try:
        if _sip_sock: _sip_sock.close()
    except Exception: pass
    _sip_sock = None

def _sip_restart():
    _sip_stop_proc()
    time.sleep(0.5)
    if _sip_cfg_ok():
        _sip_start_proc()

def _sip_supervisor_loop():
    """Houdt baresip draaiend zolang de functie aan+ingesteld is; herstart bij
    een crash; stopt 'm als de functie uit gaat."""
    while True:
        try:
            want = _sip_cfg_ok()
            with _sip_proc_lock:
                alive = bool(_sip_proc and _sip_proc.poll() is None)
            if want and not alive:
                _sip_start_proc()
            elif (not want) and alive:
                _sip_stop_proc()
        except Exception:
            pass
        time.sleep(6)

def _sip_send(command):
    """Stuur een baresip-commando via ctrl_tcp (netstring-JSON)."""
    global _sip_sock
    j = json.dumps({"command": command})
    ns = ("%d:%s," % (len(j), j)).encode()
    with _sip_send_lock:
        try:
            if _sip_sock:
                _sip_sock.sendall(ns)
                return True
        except Exception:
            pass
    return False

def _sip_on_message(data):
    try:
        msg = json.loads(data.decode("utf-8", "replace"))
    except Exception:
        return
    if not isinstance(msg, dict):
        return
    # reginfo-antwoord → registratiestatus bijwerken (robuust, los van event-timing:
    # het REGISTER_OK-event kan al afgaan vóór onze ctrl-verbinding er is).
    if msg.get("response") and isinstance(msg.get("data"), str) and "Expires" in msg["data"]:
        m = re.search(r"Expires\s+([0-9]+)s", msg["data"])
        _sip_state["registered"] = bool(m and int(m.group(1)) > 0)
        return
    if not msg.get("event"):
        return
    typ = (msg.get("type") or "").upper()
    _sip_state["last_event"] = typ
    if typ == "REGISTER_OK":
        if not _sip_state["registered"]:
            log_action("Live omroep (SIP): geregistreerd bij de SBC", source="sip")
        _sip_state["registered"] = True
    elif typ in ("REGISTER_FAIL", "UNREGISTERING"):
        _sip_state["registered"] = False
    elif typ == "CALL_INCOMING":
        peer = msg.get("peeruri") or msg.get("param") or ""
        _sip_state["last_peer"] = peer
        threading.Thread(target=_sip_handle_call, args=(peer,), daemon=True).start()
    elif typ == "CALL_CLOSED":
        _sip_call_ended.set()

def _sip_ctrl_loop():
    """Verbindt met baresip's ctrl_tcp, leest events (netstrings) en verwerkt ze."""
    global _sip_sock
    while True:
        with _sip_proc_lock:
            alive = bool(_sip_proc and _sip_proc.poll() is None)
        if not alive:
            _sip_state["registered"] = False
            time.sleep(2); continue
        try:
            s = socket.create_connection((SIP_CTRL_HOST, SIP_CTRL_PORT), timeout=4)
        except Exception:
            time.sleep(2); continue
        _sip_sock = s
        buf = b""
        try:
            s.settimeout(1.0)
            last_poll = 0.0
            while True:
                with _sip_proc_lock:
                    if not (_sip_proc and _sip_proc.poll() is None):
                        break
                now = time.time()
                if now - last_poll > 5:          # registratiestatus periodiek uitlezen
                    _sip_send("reginfo"); last_poll = now
                try:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                except socket.timeout:
                    continue
                except Exception:
                    break
                while True:                     # parse netstrings: <len>:<data>,
                    ci = buf.find(b":")
                    if ci < 0 or ci > 12:
                        if ci > 12: buf = b""    # verminkt → weggooien
                        break
                    try:
                        ln = int(buf[:ci])
                    except Exception:
                        buf = b""; break
                    if len(buf) < ci + 1 + ln + 1:
                        break
                    payload = buf[ci + 1: ci + 1 + ln]
                    buf = buf[ci + 1 + ln + 1:]  # trailing komma overslaan
                    _sip_on_message(payload)
        except Exception:
            pass
        finally:
            try: s.close()
            except Exception: pass
            _sip_sock = None
        time.sleep(1)

def _sip_ext_in_token(digits, token):
    """Valt een (genummerd) toestel binnen één allowlist-item?
    Item is óf een enkel nummer ('101') óf een bereik ('301-309')."""
    token = (token or "").strip()
    if "-" in token:                             # bereik lo-hi (inclusief)
        a, _, b = token.partition("-")
        a = re.sub(r"\D", "", a); b = re.sub(r"\D", "", b)
        if a.isdigit() and b.isdigit() and digits.isdigit():
            lo, hi = int(a), int(b)
            if lo > hi: lo, hi = hi, lo
            return lo <= int(digits) <= hi
        return False
    t = re.sub(r"\D", "", token)                 # enkel nummer (exact)
    return bool(t) and t == digits

def _sip_call_allowed(ext):
    """Mag dit toestel omroepen?
    - meer dan 3 cijfers = buitenlijn → NOOIT toegestaan (harde veiligheidsregel);
    - lege allowlist = alle interne toestellen toegestaan;
    - anders alleen als het toestel in een item/bereik van de allowlist valt."""
    digits = re.sub(r"\D", "", ext or "")
    if len(digits) > 3:                          # buitenlijn → altijd weigeren
        return False
    allowed = settings.get("sip_allowed_exts") or []
    if not allowed:                              # niks ingevuld → alles (intern) mag
        return True
    if not digits:
        return False
    return any(_sip_ext_in_token(digits, tok) for tok in allowed)

def _sip_handle_call(peer):
    """Inkomend gesprek → dempen, intro, aannemen, live over de speakers,
    outro, muziek herstellen. Serieel met presets/TTS via duck_lock."""
    ext = _sip_peer_ext(peer)
    if not _sip_call_allowed(ext):               # buitenlijn of niet-toegestaan toestel
        _sip_send("hangup")
        log_action("Live omroep geweigerd — toestel %s (niet toegestaan / buitenlijn)"
                   % (ext or "onbekend"), source="sip")
        return
    if _sip_state.get("in_call") or not _sip_cfg_ok():
        _sip_send("hangup"); return
    if not duck_lock.acquire(timeout=2):         # er loopt al een omroep → bezet
        _sip_send("hangup"); return
    prev_bg = get_bg_volume_pct()
    t_duck  = None
    try:
        _sip_state["in_call"]   = True
        _sip_state["caller_ext"] = ext
        _sip_state["since"]     = time.time()
        _sip_call_ended.clear()
        log_action("Live omroep gestart — toestel %s" % (ext or "onbekend"),
                   source="sip", user=("toestel %s" % ext if ext else "SIP"))
        t_duck = threading.Thread(target=pi_duck, daemon=True)
        if PI_ENABLED:
            t_duck.start()
        _duck_local(prev_bg)                     # Spotify + PLUS Radio wegfaden
        set_pst_gain(max(0, min(200, int(settings.get("sip_gain", 100) or 100))))
        if PI_ENABLED and t_duck is not None:
            t_duck.join(timeout=PI_DUCK_WAIT)
        if settings.get("sip_intro", True):
            _play_preroll()
        _sip_send("accept")                      # nu aannemen → live audio naar pst
        maxs = max(10, min(1800, int(settings.get("sip_max_secs") or 300)))
        if not _sip_call_ended.wait(timeout=maxs):
            log_action("Live omroep: max-duur bereikt → automatisch beëindigd", source="sip")
            _sip_send("hangup")
            _sip_call_ended.wait(timeout=3)
        if settings.get("sip_outro", True):
            _play_outro()
    except Exception as e:
        log_action("Live omroep fout: %s" % e, source="sip")
        try: _sip_send("hangup")
        except Exception: pass
    finally:
        if PI_ENABLED and t_duck is not None:
            try: t_duck.join(timeout=8)
            except Exception: pass
            threading.Thread(target=pi_unduck, daemon=True).start()
        try: _unduck_local(prev_bg)
        except Exception: pass
        _sip_state["in_call"]   = False
        _sip_state["caller_ext"] = ""
        log_action("Live omroep beëindigd — toestel %s" % (ext or "onbekend"),
                   source="sip", user=("toestel %s" % ext if ext else "SIP"))
        duck_lock.release()

def _sip_probe_register(timeout=10):
    """Verbindings-/registratietest: bereikt de VM de SBC, en accepteert die de
    registratie van de extensie? Draait de functie al (ingeschakeld) → live-
    status. Anders → een korte wegwerp-baresip op aparte poorten die één keer
    probeert te registreren. Onderscheidt 3 gevallen:
      • REGISTER_OK   → gelukt
      • REGISTER_FAIL → SBC antwoordt maar wéígert (auth/extensie)
      • geen antwoord → SBC onbereikbaar (firewall-retourpad)."""
    s = settings
    for k in ("sip_extension", "sip_registrar_host", "sip_sbc_host",
              "sip_auth_id", "sip_auth_pass"):
        if not s.get(k):
            return {"ok": False, "stage": "config",
                    "msg": "Vul eerst alle velden in en sla op."}
    reg_host = str(s.get("sip_registrar_host")).strip()
    try:    dns_ip = socket.gethostbyname(reg_host)
    except Exception: dns_ip = None
    sbc = str(s.get("sip_sbc_host")).strip()
    try:    sbcp = int(s.get("sip_sbc_port") or 5060)
    except Exception: sbcp = 5060
    # Al een ingeschakelde sessie actief? → gebruik de live registratiestatus.
    with _sip_proc_lock:
        alive = bool(_sip_proc and _sip_proc.poll() is None)
    if alive:
        if _sip_state.get("registered"):
            return {"ok": True, "stage": "live", "registered": True, "dns": dns_ip,
                    "msg": "Geregistreerd bij de SBC — bellen kan."}
        return {"ok": False, "stage": "live", "registered": False, "dns": dns_ip,
                "msg": "baresip draait maar is (nog) niet geregistreerd — geen "
                       "antwoord van de SBC. Controleer het firewall-retourpad "
                       "(SBC → %s) en de 3CX-kant." % reg_host}
    # Wegwerp-probe op aparte poorten (raakt de hoofd-instantie niet).
    d = tempfile.mkdtemp(prefix="sipprobe_")
    ctrlp, sipp = 4460, 5064
    proc = None
    try:
        ext = str(s.get("sip_extension")).strip()
        aid = str(s.get("sip_auth_id")).strip()
        pwd = str(s.get("sip_auth_pass"))
        try:    regp = int(s.get("sip_registrar_port") or 5060)
        except Exception: regp = 5060
        reg_uri = "sip:%s@%s%s" % (ext, reg_host, (":%d" % regp if regp and regp != 5060 else ""))
        with open(os.path.join(d, "accounts"), "w") as f:
            f.write('<%s>;auth_user=%s;auth_pass=%s;outbound="sip:%s:%d;transport=udp";'
                    'regint=600;answermode=manual\n' % (reg_uri, aid, pwd, sbc, sbcp))
        os.chmod(os.path.join(d, "accounts"), 0o600)
        with open(os.path.join(d, "config"), "w") as f:
            f.write("module_path /usr/lib/baresip/modules\n"
                    "sip_listen 0.0.0.0:%d\nmodule account.so\nmodule g711.so\n"
                    "module stun.so\nmodule menu.so\nmodule ctrl_tcp.so\n"
                    "ctrl_tcp_listen 127.0.0.1:%d\n" % (sipp, ctrlp))
        proc = subprocess.Popen(["baresip", "-f", d],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                stdin=subprocess.DEVNULL, env={**os.environ, "HOME": HOME})
        deadline = time.time() + timeout
        sock = None
        while time.time() < deadline and sock is None:
            try:    sock = socket.create_connection((SIP_CTRL_HOST, ctrlp), timeout=2)
            except Exception: time.sleep(0.4)
        registered, failmsg = None, ""
        if sock:
            sock.settimeout(1.0); buf = b""; last_poll = 0.0
            while time.time() < deadline:
                now = time.time()
                if now - last_poll > 1.5:        # registratiestatus opvragen
                    try:
                        jj = json.dumps({"command": "reginfo"})
                        sock.sendall(("%d:%s," % (len(jj), jj)).encode())
                    except Exception: pass
                    last_poll = now
                try:    chunk = sock.recv(4096)
                except socket.timeout: continue
                except Exception: break
                if not chunk: break
                buf += chunk
                while True:
                    ci = buf.find(b":")
                    if ci < 0 or ci > 12:
                        if ci > 12: buf = b""
                        break
                    try:    ln = int(buf[:ci])
                    except Exception: buf = b""; break
                    if len(buf) < ci + 1 + ln + 1: break
                    payload = buf[ci + 1: ci + 1 + ln]; buf = buf[ci + 1 + ln + 1:]
                    try:    msg = json.loads(payload.decode("utf-8", "replace"))
                    except Exception: msg = None
                    if not isinstance(msg, dict):
                        continue
                    if msg.get("event"):
                        t = (msg.get("type") or "").upper()
                        if t == "REGISTER_OK":
                            registered = True
                        elif t == "REGISTER_FAIL":
                            registered = False; failmsg = str(msg.get("param") or "")
                    elif msg.get("response") and isinstance(msg.get("data"), str) and "Expires" in msg["data"]:
                        mm = re.search(r"Expires\s+([0-9]+)s", msg["data"])
                        if mm and int(mm.group(1)) > 0:
                            registered = True
                if registered is True or (registered is False and failmsg):
                    break
            try: sock.close()
            except Exception: pass
        if registered is True:
            return {"ok": True, "stage": "probe", "registered": True, "dns": dns_ip,
                    "msg": "Registratie gelukt — de SBC accepteert extensie %s. ✔" % ext}
        if registered is False:
            return {"ok": False, "stage": "probe", "registered": False, "dns": dns_ip,
                    "msg": "De SBC antwoordt, maar wéígert de registratie — controleer "
                           "Auth-ID, wachtwoord en extensie.%s"
                           % ((" (%s)" % failmsg) if failmsg else "")}
        return {"ok": False, "stage": "probe", "registered": None, "dns": dns_ip,
                "msg": "Geen antwoord van de SBC (%s:%d) binnen %d s — de pakketten "
                       "komen niet terug. Controleer het firewall-retourpad tussen "
                       "%s (radio) en de SBC, en of 3CX de VM niet blokkeert."
                       % (sbc, sbcp, timeout, "10.0.12.70")}
    finally:
        if proc and proc.poll() is None:
            try: proc.terminate(); proc.wait(timeout=3)
            except Exception:
                try: proc.kill()
                except Exception: pass
        shutil.rmtree(d, ignore_errors=True)

def _sip_test_announce():
    """Test de omroep-audioketen zónder telefoontje: dempen → intro →
    gesproken testregel → outro → herstel. Zo hoor je precies hoe een echte
    live omroep klinkt (werkt ook als de SBC-registratie nog niet rond is)."""
    if _sip_state.get("in_call"):
        return False
    if not duck_lock.acquire(timeout=2):
        return False
    prev_bg = get_bg_volume_pct()
    t_duck  = None
    tmpwav  = None
    try:
        log_action("Live omroep: testomroep afgespeeld", source="sip")
        t_duck = threading.Thread(target=pi_duck, daemon=True)
        if PI_ENABLED:
            t_duck.start()
        _duck_local(prev_bg)
        set_pst_gain(max(0, min(200, int(settings.get("sip_gain", 100) or 100))))
        if PI_ENABLED and t_duck is not None:
            t_duck.join(timeout=PI_DUCK_WAIT)
        if settings.get("sip_intro", True):
            _play_preroll()
        try:
            tmpwav = _tts_generate_to_wav(
                "Dit is een test van de live omroep via de telefoon.",
                settings.get("tts_edge_voice") or "nl-NL-MaartenNeural", 165)
        except Exception:
            tmpwav = None
        if tmpwav and os.path.exists(tmpwav):
            _play_file_to_pst(tmpwav)
        if settings.get("sip_outro", True):
            _play_outro()
    finally:
        if PI_ENABLED and t_duck is not None:
            try: t_duck.join(timeout=8)
            except Exception: pass
            threading.Thread(target=pi_unduck, daemon=True).start()
        try: _unduck_local(prev_bg)
        except Exception: pass
        if tmpwav:
            try: os.remove(tmpwav)
            except Exception: pass
        duck_lock.release()
    return True

@app.route("/api/sip/status")
def api_sip_status():
    admin_required()
    s = settings
    return jsonify(
        enabled=bool(s.get("sip_enabled")),
        configured=_sip_cfg_ok(),
        running=_sip_state.get("running", False),
        registered=_sip_state.get("registered", False),
        in_call=_sip_state.get("in_call", False),
        last_event=_sip_state.get("last_event", ""),
        last_peer=_sip_state.get("last_peer", ""),
        caller_ext=_sip_state.get("caller_ext", ""),
        extension=s.get("sip_extension", ""),
        registrar=s.get("sip_registrar_host", ""),
        sbc=s.get("sip_sbc_host", ""),
    )

@app.route("/api/sip/live")
def api_sip_live():
    """Lichtgewicht live-status voor de melding bij de balie (elke ingelogde
    gebruiker mag dit uitlezen; alleen wie het vinkje aan heeft, polt 'm)."""
    if not is_logged_in():
        abort(403)
    in_call = bool(_sip_state.get("in_call"))
    since = _sip_state.get("since", 0.0) or 0.0
    return jsonify(
        in_call=in_call,
        caller_ext=_sip_state.get("caller_ext", "") if in_call else "",
        since_secs=int(max(0.0, time.time() - since)) if (in_call and since) else 0,
    )

@app.route("/api/sip/hangup", methods=["POST"])
def api_sip_hangup():
    """Stop een lopende live omroep (stopknop bij de balie). Toegestaan voor
    admins en gebruikers met het live-omroep-melding-vinkje aan."""
    if not is_logged_in():
        abort(403)
    u = current_user()
    if not (is_admin() or u.get("sip_alert")):
        abort(403)
    if not _sip_state.get("in_call"):
        return jsonify(ok=True, note="geen actieve omroep")
    _sip_send("hangup")
    log_action("Live omroep gestopt via de melding (toestel %s)"
               % (_sip_state.get("caller_ext") or "onbekend"),
               source="sip", user=current_username(), ip=client_ip())
    return jsonify(ok=True)

@app.route("/admin/sip/save", methods=["POST"])
def admin_sip_save():
    admin_required()
    d = request.get_json(silent=True) or {}
    def _str(k):
        v = d.get(k, "")
        return v.strip() if isinstance(v, str) else str(v or "").strip()
    def _port(k, dflt=5060):
        try: return max(1, min(65535, int(d.get(k) or dflt)))
        except Exception: return dflt
    settings["sip_enabled"]        = bool(d.get("sip_enabled"))
    settings["sip_extension"]      = _str("sip_extension")[:32]
    settings["sip_auth_id"]        = _str("sip_auth_id")[:64]
    pw = d.get("sip_auth_pass")
    if pw:                                        # leeg = ongewijzigd laten
        settings["sip_auth_pass"] = str(pw)[:128]
    settings["sip_registrar_host"] = _str("sip_registrar_host")[:128]
    settings["sip_sbc_host"]       = _str("sip_sbc_host")[:128]
    settings["sip_registrar_port"] = _port("sip_registrar_port")
    settings["sip_sbc_port"]       = _port("sip_sbc_port")
    try:    settings["sip_max_secs"] = max(10, min(1800, int(d.get("sip_max_secs") or 300)))
    except Exception: settings["sip_max_secs"] = 300
    try:    settings["sip_gain"] = max(0, min(200, int(d.get("sip_gain") or 100)))
    except Exception: settings["sip_gain"] = 100
    raw = d.get("sip_allowed_exts", "")
    parts = raw if isinstance(raw, list) else re.split(r"[\s,;]+", str(raw or ""))
    clean = []
    for p in parts:                              # alleen '123' of '123-456' behouden
        p = (p or "").strip().replace(" ", "")
        if re.fullmatch(r"\d{1,4}(-\d{1,4})?", p):
            clean.append(p)
    settings["sip_allowed_exts"] = clean[:50]
    settings["sip_intro"] = bool(d.get("sip_intro", True))
    settings["sip_outro"] = bool(d.get("sip_outro", True))
    _save_json(SETTINGS_JSON, settings)
    log_action("Live omroep (SIP)-instellingen opgeslagen", source="admin")
    threading.Thread(target=_sip_restart, daemon=True).start()   # herstart/stop baresip
    return jsonify(ok=True, configured=_sip_cfg_ok())

@app.route("/admin/sip/test", methods=["POST"])
def admin_sip_test():
    admin_required()
    if settings.get("demo_mode"):
        return jsonify(ok=False, error="Niet beschikbaar in demo")
    if _sip_state.get("in_call"):
        return jsonify(ok=False, error="Er loopt al een live omroep")
    threading.Thread(target=_sip_test_announce, daemon=True).start()
    return jsonify(ok=True)

@app.route("/admin/sip/test_connection", methods=["POST"])
def admin_sip_test_connection():
    admin_required()
    if settings.get("demo_mode"):
        return jsonify(ok=False, msg="Niet beschikbaar in demo")
    try:
        return jsonify(_sip_probe_register(timeout=10))
    except Exception as e:
        return jsonify(ok=False, msg="Test mislukt: %s" % e)


if __name__ == "__main__":
    threading.Thread(target=_startup_audio, daemon=True).start()
    threading.Thread(target=_lisa_loop, daemon=True).start()
    threading.Thread(target=_sip_supervisor_loop, daemon=True).start()   # baresip aan/uit + crash-herstel
    threading.Thread(target=_sip_ctrl_loop, daemon=True).start()         # SIP-events + belafhandeling
    for _f in glob.glob("/tmp/comm_*.wav"):   # opruimen na een eventuele crash
        try: os.remove(_f)
        except Exception: pass
    _comm_ring_ensure()               # commercial-replay ringbuffer starten indien aan
    threading.Thread(target=_comm_boundary_loop, daemon=True).start()   # speelt bij nummerovergang
    app.run(host="0.0.0.0", port=int(os.environ.get("OMROEPWEB_PORT", "5050")),
            debug=False, threaded=True)