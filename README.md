# decode-course

A Claude Code skill that **reverse-engineers any paid course / VSL / sales funnel
/ "método" guru offer — without buying it** — into a cited dossier that separates
the real mechanics from the inflated marketing.

It orchestrates other skills across a 7-phase workflow:

1. **Recon** the sales page (surf)
2. **Transcribe the VSL** — the bundled `scripts/vsl_transcribe.py` finds the
   embedded stream (converteai/vturb/Panda/custom HLS), downloads audio-only, and
   transcribes it (**Groq by default**, `--local` for faster-whisper on demand)
3. **OSINT** the real operator (Meta Ad Library + CNPJ + socials)
4. **Deep-research** the model's real mechanics, costs, legality & reputation
5. **Consume** the guru's Instagram/YouTube + any long-form interview
6. **Map the adjacent/international parallel** (Reddit, exposés, regulators)
7. **Synthesize** a dossier (template in `references/playbook.md`)

## Install
```bash
git clone https://github.com/MrIago/decode-course.git ~/.claude/skills/decode-course
```
Then invoke with `/decode-course <url>` or just describe the task ("faz a
engenharia reversa desse curso", "esse método é golpe?").

## Dependencies
Installed skills: **surf**, **consume**, **deep-research**. Tools: `node`,
`ffmpeg`, `python3`. A `GROQ_API_KEY` (in `~/.config/consume/.env`) for fast
transcription. Paths to the orchestrated skills are overridable via
`$DECODE_SURF_DIR` / `$DECODE_CONSUME_DIR`.

## Layout
```
decode-course/
├── SKILL.md                  # frontmatter + the phase workflow
├── scripts/vsl_transcribe.py # find VSL stream → audio → transcript (Groq/local)
└── references/playbook.md    # per-source how-to, OSINT, gotchas, dossier template
```
