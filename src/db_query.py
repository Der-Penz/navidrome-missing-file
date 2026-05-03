from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import sqlite3
import logging


@dataclass
class Song:
    id: str
    title: str
    album: str
    artist: str
    path: str
    search_text: str


@dataclass
class Playlist:
    id: str
    name: str


@dataclass
class User:
    id: str
    name: str


@dataclass
class Annotation:
    play_count: int
    rating: int
    starred: bool
    starred_at: datetime | None
    rated_at: datetime | None
    user_id: str


class DBQuery:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path)

    def __enter__(self):
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.cur = self.connection.cursor()
        logging.debug(f"Connected to database at {self.db_path}")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.connection.close()

    def find_files(self, missing: int) -> list[Song]:
        self.cur.execute(
            """
            SELECT id, title, album, artist, path
            FROM media_file
            WHERE missing = ?
            ORDER BY path
            """,
            (missing,),
        )

        rows = self.cur.fetchall()
        logging.debug(f"Found {len(rows)} files with missing={missing}")

        songs: list[Song] = []
        for r in rows:
            title = (r["title"] or "").strip()
            album = (r["album"] or "").strip()
            artist = (r["artist"] or "").strip()
            path = r["path"] or ""
            search_text = f"{title} {album} {artist}".lower()
            songs.append(
                Song(
                    id=r["id"],
                    title=title,
                    album=album,
                    artist=artist,
                    path=path,
                    search_text=search_text,
                )
            )
        return songs

    def get_users(self) -> list[User]:
        self.cur.execute(
            """
            SELECT id, name
            FROM user
            """,
        )

        rows = self.cur.fetchall()
        logging.debug(f"Found {len(rows)} users in the database")

        users: list[User] = []
        for r in rows:
            users.append(
                User(
                    id=r["id"],
                    name=r["name"],
                )
            )
        return users

    def get_annotation(self, song: Song, user: User) -> Annotation | None:
        self.cur.execute(
            """
        SELECT *
        FROM annotation
        WHERE item_id = ? AND user_id = ?
        LIMIT 1
        """,
            (song.id, user.id),
        )

        row = self.cur.fetchone()

        if row is None:
            return None
        annotation = Annotation(
            play_count=row["play_count"],
            rating=row["rating"],
            starred=row["starred"],
            starred_at=row["starred_at"],
            rated_at=row["rated_at"],
            user_id=row["user_id"],
        )
        logging.debug(
            f"found annotation for {song.id} from user {user.name}: {annotation}"
        )
        return annotation

    def create_annotation(self, song: Song, annot: Annotation):
        logging.debug(
            f"Creating annotation for {song.id} and user {annot.user_id}: {annot}"
        )
        self.cur.execute(
            """
            INSERT INTO annotation (item_id, item_type, user_id, play_count, rating, starred, starred_at, rated_at)
            VALUES (?, 'media_file', ?, ?, ?, ?, ?, ?)
            """,
            (
                song.id,
                annot.user_id,
                annot.play_count,
                annot.rating,
                annot.starred,
                annot.starred_at,
                annot.rated_at,
            ),
        )

    def set_annotation(self, song: Song, annot: Annotation, user: User):
        logging.debug(f"Setting annotation for {song.id} and user {user.id}: {annot}")

        self.cur.execute(
            """
            UPDATE annotation
            SET
                play_count = ?,
                rating = ?,
                starred = ?,
                starred_at = ?,
                rated_at = ?
            WHERE
                user_id = ?
                AND item_id = ?
                AND item_type = 'media_file'
            """,
            (
                annot.play_count,
                annot.rating,
                annot.starred,
                annot.starred_at,
                annot.rated_at,
                user.id,
                song.id,
            ),
        )

        if self.cur.rowcount == 0:
            self.create_annotation(song, annot)

    def delete_annotation(self, song: Song, user: User):
        logging.debug(f"Deleting annotation for {song.id} and user {user.id}")
        self.cur.execute(
            """
            DELETE FROM annotation
            WHERE user_id = ?
            AND item_id = ?
            AND item_type = 'media_file'
            """,
            (user.id, song.id),
        )

    def delete_media_file(self, song: Song):
        logging.debug(f"Deleting media file with id: {song.id}")
        self.cur.execute("DELETE FROM media_file WHERE id = ?", (song.id,))

    def get_playlists_of_song(self, song: Song) -> list[Playlist]:
        self.cur.execute(
            """
            SELECT p.id, p.name
            FROM playlist_tracks pt
            JOIN playlist p ON p.id = pt.playlist_id
            WHERE pt.media_file_id = ?
            AND p.rules IS NULL
            """,
            (song.id,),
        )
        rows = self.cur.fetchall()
        logging.debug(f"Found playlists for media_file_id {song.id}: {len(rows)}")

        playlists: list[Playlist] = []
        for r in rows:
            playlists.append(
                Playlist(
                    id=r["id"],
                    name=r["name"],
                )
            )
        return playlists

    def add_to_playlist(
        self, playlist: Playlist, song: Song, playlist_position: int = None
    ):
        logging.debug(
            f"Adding item {song.id} to playlist {playlist.id} at position {playlist_position}"
        )
        self.cur.execute(
            """
            INSERT INTO playlist_tracks (playlist_id, media_file_id, id)
            VALUES (?, ?, ?)
            """,
            (playlist.id, song.id, playlist_position),
        )

    def remove_from_playlist(self, playlist: Playlist, song: Song):
        logging.debug(f"Removing item {song.id} from playlist {playlist.id}")
        self.cur.execute(
            """
            DELETE FROM playlist_tracks
            WHERE playlist_id = ? AND media_file_id = ?
            """,
            (playlist.id, song.id),
        )

    def get_playlist_positions(self, playlist: Playlist, song: Song) -> list[int]:
        self.cur.execute(
            """
            SELECT id
            FROM playlist_tracks
            WHERE playlist_id = ? AND media_file_id = ?
            """,
            (playlist.id, song.id),
        )
        rows = self.cur.fetchall()
        logging.debug(
            f"Found playlist positions for item {song.id} in playlist {playlist.id}: {len(rows)}"
        )
        return [r["id"] for r in rows]

    def commit(self):
        self.connection.commit()

    def replace_song(
        self,
        old_song: Song,
        new_song: Song,
        new_annotation: Annotation,
        user: User,
    ):
        logging.debug(
            f"Replacing song {old_song.id} with {new_song.id} for user {user.id}"
        )

        try:
            with self.connection:
                self.set_annotation(new_song, new_annotation, user)

                self.delete_annotation(old_song, user)

        except Exception as e:
            self.connection.rollback()
            logging.error(f"Failed to replace song: {e}")
            raise

    def repair_playlist(self, old_song: Song, new_song: Song):
        logging.debug(
            f"Repairing playlists by replacing song {old_song.id} with {new_song.id}"
        )
        playlists = self.get_playlists_of_song(old_song)
        for playlist in playlists:
            positions = self.get_playlist_positions(playlist, old_song)
            for pos in positions:
                self.remove_from_playlist(playlist, old_song)
                self.add_to_playlist(playlist, new_song, playlist_position=pos)
