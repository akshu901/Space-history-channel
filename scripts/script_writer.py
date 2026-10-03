from config.settings import TARGET_WORDS
from scripts.llm import generate_json

STRUCTURE = ["hook", "intro", "main", "details", "conclusion", "cta"]

def build_prompt(topic, angle, sources, feedback=None):
    src = "\n\n".join(f"[S{i}] {s['title']} ({s['url']})\n{s['text']}" for i, s in enumerate(sources))
    fb = f"\nA previous draft failed fact-check. Fix these problems:\n{feedback}\n" if feedback else ""
    return f"""You write narration for a faceless YouTube channel about US space and science history.
Topic: {topic}
Angle: {angle}
Use ONLY facts found in the sources below. If something is uncertain or disputed, say so plainly.
Do not invent quotes, dates, or numbers. No clickbait, no hype that the facts don't support.
Style: natural American English, conversational, short sentences, varied rhythm, no filler phrases like "buckle up".
Length: about {TARGET_WORDS} words total. Spell out numbers and abbreviations so a TTS voice reads them right.
Return JSON: {{"title": str, "sections": [{{"name": one of {STRUCTURE}, "narration": str, "visual_hint": str}}],
"claims": [{{"claim": str, "source": "S0"}}]}}
Sections must appear in exactly this order: {STRUCTURE}.
The last section (cta) is one short sentence asking viewers to subscribe if they enjoyed it.
{fb}
SOURCES:
{src}"""

def write_script(topic, angle, sources, feedback=None):
    data = generate_json(build_prompt(topic, angle, sources, feedback))
    names = [s["name"] for s in data["sections"]]
    if names != STRUCTURE:
        raise ValueError(f"Bad section order: {names}")
    return data

def word_count(script):
    return sum(len(s["narration"].split()) for s in script["sections"])
