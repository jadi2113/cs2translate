# CS2Translate
A simple, lightweight translator app for Counter-Strike 2 that watches your in-game chat and automatically translates messages to your language of choice.

## Features
CS2Translate watches the games `console.log` file for new messages and translates them using Google Translate as they arrive. Messages are displayed in a separate window on your second monitor.

#### Fully external
By reading messages off of the disk and displaying translations in a separate window, CS2Translate never has to inject code or read game memory. Because of this it remains **fully external** and poses **no risk of a VAC Ban**. The trade-off is that **you need a second monitor** (or another way to look at the translator window while playing).

#### Message filtering and caching
Common untranslatable phrases in CS chat, such as `gg`, `gl hf`, etc., as well as messages already in your configured target language are automatically ignored. You can optionally configure messages you sent yourself and messages detected as English to be skipped as well.
There is also a cache for recent translations, so players spamming won't get you rate limited by Google.

#### Low performance impact
The app itself uses very little CPU, on the order of 0 to 1% (on my hardware). The `-condebug` launch option required for `console.log` to actually be written should also make little difference on average hardware. If your game is desperate for CPU cycles, don't use this app.

## Installation
There currently are only prebuilt binaries for Windows. If you're on Linux, visit [Building from Source](#building-from-source) first.

1. Download the latest portable release from the [GitHub Releases Page](https://github.com/jadi2113/cs2translate/releases). (cs2translate-portable-win.zip)

2. Extract the downloaded archive to a folder of your choice.

3. Go to Steam -> CS2 -> Properties and add the `-condebug` launch option. It is required for `console.log` to be created and updated with new messages.

4. Launch the game once to ensure `console.log` already exists, then start `cs2translate.exe`.

5. Open the settings window and configure the path to your `console.log` file. (Usually in `steamapps\common\Counter-Strike Global Offensive\game\csgo`)

6. Configure your target language and other options as needed.

### Optional: Auto-launch together with CS2
You can have Steam launch CS2Translate automatically when you start CS2. To configure this, add the following at the start of your CS2 launch options in addition to `-condebug`. Replace `path/to/dir` with the path to where `cs2translate.exe` is saved. Use `.sh` instead of `.bat` on Linux.
```
path/to/dir/launch.bat %command%
```

### Building from Source
There currently are only prebuilt binaries for Windows. Until I set up GitHub Actions, Linux users have to build from source.
To do this, make sure Python is installed, then run the following:
```
pip install -r requirements.txt
```
```
./build.sh
```
The binary output will be located in the `build/` directory.

To make the auto-launch functionality work on Linux, don't forget:
```
chmod +x launch.sh
```

## Usage
1. Launch Counter-Strike 2 and CS2Translate.
2. Make sure the status bar shows `Watching console.log for new messages`.
3. Play as normal, translated chat messages will be displayed in the main window.
4. Open Settings at any time to change the target language, clear previous translations, etc.

If you experience an error, first try deleting config.json (saved next to the executable) and restarting. If it doesn't work, reinstall the app, and if the issue still appears, do the following:
1. Start the app from a Terminal.
2. Reproduce the issue.
3. Open a [GitHub Issue](https://github.com/jadi2113/cs2translate/issues) and provide the error message and terminal output.

## Notes
- Translation is powered by deep_translator's Google Translate endpoint under the hood. You may see rate limit or server errors during heavy use. Messages containing certain slurs or other flagged language may not be translated.
- The current language detection system can be unreliable for short messages, so occasional mesdetections or erroneously skipped messages are expected. This does not affect translation quality.
