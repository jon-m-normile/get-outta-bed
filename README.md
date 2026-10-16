# Get Outta Bed!

An alarm clock for elementary OS that plays recorded wake-up messages and keeps going until a puzzle is solved. There is no snooze.

## Install

1. Copy this folder to the computer, open a Terminal in it, and run:

   ```
   ./install.sh
   ```

   If any required packages are missing, it runs `sudo apt install` and asks for your password. Then it:
   - copies the app to `~/.local/share/get-outta-bed/app/`
   - adds the launcher, icon and a login autostart entry
   - starts the app in the background

2. To upgrade, run `./install.sh` again from the new folder. Alarms, recordings and the puzzle photo are kept.

To remove the app, run `./uninstall.sh`. It asks before deleting alarms, recordings and the photo.

## Keep it in the dock

1. Open **Applications** and launch **Get Outta Bed!**.
2. Right-click its icon in the dock and choose **Keep in Dock**.

Closing the window only hides it. The app keeps running so alarms still ring, and clicking the dock icon brings the window back. To really stop it, use **Quit** in the app menu (top right). Quitting means no alarms will ring until the app is started again, either from Applications or automatically at the next login.

While the app is running, it stops the computer from going to sleep on its own. The screen can still blank and lock.

## Adding recordings

1. Record the messages. iPhone Voice Memos (`.m4a`) work, as do MP3, AAC, WAV, OGG, OPUS and FLAC.
2. Get the files onto this computer by email, USB stick or cloud drive.
3. In the app, click **Recordings**, then **Add recordings…**, or drag the files onto the Recordings window. The files are copied into the app, so the originals can be deleted afterwards.
4. Open an alarm and tick the messages it should play. Drag them to reorder, and choose **Play in order** or **Shuffle**.

If an alarm has no messages ticked, or its files are missing, a built-in alarm tone plays instead.

## When the screen is locked

If the screen is locked when an alarm goes off, the sound still plays and the volume still ramps up. The puzzle appears once the screen is unlocked, and the alarm keeps playing until the puzzle is solved.

If nobody solves the puzzle, the alarm stops by itself after 60 minutes.

## Troubleshooting

- **Check the log.** Every alarm, skipped alarm, solve and error is recorded in `~/.local/share/get-outta-bed/log.txt`. To read it, run:

  ```
  tail -n 50 ~/.local/share/get-outta-bed/log.txt
  ```

- **Test the sound.** Open an alarm and click **▶ Test** next to the volume slider. It plays for 5 seconds at that alarm's maximum volume, then puts the volume back. To try the full experience, click **Ring now (test)**.
- **No sound from an `.m4a` file.** Run `./install.sh` again. It installs `gstreamer1.0-libav`, which is needed for M4A.
- **An alarm didn't ring.**
  - Make sure the app is running. It should appear in the dock, or show up when you run `pgrep -af get-outta-bed`.
  - Make sure the alarm's switch is on.
  - If the computer was asleep or off when the alarm was due, it won't ring. An alarm that is missed by more than 15 minutes is skipped, and the skip is noted in the log.
- **Settings file damaged.** If `settings.json` can't be read, it's saved as `settings.json.corrupt-<time>` and the app starts fresh.

## Running the tests

```
python3 -m pip install --user pytest   # or: sudo apt install python3-pytest
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` stops unrelated pytest plugins on the machine from interfering.
