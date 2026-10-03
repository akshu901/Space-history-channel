from scripts.llm import generate_json

def fact_check(script, sources):
    src = "\n\n".join(f"[S{i}] {s['title']}\n{s['text']}" for i, s in enumerate(sources))
    narration = "\n".join(s["narration"] for s in script["sections"])
    prompt = f"""You are a strict fact-checker. Compare the narration to the sources.
List specific factual claims (dates, names, numbers, causes) that are NOT stated in the sources
and do not follow directly from them, plus any speculation stated as fact.
Do NOT flag dramatic phrasing, scene-setting, or paraphrases of facts that the sources do state.
Search the WHOLE of each source before deciding a claim is unsupported. Return JSON:
{{"verdict": "pass" or "fail", "unsupported": [str], "uncertain": [str]}}
Verdict is "fail" if there is any unsupported specific claim.

NARRATION:
{narration}

SOURCES:
{src}"""
    return generate_json(prompt)
