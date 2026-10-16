#!/usr/bin/env bash
# Removes Get Outta Bed! (app, launcher, icon, autostart). Asks before deleting alarms and recordings.
set -euo pipefail

APP_ID=io.github.getouttabed.GetOuttaBed
DATA="$HOME/.local/share/get-outta-bed"
ICONS="$HOME/.local/share/icons/hicolor"

if [[ -x "$DATA/app/run.py" ]]; then
    python3 "$DATA/app/run.py" --quit >/dev/null 2>&1 || true
    sleep 1
fi

rm -rf "$DATA/app"
rm -f "$HOME/.local/share/applications/$APP_ID.desktop" \
      "$HOME/.config/autostart/$APP_ID.desktop" \
      "$ICONS/scalable/apps/$APP_ID.svg"
gtk-update-icon-cache -f -t "$ICONS" >/dev/null 2>&1 || true
update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
echo "Get Outta Bed! has been removed."

if [[ -d "$DATA" ]]; then
    read -r -p "Also delete alarms, recordings and the puzzle photo in $DATA? [y/N] " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        rm -rf "$DATA"
        echo "Data deleted."
    else
        echo "Data kept in $DATA."
    fi
fi
