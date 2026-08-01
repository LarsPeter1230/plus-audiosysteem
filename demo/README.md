# Statische demo (GitHub Pages)

De map die op de `gh-pages`-branch staat is een **statische, interactieve kopie** van de
web-UI (laatste versie), met **nagebootste data** in de browser (`mock.js`) — geen backend.
Bedoeld om de interface te tonen; geluid werkt niet (dat vereist de echte server + hardware).

**Live:** https://larspeter1230.github.io/plus-audiosysteem/ (actief zodra de repo publiek is).

## Opnieuw genereren
1. Draai een instantie van de app en haal de gerenderde pagina's op naar `/tmp/demo_src/`
   (`volume.html`, `onboarding.html`, `presets.html`, `tts.html`).
2. `python3 demo/build_demo.py` → schrijft de statische site naar `/tmp/demo/`.
3. Push de inhoud van `/tmp/demo/` naar de `gh-pages`-branch.
