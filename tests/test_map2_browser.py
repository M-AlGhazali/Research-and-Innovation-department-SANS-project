"""Map 2 in a real browser: mode menu, default selection, wording and Scenario playback.

Needs Playwright with Chromium (pip install playwright; python -m playwright install chromium); skipped otherwise.
The page is served from this checkout, either as localhost or under a made-up public host name.
"""
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sync_api = pytest.importorskip("playwright.sync_api")
ROOT = Path(__file__).resolve().parents[1]
ARGS = ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
TYPES = {".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json", ".css": "text/css",
         ".html": "text/html", ".svg": "image/svg+xml", ".geojson": "application/json"}


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, **TYPES}

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}/map-2/"
    httpd.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as pw:
        try:
            b = pw.chromium.launch(headless=True, args=ARGS)
        except Exception as e:  # Chromium not installed
            pytest.skip(f"Chromium for Playwright is not available: {e}")
        yield b
        b.close()


def open_map(browser, url, routes=None):
    page = browser.new_page(viewport={"width": 1600, "height": 900})
    requests = []
    page.on("request", lambda r: requests.append(r.url))
    for pattern, handler in (routes or {}).items():
        page.route(pattern, handler)
    page.goto(url)
    page.wait_for_function("window.map2 && window.map2.scenario.getState().recordId", timeout=60000)
    return page, requests


def modes(page):
    return page.eval_on_selector("select[aria-label='Flight mode']", "s=>[...s.options].map(o=>o.value)")


def test_public_site_hides_recorded_mode_and_never_asks_for_its_data(browser):
    def from_disk(route):
        path = route.request.url.split("masar.test/", 1)[1].split("?")[0]
        file = ROOT / path
        if file.is_dir():
            file = file / "index.html"
        if file.is_file():
            route.fulfill(path=str(file), content_type=TYPES.get(file.suffix, "application/octet-stream"))
        else:
            route.fulfill(status=404, body="")
    page, requests = open_map(browser, "http://masar.test/map-2/", {"http://masar.test/**": from_disk})
    page.wait_for_timeout(1000)
    assert modes(page) == ["illustrative", "scenario"]
    assert not [u for u in requests if "observed-data" in u]
    page.close()


def test_recorded_mode_appears_when_the_local_dataset_exists(browser, server):
    manifest = lambda route: route.fulfill(status=200, content_type="application/json", body="{}")
    page, _ = open_map(browser, server, {"**/observed-data/manifest.json": manifest})
    page.wait_for_function("document.querySelector('select[aria-label=\"Flight mode\"] option[value=observed]')", timeout=10000)
    assert modes(page) == ["illustrative", "observed", "scenario"]
    page.close()


def test_opens_in_scenario_mode_with_the_default_selection(browser, server):
    page, _ = open_map(browser, server)
    assert page.eval_on_selector("select[aria-label='Flight mode']", "s=>s.value") == "scenario"
    st = page.evaluate("window.map2.scenario.getState()")
    assert (st["runway"], st["sid"], st["aircraft"], st["recordId"]) == ("34C", "ISLAM 2W", "A320", "34C_ISLAM2W_A320")
    assert page.inner_text("#sources") == "Sources & assumptions"
    # fuel, CO2 and the daily/yearly totals sit in the glass panel on the map, not in the sidebar
    hud = page.locator(".scenario-hud")
    assert hud.is_visible() and "643 kg" in hud.inner_text() and "2,033 kg" in hud.inner_text()
    assert page.locator("section.scenario-panel .scenario-tile").count() == 0
    page.close()


def test_departures_sentence_uses_the_singular_for_one(browser, server):
    page, _ = open_map(browser, server)
    slider = page.locator("section.scenario-panel input[aria-label='Departures per day']")
    sentence = "section.scenario-panel p.scenario-intro >> text=People inside"
    slider.fill("1")
    assert "hear about 1 departure like this a day" in page.inner_text(sentence)
    slider.fill("2")
    assert "hear about 2 departures like this a day" in page.inner_text(sentence)
    page.close()


def test_playback_ends_on_the_saved_totals_and_resets_on_a_new_selection(browser, server):
    record = next(s for s in json.loads((ROOT / "map-2/scenarios/index.json").read_text(encoding="utf-8"))["scenarios"]
                  if s["id"] == "34C_ISLAM2W_A320")
    page, _ = open_map(browser, server)
    page.select_option("select[aria-label='Scenario playback speed']", "60")
    page.click(".scenario-transport button.primary")
    page.wait_for_function("window.map2.scenario.getState().playback.t>0")
    page.wait_for_function(f"window.map2.scenario.getState().playback.t>={record['to10k']['time_s']}", timeout=60000)
    pb = page.evaluate("window.map2.scenario.getState().playback")
    assert pb["playing"] is False
    assert pb["fuel"] == f"{round(record['to10k']['fuel_kg']):,} kg"
    assert pb["co2"] == f"{round(record['to10k']['co2_kg']):,} kg"
    assert pb["altitude"] == "10,000 ft"
    page.locator(".scenario-seg button", has_text="B77W").click()
    page.wait_for_function("window.map2.scenario.getState().recordId==='34C_ISLAM2W_B77W'")
    # the counters redraw on the next animation frame
    page.wait_for_function("window.map2.scenario.getState().playback.fuel==='0 kg'", timeout=10000)
    pb = page.evaluate("window.map2.scenario.getState().playback")
    assert pb["t"] == 0 and pb["fuel"] == "0 kg" and pb["playing"] is False
    page.close()
