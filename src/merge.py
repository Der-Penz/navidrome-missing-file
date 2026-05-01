# make me a merge protocol class that has one merge function and takes source and target as arguments. The merge function should be able to handle the merging logic and return the merged result. The class should also

from dataclasses import dataclass
from typing import Protocol

from src.db_query import Annotation


class Merge(Protocol):
    def merge(self, source: Annotation, target: Annotation) -> Annotation:
        """Merge the source and target dictionaries and return the merged result."""
        ...


class AddMerge(Merge):
    def merge(self, source: Annotation, target: Annotation) -> Annotation:
        """Merge by adding values from source to target."""

        play_count = source.play_count + target.play_count
        rating = max(source.rating, target.rating)
        starred = source.starred or target.starred
        starred_at = source.starred_at if source.starred_at else target.starred_at
        rated_at = source.rated_at if source.rated_at else target.rated_at

        return Annotation(
            play_count=play_count,
            rating=rating,
            starred=starred,
            starred_at=starred_at,
            rated_at=rated_at,
            user_id=source.user_id,
        )


class ReplaceMerge(Merge):
    def merge(self, source: Annotation, target: Annotation) -> Annotation:
        """Merge by taking all values from source, ignoring target."""
        return Annotation(**source.__dict__)


MERGE_STRATEGIES: dict[str, Merge] = {
    "add": AddMerge(),
    "overwrite": ReplaceMerge(),
}
