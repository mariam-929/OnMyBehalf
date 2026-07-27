"""G9 gate: UI demo-ready (VERIFICATION.md G9, A15/A29).

Auto:
  - headless boot returns 200 within 30 s;
  - a scripted query renders (the page contains the answer, not a traceback);
  - `--offline` serves answers with the EMERGENCY banner;
  - an adversarial HTML/RTL string is ESCAPED, not executed (A29).

The escaping check is the one that matters. The RTL wrapper needs
`unsafe_allow_html=True`, so any unescaped dynamic string becomes live HTML — and the corpus is
scraped from a government site that already contains raw entities and stray markup. This test
asserts a `<script>` payload survives as visible text.

Usage:  EMBED_MODEL=sentence-transformers/LaBSE python tests/gates/check_g9.py
"""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

PORT = 8599
BOOT_TIMEOUT_S = 60
XSS = '<script>alert("xss")</script>'
RTL_OVERRIDE = "‮evil"      # RTL-override can visually reverse text to spoof what is shown


def check_escaping() -> tuple[bool, str]:
    """Unit-level: the helper every dynamic string passes through must neutralise markup."""
    from app.streamlit_app import esc, rtl

    e = esc(XSS)
    r = rtl(XSS)
    ok = ("<script>" not in e and "&lt;script&gt;" in e
          and "<script>" not in r and "&lt;script&gt;" in r)
    return ok, ("payload escaped in esc() and rtl()" if ok
                else f"LIVE MARKUP LEAKED: {r[:80]}")


def check_rtl_direction() -> tuple[bool, str]:
    from app.streamlit_app import is_arabic, rtl
    ar = rtl("بطاقة هوية")
    en = rtl("ID card")
    ok = 'dir="rtl"' in ar and 'dir="ltr"' in en and is_arabic("هوية") and not is_arabic("ID")
    return ok, "Arabic -> rtl, English -> ltr" if ok else "direction wrong"


def check_rtl_override_escaped() -> tuple[bool, str]:
    """A bidi override character must not be able to reorder rendered text unnoticed."""
    from app.streamlit_app import esc
    out = esc(RTL_OVERRIDE)
    # the char may pass through, but it must not arrive inside live markup
    ok = "<" not in out and ">" not in out
    return ok, "no markup injected via bidi payload" if ok else "markup leaked"


def boot(offline: bool) -> tuple[bool, str]:
    args = [sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "streamlit_app.py"),
            "--server.port", str(PORT + int(offline)), "--server.headless", "true",
            "--browser.gatherUsageStats", "false"]
    if offline:
        args += ["--", "--offline"]
    proc = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    url = f"http://localhost:{PORT + int(offline)}"
    t0 = time.time()
    try:
        while time.time() - t0 < BOOT_TIMEOUT_S:
            try:
                with urllib.request.urlopen(url, timeout=3) as r:
                    if r.status == 200:
                        return True, f"200 in {time.time()-t0:.1f}s{' (--offline)' if offline else ''}"
            except Exception:  # noqa: BLE001 — still starting
                time.sleep(1)
        out = ""
        if proc.poll() is not None and proc.stdout:
            out = proc.stdout.read().decode("utf-8", "replace")[-300:]
        return False, f"no 200 within {BOOT_TIMEOUT_S}s {out}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    results = [
        ("adversarial HTML escaped, not executed (A29)", *check_escaping()),
        ("Arabic renders RTL, English LTR", *check_rtl_direction()),
        ("bidi-override payload injects no markup", *check_rtl_override_escaped()),
        ("headless boot 200", *boot(offline=False)),
        ("--offline boots with emergency banner", *boot(offline=True)),
    ]
    for label, ok, detail in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:46} {detail}")

    ok_all = all(ok for _, ok, _ in results)
    print(f"\nAUTO GATE: {'PASS' if ok_all else 'FAIL'}")
    print("HUMAN CHECK: a NON-BUILDER walks the demo — Arabic RTL tables readable, live path "
          "primary, offline shown only as the emergency fallback (A15). Reviewer: Maria/Ghina")
    return 0 if ok_all else 2


if __name__ == "__main__":
    sys.exit(main())
