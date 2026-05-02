# RxSentinel — Demo Video Script (4 minutes)

**Hard rule from the assignment:** must not exceed 5 minutes. We target 4:00.

The video should illustrate the full workflow: input → agents executing → tool
calls → final report. Every architectural component (multi-agent, tools,
state, observability) must be visible at least once.

## Pre-recording checklist

1. `ollama serve` running, `qwen2.5:3b` already loaded (do a warm-up run first
   so the first demo run isn't slow).
2. `cd backend && python -m uvicorn rxsentinel.app:app` (port 8000) running.
3. `cd frontend && pnpm dev` (port 3000) running.
4. Browser at http://localhost:3000 with **dark mode default**.
5. Browser zoom **125%** for legibility on the recording.
6. Close all unnecessary tabs/apps. Hide bookmarks bar. Clean wallpaper.
7. Test mic level. Speak naturally; you're a developer demoing your work.
8. Have a clean test input ready — a known-severe combo (warfarin + ibuprofen
   + amiodarone) so the pipeline produces visible red flags.

## Recommended test input (drama-friendly)

```
warfarin 5mg daily, amiodarone 200mg twice daily, ibuprofen 400mg as needed for joint pain, simvastatin 40mg, clarithromycin 500mg twice daily for chest infection
```

This produces ~5 high-severity interactions (warfarin+ibuprofen, amiodarone+
warfarin, amiodarone+simvastatin, simvastatin+clarithromycin) and demonstrates
the full severity ladder.

---

## Section-by-section script

### [0:00 — 0:30] Opening + problem (30s)

**Visual:** Landing page in dark mode, RxSentinel logo, hero headline animating in.

**Voiceover (read at conversational pace):**

> "Adverse drug events are one of the top five preventable causes of hospital
> admission. Yet the tools clinicians use to catch them — Lexicomp, Micromedex —
> are paid, gated, and online. We built RxSentinel: a multi-agent system that
> performs medication safety reviews entirely on your laptop. No paid APIs.
> No data leaving your machine. Just four AI agents, working together."

### [0:30 — 1:00] Architecture explainer (30s)

**Visual:** Quick cut to architecture diagram (from the report) overlaid on
the page, with the four agent cards highlighting one at a time.

**Voiceover:**

> "Four agents, orchestrated by LangGraph. The Coordinator validates input
> and routes. The Med Parser normalizes drug names against the NIH RxNorm
> database. The Interaction Analyzer checks every drug pair against openFDA
> adverse-event data and our curated severe-interaction database. And the
> Patient Communicator translates findings into plain English at a sixth-
> grade reading level."

### [1:00 — 1:30] Submitting the input (30s)

**Visual:** Cursor moves to the textarea. Click the example chip OR type live
(typing live is more authentic but takes ~25 seconds — pre-fill via the chip
to save time).

**Voiceover:**

> "Let's run a real example: a patient on warfarin, amiodarone, ibuprofen,
> simvastatin, and clarithromycin. A combination you'd see in a primary care
> clinic — and one that's quietly dangerous."

Click "Run safety review."

### [1:30 — 2:30] Live agent pipeline (60s — this is the money shot)

**Visual:** The agent pipeline cards animate one by one. Each card pulses
cyan when active, shows the tool it's currently calling (rxnorm_lookup,
check_interaction, query_openfda), and timestamps when it finishes.

**Voiceover (sync with what's on screen):**

> "And we're off. The Coordinator validates the input — under a hundred
> milliseconds, no LLM call needed for that. Now the Med Parser is calling
> the LLM to extract candidate medications, then making parallel RxNorm
> lookups to assign canonical drug codes. You can see five medications
> recognized in the trace.
>
> Now the Interaction Analyzer kicks in. It builds every unique pair —
> ten pairs from five drugs — and queries each one. Notice the local
> database catches the warfarin-ibuprofen pair instantly, while openFDA
> adds a population-level signal on co-mention rates.
>
> And finally the Patient Communicator drafts a summary. It runs Flesch-
> Kincaid on its own draft, and if the grade level's too high it rewrites
> until it hits sixth grade."

### [2:30 — 3:15] Final report (45s)

**Visual:** Scroll through the bento layout — severity dial, medications
parsed, interactions table with red/yellow/green badges, patient summary,
limitations.

**Voiceover:**

> "Here's the report. Five high-severity interactions detected, color-coded.
> Each interaction shows the mechanism — why it's dangerous — and a clinical
> recommendation. Below, the patient-friendly summary at a sixth-grade
> reading level. And in the corner, the readability grade and request ID for
> traceability.
>
> The whole pipeline ran in under twelve seconds on an M2 MacBook Air with
> eight gigs of RAM. Quantized qwen-2.5 3B doing all the reasoning, fully
> offline."

### [3:15 — 3:45] Observability + tests (30s)

**Visual:** Click "Trace" to expand the JSONL trace. Show timestamps + tool
calls scrolling by. Then briefly tab to terminal showing `pytest -v` passing
all unit tests.

**Voiceover:**

> "Every agent step and every tool call is captured in a JSONL trace —
> streamed to the UI live via Server-Sent Events. We also wrote a full test
> harness: unit tests for every tool, plus an LLM-as-Judge evaluation suite
> for every agent, all running against the same local model."

### [3:45 — 4:00] Closing (15s)

**Visual:** GitHub link in header. Quick fade to logo + "Built by 4 students
for SE4010 CTSE" credit.

**Voiceover:**

> "Built with LangGraph, FastAPI, Next.js fifteen, and Ollama. All open
> source, all local, all free. Four agents on watch — for medication harm.
> Thanks for watching."

---

## Recording tips

- **Use Loom or QuickTime + a USB mic.** Built-in MacBook mic is acceptable
  but a USB mic sounds more professional.
- **Record in 1080p minimum.** 1440p preferred if disk space allows.
- **Do one full take per scene** rather than a single long take. Stitch in
  iMovie or DaVinci Resolve. Easier to redo a section if you flub a line.
- **Pre-warm the model** with a dummy run 2 minutes before recording. First
  Ollama call after a long idle is ~5s slower than steady-state.
- **Mute notifications** (`Do Not Disturb` mode on macOS).
- **Hide your dock** during recording (System Settings → Desktop & Dock → Auto-hide).
