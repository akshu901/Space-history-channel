import json
from config.settings import TARGET_WORDS
from scripts.llm import generate_json

STRUCTURE = ["hook", "intro", "main", "details", "conclusion", "cta"]
MIN_WORDS, MAX_WORDS = 700, 1300


def build_prompt(topic, angle, sources, feedback=None, previous=None):
    src = "\n\n".join(f"[S{i}] {s['title']} ({s['url']})\n{s['text']}" for i, s in enumerate(sources))
    rules = f"""You write narration for a faceless YouTube channel about US space and science history.
Topic: {topic}
Angle: {angle}

STRICT FACT RULES:
- Use ONLY facts that are written in the sources below. If it is not in the sources, leave it out.
- Do NOT add anything about people's lives after the mission (deaths, ages, later careers) unless a source says it.
- Do NOT add specific numbers, materials, colors, or causes that the sources do not state.
- Do not invent quotes, dates, or numbers. If something is uncertain or disputed, say so plainly.
- No clickbait, no hype that the facts don't support.

STYLE: natural American English, conversational, short sentences, varied rhythm, no filler phrases like "buckle up".
LENGTH: about {TARGET_WORDS} words total. It MUST be between {MIN_WORDS} and {MAX_WORDS} words. Too short counts as a failure.
Spell out numbers and abbreviations so a TTS voice reads them right.
Return JSON: {{"title": str, "sections": [{{"name": one of {STRUCTURE}, "narration": str, "visual_hint": str}}],
"claims": [{{"claim": str, "source": "S0"}}]}}
Sections must appear in exactly this order: {STRUCTURE}.
The last section (cta) is one short sentence asking viewers to subscribe if they enjoyed it."""

    if previous and feedback:
        task = f"""
REVISION TASK. Here is your previous draft:
{json.dumps(previous, indent=1)}

It failed review. Problems:
{feedback}

Revise the draft. Change ONLY what is needed to fix these problems:
- Delete or rewrite every sentence containing an unsupported claim.
- Keep all other text as it is. Do not shorten the script.
- If the length is the problem, expand with more facts that appear in the sources.
Return the full revised JSON.
"""
    else:
        task = ""
    return f"{rules}\n{task}\nSOURCES:\n{src}"


def write_script(topic, angle, sources, feedback=None, previous=None):
    data = generate_json(build_prompt(topic, angle, sources, feedback, previous))
    names = [s["name"] for s in data["sections"]]
    if names != STRUCTURE:
        raise ValueError(f"Bad section order: {names}")
    return data


def word_count(script):
    return sum(len(s["narration"].split()) for s in script["sections"])
