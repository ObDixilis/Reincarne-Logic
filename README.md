# Reincarne-Logic

This repository contains a small prototype for a "Think Tank" web application. The app lets users submit ideas for solving grand challenges and displays the submissions in a simple list.

## Running the web app

The application requires Python and Flask. Install dependencies and start the server with:

```bash
pip install flask
python app.py
```

Visit `http://localhost:5000` in your browser to interact with the Think Tank interface.

## iOS game prototype

A SwiftUI prototype that turns the pattern-recognition prompt into a game lives in `ios/ReincarneLogicGame`. See `ios/README.md` for the gameplay loop and Xcode setup steps.

## Serpentine Sense experiment

The iOS prototype now includes **Serpentine Sense**, an Afro-Gorgon
environmental-awareness vertical slice. It fuses serpentine instinct, aura
perception, aetherware prediction, and hex sensitivity into an eight-direction
threat-reading loop with calculated time dilation.

- Open the **Serpentine** tab in the iOS app to play the cognition loop.
- Read [the system RFC](docs/SERPENTINE_SENSE_RFC.md) for lore, human-factors
  assumptions, architecture, accessibility, and Unreal-port guidance.
- Run the deterministic balance model with:

  ```bash
  python3 simulation/serpentine_sense_balance.py
  python3 -m unittest discover -s simulation -p "test_*.py"
  ```

The simulator uses only the Python standard library.

