Lora (SIL Open Font License 1.1) — self-hosted webfont assets
(docs/DESIGN_SYSTEM.md §3.1).

The implementation sandbox's egress proxy blocked the font CDNs
(Google Fonts / jsDelivr), so the woff2 files could not be fetched at build
time. To enable the exact Lora rendering, download these four files (latin
subset) into this directory using exactly these names:

    lora-normal-400.woff2    lora-normal-500.woff2
    lora-normal-600.woff2    lora-italic-400.woff2

(e.g. from https://fonts.google.com/specimen/Lora → "Download family" →
extract the latin woff2 files).

`ui/app.py` embeds whatever files it finds here as base64 @font-face rules
at startup (runtime, not build time). If the directory is empty, the
design's documented fallback stack ("Iowan Old Style", "Palatino", serif)
renders instead — no other change is needed.
