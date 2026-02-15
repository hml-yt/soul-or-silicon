This project is a custom-built, interactive game show system designed for your YouTube channel, **Hacking Modern Life**. The concept is **"Silicon or Soul,"** where contestants listen to a piece of music and guess whether it was composed by Artificial Intelligence ("Silicon") or a human musician ("Soul").

Here is the breakdown of the entire system, from the physical build to the modern game engine.

### 1. The Physical Architecture

The system is designed to be modular, robust for video shoots, and visually distinct on camera.

* **The Consoles (x3):**
* **Design:** 3D-printed, slanted enclosures with a "sliding dovetail" bottom lid for screw-less assembly.
* **Interface:** Two 24mm arcade buttons per player. One for "Silicon" (AI) and one for "Soul" (Human).
* **Connectivity:** Each console has a panel-mount RJ45 jack on the back. They connect to the main hub using standard Ethernet cables (acting as 8-wire umbilical cords, not networking).


* **The Hub (The Brain):**
* **Core:** A Raspberry Pi 5 (or 4) running the Python package.
* **Interface:** 3x RJ45 Breakout boards receive the signals from the consoles.
* **Power Handling:** A **ULN2003A** chip (or driver board) sits on a breadboard to bridge the voltage gap. It allows the Pi’s delicate 3.3V GPIO pins to safely switch the bright 5V LEDs inside the arcade buttons so they look good on camera.


### 2. The Software (Modern Game Engine)

The game engine now runs as a modern Python package under `src/` and is optimized for Raspberry Pi usage with an external keyboard until the physical consoles are ready. The Pi automatically runs full rounds (play song → open voting → auto-reveal → next round).

**Key Features:**

* **Auto-Round Loop (No Manual Reveal):**
* Randomly plays a track from `songs/ai/` or `songs/human/`.
* Opens voting immediately and auto-closes after **15 seconds** or when all players vote.
* Auto-reveals winners based on the folder (AI = Silicon, Human = Soul), updates scores, and plays SFX.

* **Keyboard-First Input (Pi Friendly):**
* Player keys:
  * Player 1: `A` (Silicon), `S` (Soul)
  * Player 2: `D` (Silicon), `F` (Soul)
  * Player 3: `G` (Silicon), `H` (Soul)
* Host keys:
  * `P`: Pause/Resume
  * `N`: Skip song / next round
  * `Q` or `ESC`: Quit

* **Visual & Audio Feedback:**
* **Pygame Host Display:** Shows status, voting countdown, votes, and animated scores.
* **Soundboard:** Uses `pygame.mixer` for SFX and `.mp3` playback for songs.

* **Logging:**
* Every round appends a JSON line to `logs/game_log.jsonl` for post-production.

### 3. How it Runs on Shoot Day

1. You set up the 3 consoles and plug them into the Hub via Ethernet.
2. You connect the Hub (Pi) to the studio speakers (Audio Out) and a small monitor (HDMI).
3. You run the game module.
4. **Action:** The Pi automatically plays a song and opens voting for 15s (or until all players vote).
5. **Reveal:** The system auto-reveals the correct answer, plays SFX, and updates the scoreboard.

### 4. Folder Structure

```
silicon-or-soul/
  songs/
    ai/
    human/
  sounds/
    start.wav
    lock_in.wav
    reveal.wav
    win.wav
    lose.wav
  logs/
    game_log.jsonl
```

### 5. Running the Game

Install once (editable install):
```
pip install -e .
```

Run the module:
```
python -m silicon_or_soul
```

### 6. Arduino Controller Setup (PLAYER_1..PLAYER_3)

The game now supports up to 3 USB serial controllers using the firmware in `arduino/sketch_controller/sketch_controller.ino`.

1. Flash each board with a unique `PLAYER_ID` in the sketch:
   - Board A: `PLAYER_1`
   - Board B: `PLAYER_2`
   - Board C: `PLAYER_3`
2. Plug boards into the host machine (Pi/Mac) over USB.
3. Start the game normally (`python -m silicon_or_soul`).

At runtime the game auto-discovers controllers and uses this serial protocol:

- Host -> controller:
  - `WHO_ARE_YOU?` (handshake; board replies with its `PLAYER_ID`)
  - `RESET` (sent when a new voting window opens)
  - `WIN_SILICON` / `WIN_SOUL` (sent on reveal so matching winners flash)
- Controller -> host:
  - `PLAYER_1` / `PLAYER_2` / `PLAYER_3`
  - `VOTE:SILICON` / `VOTE:SOUL`

Keyboard voting still works as a fallback, so you can run without hardware connected.

### 7. MP3 Notes (Raspberry Pi)

If `.mp3` playback fails on your Pi (SDL_mixer build issues), convert tracks to `.ogg` or `.wav` and re-scan the `songs/` folders.
This project is a custom-built, interactive game show system designed for your YouTube channel, **Hacking Modern Life**. The concept is **"Silicon or Soul,"** where contestants listen to a piece of music and guess whether it was composed by Artificial Intelligence ("Silicon") or a human musician ("Soul").

Here is the breakdown of the entire system, from the physical build to the code currently in the Canvas.

### 1. The Physical Architecture

The system is designed to be modular, robust for video shoots, and visually distinct on camera.

* **The Consoles (x3):**
* **Design:** 3D-printed, slanted enclosures with a "sliding dovetail" bottom lid for screw-less assembly.
* **Interface:** Two 24mm arcade buttons per player. One for "Silicon" (AI) and one for "Soul" (Human).
* **Connectivity:** Each console has a panel-mount RJ45 jack on the back. They connect to the main hub using standard Ethernet cables (acting as 8-wire umbilical cords, not networking).


* **The Hub (The Brain):**
* **Core:** A Raspberry Pi 5 (or 4) running the Python script.
* **Interface:** 3x RJ45 Breakout boards receive the signals from the consoles.
* **Power Handling:** A **ULN2003A** chip (or driver board) sits on a breadboard to bridge the voltage gap. It allows the Pi’s delicate 3.3V GPIO pins to safely switch the bright 5V LEDs inside the arcade buttons so they look good on camera.



### 2. The Software (Modern Game Engine)

The Python script is the "Game Engine." It manages the game flow, lights, sound, and scoring. It is built with a **Hybrid Architecture** to work on both your development machine (MacBook Pro) and the production hardware (Raspberry Pi).

**Key Features of the Code:**

* **Auto-Detection (Simulation Mode):**
* The script checks if `gpiozero` (the Pi hardware library) is present.
* **On your Mac:** It fails to find `gpiozero`, so it loads "Dummy Classes" and enters **Simulation Mode**. This lets you test the game logic using keyboard keys (`A/S` for Player 1, `D/F` for Player 2, etc.) and see "Virtual LEDs" on the screen.
* **On the Pi:** It loads the real drivers and controls the physical GPIO pins.


* **The Game Loop:**
* **State Machine:** The game cycles through `IDLE`, `VOTING`, and `REVEAL` states.
* **Host Controls:** You (the host) control the flow via keyboard:
* `SPACE`: Opens voting (Resets LEDs, plays "Start" sound).
* `1` or `2`: Triggers the Reveal. The code checks who voted correctly and flashes their specific LED (e.g., if the answer is Silicon, only the Silicon button flashes for players who voted Silicon).
* `R`: Resets the round.




* **Visual & Audio Feedback:**
* **Pygame Window:** Provides a "Host Display" showing who has voted (Cyan for Silicon, Orange for Soul) and their current score. This is critical for you to manage the show while filming.
* **Soundboard:** The system uses `pygame.mixer` to play .wav files for game events (Lock In, Win, Start), adding production value directly from the Pi.



### 3. How it Runs on Shoot Day

1. You set up the 3 consoles and plug them into the Hub via Ethernet.
2. You connect the Hub (Pi) to the studio speakers (Audio Out) and a small monitor (HDMI).
3. You run the script.
4. **Action:** You play a song. You hit `SPACE`. The players smash their buttons. The script locks in their votes (preventing changing answers).
5. **Reveal:** You hit `1` (for AI). The script instantly flashes the lights of the winners and plays a "Win" sound, capturing the genuine reaction of the contestants.
