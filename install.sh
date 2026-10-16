#!/usr/bin/env bash
# Installs (or upgrades) Get Outta Bed! for the current user. Safe to re-run:
# alarms, recordings and the puzzle photo in ~/.local/share/get-outta-bed/ are kept.
set -euo pipefail

APP_ID=io.github.getouttabed.GetOuttaBed
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA="$HOME/.local/share/get-outta-bed"
DEST="$DATA/app"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor"
AUTOSTART="$HOME/.config/autostart"

PACKAGES=(python3 python3-gi gir1.2-gtk-4.0 python3-dateutil pulseaudio-utils
          gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly
          gstreamer1.0-libav gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0)

missing=()
for p in "${PACKAGES[@]}"; do
    dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "install ok installed" || missing+=("$p")
done
if ((${#missing[@]})); then
    echo "Installing missing packages: ${missing[*]}"
    sudo apt install -y "${missing[@]}"
else
    echo "All required packages are already installed."
fi

# Stop a running copy so its files can be replaced.
if [[ -x "$DEST/run.py" ]]; then
    python3 "$DEST/run.py" --quit >/dev/null 2>&1 || true
    sleep 1
fi

echo "Copying app to $DEST"
mkdir -p "$DATA/recordings"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -r "$SRC/run.py" "$SRC/getouttabed" "$SRC/data" "$DEST/"
find "$DEST" -name __pycache__ -type d -prune -exec rm -rf {} +
chmod +x "$DEST/run.py"

desktop_entry() {
    cat <<EOF
[Desktop Entry]
Type=Application
Name=Get Outta Bed!
Comment=An alarm clock that keeps going until you solve a puzzle
Exec=/usr/bin/python3 "$DEST/run.py"$1
Icon=$APP_ID
Terminal=false
Categories=Utility;Clock;
Keywords=alarm;clock;wake;
StartupNotify=true
StartupWMClass=$APP_ID
EOF
}

mkdir -p "$APPS" "$ICONS/scalable/apps" "$AUTOSTART"
desktop_entry "" > "$APPS/$APP_ID.desktop"
{ desktop_entry " --background"; echo "NoDisplay=true"; echo "X-GNOME-Autostart-enabled=true"; } \
    > "$AUTOSTART/$APP_ID.desktop"
cp "$SRC/data/$APP_ID.svg" "$ICONS/scalable/apps/$APP_ID.svg"

[[ -f "$ICONS/index.theme" ]] || cp /usr/share/icons/hicolor/index.theme "$ICONS/" 2>/dev/null || true
gtk-update-icon-cache -f -t "$ICONS" >/dev/null 2>&1 || true
update-desktop-database "$APPS" >/dev/null 2>&1 || true

echo "Starting Get Outta Bed! in the background"
setsid nohup /usr/bin/python3 "$DEST/run.py" --background >/dev/null 2>&1 < /dev/null &

echo
echo "Done. Open \"Get Outta Bed!\" from Applications, then right-click its dock icon and choose \"Keep in Dock\"."
