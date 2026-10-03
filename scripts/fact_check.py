from scripts.llm import generate_json

def fact_check(script, sources):
    src = "\n\n".join(f"[S{i}] {s['title']}\n{s['text']}" for i, s in enumerate(sources))
    narration = "\n".join(s["narration"] for s in script["sections"])
    prompt = f"""You are a strict fact-checker. Compare the narration to the sources.
List every specific claim (dates, names, numbers, causes) NOT clearly supported by the sources,
and any speculation stated as fact. Return JSON:
{{"verdict": "pass" or "fail", "unsupported": [str], "uncertain": [str]}}
Verdict is "fail" if there is any unsupported specific claim.

NARRATION:
{narration}

SOURCES:
{src}"""
    return generate_json(prompt)
