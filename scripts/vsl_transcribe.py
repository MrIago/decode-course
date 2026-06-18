#!/usr/bin/env python3
"""decode-course — find a VSL's video stream and transcribe it.

The fiddly, identical-every-time step of reverse-engineering an infoproduct
funnel: an arbitrary sales/"aula" page embeds a video (usually a converteai /
vturb / Panda smartplayer) whose HLS stream lives on a public CDN. This script:

  1. loads the page in a real browser (surf's cf_cdp) and CAPTURES the video
     stream URL from the network (m3u8/mp4),
  2. downloads ONLY THE AUDIO with ffmpeg (small + fast),
  3. transcribes it with consume's transcribe.py.

Its stdout IS the result: the timestamped transcript ([MM:SS] text). All
diagnostics go to stderr.

USAGE
  python3 vsl_transcribe.py "<vsl-page-url>"            # Groq (default)
  python3 vsl_transcribe.py "<page-url>" --local        # local faster-whisper
  python3 vsl_transcribe.py "<direct .m3u8/.mp4 url>"   # skip the capture step
  python3 vsl_transcribe.py "<url>" --out vsl.txt --keep --referer https://site/

TRANSCRIPTION BACKEND
  Default is **Groq** (WATCH_TRANSCRIBE=groq) — fast, chunked, no GPU. This is the
  right default: local faster-whisper of a long VSL can OOM/freeze a small GPU.
  Pass --local only when explicitly asked (or on a machine with a capable GPU and
  no GROQ_API_KEY). consume's transcribe.py reads GROQ_API_KEY from the env or
  ~/.config/consume/.env.

DEPENDENCIES (this skill orchestrates other installed skills)
  - surf skill   → scripts/cf_cdp.mjs   (override dir with $DECODE_SURF_DIR)
  - consume skill→ scripts/lib/transcribe.py (override with $DECODE_CONSUME_DIR)
  - node, ffmpeg, python3 on PATH.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

HOME = Path.home()
SURF_DIR = Path(os.environ.get("DECODE_SURF_DIR", HOME / ".claude/skills/surf"))
CONSUME_DIR = Path(os.environ.get("DECODE_CONSUME_DIR", HOME / ".claude/skills/consume"))

STREAM_RE = re.compile(r"https?://[^\s\"']+?\.(?:m3u8|mp4)(?:\?[^\s\"']*)?", re.I)


def err(msg: str) -> None:
    print(f"[decode] {msg}", file=sys.stderr)


def die(msg: str, code: int = 1):
    err(msg)
    raise SystemExit(code)


def check(tool: str, hint: str):
    from shutil import which
    if which(tool) is None:
        die(f"'{tool}' not found on PATH — {hint}")


def capture_stream(url: str, wait_ms: int) -> str:
    """Drive the page in a real browser and return the best video-stream URL."""
    script = SURF_DIR / "scripts" / "cf_cdp.mjs"
    if not script.exists():
        die(f"surf's cf_cdp.mjs not found at {script}. Install the surf skill or "
            f"set $DECODE_SURF_DIR. (Or pass a direct .m3u8/.mp4 URL.)")
    err(f"capturing video stream from {url} (real browser, {wait_ms}ms)…")
    cmd = ["node", str(script), "--url", url, "--consent",
           "--capture-net", r"m3u8|mp4|converteai|panda|vturb|cdn|playlist|video",
           "--wait", str(wait_ms)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        die("browser capture timed out (180s).")
    blob = (p.stdout or "") + "\n" + (p.stderr or "")
    # Prefer parsing the JSON 'network' list; fall back to raw regex over all output.
    urls: list[str] = []
    try:
        data = json.loads(p.stdout)
        net = data.get("network") or data.get("net") or []
        for entry in net:
            urls += STREAM_RE.findall(entry if isinstance(entry, str) else json.dumps(entry))
    except Exception:
        pass
    if not urls:
        urls = STREAM_RE.findall(blob)
    if not urls:
        die("no video stream (.m3u8/.mp4) seen on the page. Try a larger --wait, or "
            "inspect manually with surf's cf_cdp.mjs --capture-net. If it's a known "
            "platform (YouTube/Instagram/TikTok), use the consume skill instead.")
    return pick_stream(urls)


def pick_stream(urls: list[str]) -> str:
    """Choose the master playlist over variant/segment playlists and stray mp4s."""
    seen = list(dict.fromkeys(urls))  # dedupe, keep order
    m3u8 = [u for u in seen if ".m3u8" in u.lower()]
    # master playlists usually 'main.m3u8'; drop per-rendition 'video_0.m3u8' & segments
    masters = [u for u in m3u8 if "main.m3u8" in u.lower()]
    variants = [u for u in m3u8 if not re.search(r"video_\d+\.m3u8|/segment", u, re.I)]
    chosen = (masters or variants or m3u8 or [u for u in seen if u.lower().endswith(".mp4")] or seen)[0]
    err(f"stream: {chosen}")
    return chosen


def download_audio(stream: str, referer: str, work: Path) -> Path:
    out = work / "vsl_audio.mp3"
    err("downloading audio only (16k mono mp3)…")
    headers = f"Referer: {referer}\r\n" if referer else None
    cmd = ["ffmpeg", "-y", "-loglevel", "warning"]
    if headers:
        cmd += ["-headers", headers]
    cmd += ["-i", stream, "-vn", "-ar", "16000", "-ac", "1", "-b:a", "64k", str(out)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0 or not out.exists():
        die(f"ffmpeg failed to fetch audio.\n{p.stderr[-800:]}")
    mb = out.stat().st_size / 1e6
    err(f"audio: {out.name} ({mb:.1f} MB)")
    return out


def transcribe(audio: Path, local: bool) -> str:
    tscript = CONSUME_DIR / "scripts" / "lib" / "transcribe.py"
    if not tscript.exists():
        die(f"consume's transcribe.py not found at {tscript}. Install the consume "
            f"skill or set $DECODE_CONSUME_DIR.")
    backend = "local" if local else "groq"
    err(f"transcribing via {backend} (consume)…")
    if local:
        err("note: local faster-whisper can OOM/freeze a small GPU on a long VSL; "
            "Groq is the safer default.")
    env = {**os.environ, "WATCH_TRANSCRIBE": backend}
    p = subprocess.run([sys.executable, str(tscript), str(audio)],
                       capture_output=True, text=True, env=env)
    if p.returncode != 0 or not (p.stdout or "").strip():
        die(f"transcription failed (backend={backend}).\n{p.stderr[-800:]}")
    return p.stdout.rstrip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Find a VSL's stream and transcribe it.")
    ap.add_argument("url", help="VSL/sales page URL, or a direct .m3u8/.mp4 URL")
    ap.add_argument("--local", action="store_true", help="use local faster-whisper instead of Groq")
    ap.add_argument("--out", help="write transcript to this file (also printed)")
    ap.add_argument("--referer", help="Referer header for the CDN (default: page origin)")
    ap.add_argument("--wait", type=int, default=9000, help="ms to let the player load (default 9000)")
    ap.add_argument("--keep", action="store_true", help="keep the temp audio dir")
    args = ap.parse_args()

    check("ffmpeg", "install ffmpeg (e.g. `sudo apt install ffmpeg`)")

    direct = bool(re.search(r"\.(m3u8|mp4)(\?|$)", args.url, re.I))
    if not direct:
        check("node", "install Node.js (the surf skill needs it)")
    stream = args.url if direct else capture_stream(args.url, args.wait)

    referer = args.referer
    if referer is None:
        src = args.url if not direct else stream
        u = urlparse(src)
        referer = f"{u.scheme}://{u.netloc}/" if u.scheme and u.netloc else ""

    work = Path(tempfile.mkdtemp(prefix="decode-vsl-"))
    try:
        audio = download_audio(stream, referer, work)
        text = transcribe(audio, args.local)
    finally:
        if not args.keep:
            from shutil import rmtree
            rmtree(work, ignore_errors=True)
        else:
            err(f"temp kept: {work}")

    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        err(f"saved transcript → {args.out} ({text.count(chr(10)) + 1} lines)")
    print(text)
    return 0


if __name__ == "__main__":
    try:
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError, ValueError):
        pass
    raise SystemExit(main())
