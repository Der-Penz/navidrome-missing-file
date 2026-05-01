from typing import List, Tuple
from rapidfuzz import fuzz, utils
from src.db_query import Song


def _norm(s: str) -> str:
    """Normalize text for consistent matching."""
    return utils.default_process(s or "")


def _song_score(song, q: str) -> int:
    title = _norm(song.title)
    artist = _norm(song.artist)
    album = _norm(song.album)

    full = f"{title} {artist} {album}"

    score = 0

    if q == title:
        score += 300
    elif q in title:
        score += 250
    elif title.startswith(q):
        score += 220

    q_words = q.split()
    title_words = title.split()

    if q_words and all(any(tw.startswith(qw) for tw in title_words) for qw in q_words):
        score += 200

    if q in artist:
        score += 180
    elif artist.startswith(q):
        score += 160

    if q in album:
        score += 120

    score += int(fuzz.partial_ratio(q, title) * 0.8)
    score += int(fuzz.token_set_ratio(q, full) * 0.4)

    return score


def fuzzy_filter_songs(
    songs: List[Song],
    query: str,
    score_cutoff: int = 60,
) -> List[Song]:
    """
    Filter and rank songs using fuzzy matching.

    Args:
        songs: List of Song objects
        query: User search string
        score_cutoff: Minimum score to include results

    Returns:
        List of songs sorted by relevance
    """
    q = _norm(query)

    if not q:
        return songs[:]

    scored: List[Tuple[int, object]] = []

    for song in songs:
        score = _song_score(song, q)
        if score >= score_cutoff:
            scored.append((score, song))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [song for _, song in scored]
