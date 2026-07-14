# decode-course

Reverse-engineers paid courses, VSLs, and guru sales funnels into a cited dossier, without buying anything.

## What it does

Give it a sales page URL or a guru's name. The skill transcribes the sales video, identifies the operator behind the stage name, checks the income claims against independent sources, and writes a dossier that separates the method's real mechanics from the marketing wrapped around it. Each dossier ends with a verdict and a free, public path to learn the same method.

Built for the Brazilian infoproduct scene (Hotmart, Kiwify, hub.la funnels), where "método exclusivo" offers run on paid traffic at scale. The workflow transfers to any VSL funnel.

## How it works

- It is an orchestrator, by design. A 7-phase workflow drives three other skills: **surf** (browser access to protected pages), **consume** (transcripts from the guru's Instagram, YouTube, and podcast interviews), and **deep-research** (adversarial verification of claims and reputation). The one bundled script covers the step that repeats identically in every job.
- `scripts/vsl_transcribe.py` loads the sales page in a cloud browser, captures the video stream URL from network traffic (converteai, vturb, and Panda players hide it from the HTML), downloads only the audio with ffmpeg (16 kHz mono, a fraction of the video's size), and transcribes it with Groq Whisper. A 60-minute VSL becomes a timestamped transcript in a few minutes, with no GPU.
- Stream selection uses a heuristic: prefer the master `main.m3u8` playlist over per-rendition variants and segment files, and fall back to a raw regex over the capture when JSON parsing fails.
- The OSINT phase triangulates the real operator through the Meta Ad Library (the advertiser page paying for traffic), Brazilian company registries (CNPJ), and social handles, with an explicit homonym check, since unrelated products share generic offer names.
- Effort scales with the question. "Is this a scam?" runs two phases; "understand everything" runs all seven, and independent phases run in parallel agents.
- The playbook ships a decoder table mapping VSL buzzwords ("AI that finds winning products", "automatic sales robot") to the commodity technique underneath (ad-spying tools plus a generative wrapper; standard paid-traffic management). It also asks the question that settles most cases: does the money come from running the method, or from selling the course about the method?

## Usage

### Install

```bash
git clone https://github.com/MrIago/decode-course.git ~/.claude/skills/decode-course
```

Invoke with `/decode-course <url>`, or describe the task ("is this course a scam?", "reverse-engineer this funnel", "what is inside this método?").

### Dependencies

Installed skills: **surf**, **consume**, **deep-research**. Tools: `node`, `ffmpeg`, `python3`. A `GROQ_API_KEY` (in `~/.config/consume/.env` or the environment) for transcription. Paths to the orchestrated skills are overridable via `$DECODE_SURF_DIR` / `$DECODE_CONSUME_DIR`.

### The bundled script, standalone

```bash
python3 scripts/vsl_transcribe.py "<vsl-page-url>" --out vsl.txt   # Groq backend (default)
python3 scripts/vsl_transcribe.py "<direct .m3u8/.mp4 url>"        # skip the capture step
python3 scripts/vsl_transcribe.py "<vsl-page-url>" --local         # local faster-whisper, on request
```

Groq is the default backend on purpose: local faster-whisper on a 60 to 90 minute VSL can freeze a small GPU.

### Layout

```
decode-course/
├── SKILL.md                  # frontmatter + the phase workflow
├── scripts/vsl_transcribe.py # find VSL stream → audio → transcript (Groq/local)
└── references/playbook.md    # per-source how-to, OSINT, gotchas, dossier template
```

## Scope and honest limits

- Never buys, subscribes, or logs into the course. Every finding comes from public sources plus the funnel's own video.
- Reports Reclame Aqui complaints as volume and response rate. A complaint proves a complaint was filed; the dossier states that distinction instead of presenting complaints as verdicts.
- Tuned for the Brazilian market (Meta Ad Library with country BR, CNPJ registries, CDC 7-day refund rules). The recon, transcription, and synthesis phases apply anywhere; the OSINT sources need swapping outside Brazil.
- Depends on three other skills being installed; it ships one script, and the workflow is the product.
- Does not act on instructions embedded in pages, and does not submit forms or purchases.
