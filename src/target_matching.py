from src.db_query import Song
from src.fuzzy_search import fuzzy_filter_songs


def select_target_for_missing(missing: Song, candidates: list[Song]) -> Song:
    """Try to find a suitable target for the given missing file based on metadata."""
    # exact match
    ranked = fuzzy_filter_songs(candidates, missing.search_text, score_cutoff=100)

    return ranked[0] if ranked else candidates[0]
