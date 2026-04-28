from src.db_query import Song
from rapidfuzz import fuzz, process


def select_target_for_missing(missing: Song, candidates: list[Song]) -> Song:
    """Try to find a suitable target for the given missing file based on metadata."""
    # exact match
    for row in candidates:
        if row.title == missing.title and row.artist == missing.artist:
            return row

    # fuzzy match on search_text
    choices = [r.search_text for r in candidates]
    results = process.extract_iter(
        missing.search_text, choices, scorer=fuzz.WRatio, score_cutoff=60
    )
    ranked = sorted(results, key=lambda x: x[1], reverse=True)
    # take the best match
    return candidates[ranked[0][2]]
