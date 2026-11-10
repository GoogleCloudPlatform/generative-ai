# html2canvas 1.4.1

[html2canvas](https://html2canvas.hertzen.com) 1.4.1, MIT License. See
[LICENSE](LICENSE).

Used by the widget in voice mode to take low-resolution page snapshots for the
Gemini Live API. `make install` and the Dockerfile run
`scripts/fetch_html2canvas.py`, which downloads the unmodified published
`html2canvas.min.js` into this folder and verifies its SHA-256 digest. The
backend serves it at `/vendor/html2canvas.min.js` so host pages don't load code
from a public CDN at runtime.
