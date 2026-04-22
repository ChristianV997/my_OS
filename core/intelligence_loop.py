def run_intelligence(keywords):
    seen = set()
    ideas = []

    for keyword in keywords or []:
        base = " ".join(str(keyword).strip().split())
        if not base:
            continue
        idea = f"{base.title()} Opportunity"
        if idea not in seen:
            seen.add(idea)
            ideas.append(idea)

    return ideas
