def compute_tier_score(financial_materiality: int, regulatory_nexus: bool,
                        complexity: int, population_size: int) -> dict:
    score = 0
    score += financial_materiality * 20
    score += 20 if regulatory_nexus else 0
    score += complexity * 10
    if population_size > 100000:
        score += 20
    elif population_size > 10000:
        score += 10
    else:
        score += 5

    if score >= 80:
        tier = 1
        rationale = "High financial materiality, regulatory nexus, and/or model complexity — Tier 1 (Highest Risk)"
    elif score >= 50:
        tier = 2
        rationale = "Moderate impact and complexity — Tier 2 (Significant)"
    else:
        tier = 3
        rationale = "Lower impact/complexity — Tier 3 (Standard)"

    return {'tier': tier, 'score': float(score), 'rationale': rationale}
