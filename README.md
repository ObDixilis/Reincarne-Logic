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

## Star Weaver skill and lineage workbench

The self-contained [Star Weaver module](star-weaver/README.md) implements an interactive skill graph, composed light/signal effects, persistent incarnations, and reproducible hereditary/cross-breed pathways across multiple generations. It uses Python 3.10+ and a browser, with no added packages. On Windows, open `star-weaver/Start Star Weaver.cmd`; on other desktops, run `python star-weaver/server.py --open`.

The approved skill baseline keeps Affinity and Techfinity independent and Finity in Context Doubt. New hereditary rules are explicit experimental policies with synthetic profiles and provenance. The module includes editable tree data, schemas, pathway diagrams, tests, and verification evidence; it runs independently of the earlier prototypes.
