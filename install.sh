#!/usr/bin/env bash
#
# Omroepweb / PLUS Audiosysteem — installer.
# Idempotent: veilig om opnieuw te draaien (ook voor updaten van een bestaande
# installatie). Draai dit als de gebruiker die de app draait (bijv. 'radio').
#
#   ./install.sh
#
set -euo pipefail

REPO_URL="https://github.com/LarsPeter1230/plus-audiosysteem.git"
DEFAULT_DIR="$HOME/plus-audiosysteem"

# ── Bootstrap: draaien we via `curl | bash` (geen checkout)? Dan eerst klonen. ──
SELF="$(readlink -f "$0" 2>/dev/null || true)"
if [ -z "$SELF" ] || [ ! -f "$(dirname "$SELF")/app.py" ]; then
  echo "==> Repo klonen naar $DEFAULT_DIR ..."
  command -v git >/dev/null 2>&1 || { sudo apt-get update -qq; sudo apt-get install -y git; }
  if [ -d "$DEFAULT_DIR/.git" ]; then
    git -C "$DEFAULT_DIR" fetch -q origin && git -C "$DEFAULT_DIR" reset -q --hard origin/main
  else
    git clone -q "$REPO_URL" "$DEFAULT_DIR"
  fi
  exec bash "$DEFAULT_DIR/install.sh"
fi

APP_DIR="$(cd "$(dirname "$SELF")" && pwd)"
RUN_USER="$(id -un)"
RUN_HOME="$HOME"
SERVICE="omroepweb"

say(){ printf '\n\033[1;32m==>\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33m[!]\033[0m %s\n' "$*"; }

if [ "$RUN_USER" = "root" ]; then
  warn "Draai dit script NIET als root, maar als de app-gebruiker (bijv. 'radio')."
  exit 1
fi

say "App-map:  $APP_DIR"
say "Gebruiker: $RUN_USER   Home: $RUN_HOME"

# 1. OS-pakketten
say "Systeempakketten installeren (sudo)..."
sudo apt-get update -qq || true
sudo apt-get install -y \
  python3 python3-venv python3-pip git curl ffmpeg alsa-utils \
  libasound2-plugin-equal caps baresip || warn "Sommige pakketten ontbreken mogelijk (controleer handmatig)."

# 2. Python venv + dependencies
say "Python virtualenv + dependencies..."
[ -d "$APP_DIR/venv" ] || python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

# 3. Runtime-map + secrets
say "Runtime-map en omgevingsbestand..."
mkdir -p "$RUN_HOME/omroepweb/presets" "$RUN_HOME/omroepweb/avatars"
if [ ! -f "$APP_DIR/omroepweb.env" ]; then
  cp "$APP_DIR/system/omroepweb.env.example" "$APP_DIR/omroepweb.env"
  warn "Nieuw omroepweb.env aangemaakt — VUL JE SECRETS IN: $APP_DIR/omroepweb.env"
fi

# 4. systemd-service renderen + installeren
say "systemd-service installeren..."
tmp="$(mktemp)"
sed -e "s#__USER__#$RUN_USER#g" -e "s#__APP_DIR__#$APP_DIR#g" \
    "$APP_DIR/system/omroepweb.service.tmpl" > "$tmp"
sudo cp "$tmp" "/etc/systemd/system/$SERVICE.service"
rm -f "$tmp"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE" >/dev/null 2>&1 || true

# 5. Commando's + sudoers (update-knop, audio-apply) installeren
say "'omroepweb-update' + 'omroepweb-apply-audio' installeren..."
tmp="$(mktemp)"
sed -e "s#__APP_DIR__#$APP_DIR#g" -e "s#__SERVICE__#$SERVICE#g" \
    "$APP_DIR/scripts/omroepweb-update.tmpl" > "$tmp"
sudo cp "$tmp" /usr/local/bin/omroepweb-update
sudo chmod 755 /usr/local/bin/omroepweb-update
sudo cp "$APP_DIR/scripts/omroepweb-apply-audio.tmpl" /usr/local/bin/omroepweb-apply-audio
sudo chmod 755 /usr/local/bin/omroepweb-apply-audio
rm -f "$tmp"

# sudoers: app mag herstarten + audio toepassen zonder wachtwoord
sudo tee /etc/sudoers.d/omroepweb >/dev/null <<SUDO
$RUN_USER ALL=(root) NOPASSWD: /usr/bin/systemctl restart $SERVICE, /usr/bin/systemctl restart $SERVICE.service, /bin/systemctl restart $SERVICE, /bin/systemctl restart $SERVICE.service, /usr/local/bin/omroepweb-apply-audio
SUDO
sudo chmod 440 /etc/sudoers.d/omroepweb
sudo visudo -c -f /etc/sudoers.d/omroepweb >/dev/null 2>&1 || warn "sudoers-regel controleren"

# 6. Service (her)starten
say "Service (her)starten..."
sudo systemctl restart "$SERVICE"
sleep 2
sudo systemctl --no-pager --lines=0 status "$SERVICE" | head -3 || true

cat <<EOF

\033[1;32m✔ Klaar.\033[0m  De app draait op poort 5050.

Vergeet niet:
  1. Secrets invullen in:  $APP_DIR/omroepweb.env   (daarna: sudo systemctl restart $SERVICE)
  2. Audio-config (EQ/mixers): $APP_DIR/system/asound.conf  → naar /etc/asound.conf (maak eerst een backup!)
  3. Spotify Connect: go-librespot-binary + $APP_DIR/system/go-librespot.config.yml (zie README).
  4. Online stream + hardware (Icecast, Streamit Lisa, nginx): zie README.md.

Later updaten naar de laatste versie:  \033[1momroepweb-update\033[0m
EOF
