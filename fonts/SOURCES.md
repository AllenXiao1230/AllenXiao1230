# Embedded fonts

- Instrument Serif Regular: [Google Fonts source](https://github.com/google/fonts/tree/main/ofl/instrumentserif), `InstrumentSerif-OFL.txt`.
- DM Sans Regular and SemiBold: [Google Fonts source](https://github.com/google/fonts/tree/main/ofl/dmsans), `DMSans-OFL.txt`.
- Noto Sans TC Regular: [Google Fonts source](https://github.com/google/fonts/tree/main/ofl/notosanstc), `NotoSansTC-OFL.txt`.
- IBM Plex Mono SemiBold: [Google Fonts source](https://github.com/google/fonts/tree/main/ofl/ibmplexmono), `IBMPlexMono-OFL.txt`. Used for the real ASCII portrait text.

The Latin fonts are subset to printable ASCII and selected punctuation. The Chinese font is subset to this README's actual copy. All are embedded in the SVG files as WOFF2 data URIs. The SIL Open Font License files must accompany redistributed font files.

To add Chinese characters, run `python scripts/prepare_chinese_font.py` after changing `locales.json`. The helper fetches an exact text subset from the official Google Fonts service and only needs the Python standard library. It runs during the refresh workflow as well, so changed translations receive the necessary glyphs before rendering.
