"""Рендер SVG -> PNG через Chromium (Playwright)."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch()
    for src in sys.argv[1:]:
        src = Path(src).resolve()
        svg = src.read_text(encoding='utf-8')
        import re
        w, h = map(float, re.search(r'width="([\d.]+)" height="([\d.]+)"', svg).groups())
        pg = b.new_page(viewport={'width': int(w), 'height': int(h)}, device_scale_factor=2.5)
        pg.set_content(f'<html><body style="margin:0">{svg}</body></html>')
        pg.screenshot(path=str(src.with_suffix('.png')), clip={'x': 0, 'y': 0, 'width': w, 'height': h})
        pg.close()
    b.close()
