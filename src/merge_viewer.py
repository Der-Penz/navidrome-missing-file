"""
MergeViewer widget for Textual apps.

- Mountable: `await self.mount(MergeViewer(missing, target, missing_annot, target_annot))`
- Exposes `result_future` asyncio.Future that resolves to either:
    - dict with keys: `annot` (merged annotation dict) and `delete_old` (bool)
    - or `None` if cancelled

Notes:
- No `if __name__ == '__main__'` or app entrypoint included (per request).
- Requires `textual` (Textual UI library).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from textual.message import Message
from textual.scroll_view import ScrollView
from textual.reactive import reactive
from textual.widget import Widget
from textual.containers import Horizontal, Vertical, Grid
from textual.widgets import Static, Button, Checkbox, Label


class MergeViewer(Widget):
    """A small merge UI to preview and choose how to combine annotations.

    Constructor params:
        missing: dict - metadata for the old/missing file (should contain at least an "id" and a "name"/"path" optionally)
        target: dict - metadata for the new/target file
        missing_annot: dict - annotation data for the missing (old) file
        target_annot: dict - annotation data for the target (new) file

    Usage:
        mv = MergeViewer(missing, target, missing_annot, target_annot)
        await self.mount(mv)
        result = await mv.result_future

    Result: either None (cancel) or dict {"annot": <dict>, "delete_old": <bool>}
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(
        self,
        missing: Dict[str, Any],
        target: Dict[str, Any],
        missing_annot: Optional[Dict[str, Any]],
        target_annot: Optional[Dict[str, Any]],
        name: Optional[str] = None,
    ) -> None:
        super().__init__(name=name)
        self.missing = missing
        self.target = target
        self.missing_annot = missing_annot or {}
        self.target_annot = target_annot or {}

        # A future the caller awaits. We will set a dict or None.
        loop = asyncio.get_event_loop()
        self.result_future: asyncio.Future = loop.create_future()

        # UI state
        # mode: 'overwrite' or 'merge'
        self.mode = reactive("overwrite")
        # which keys from the old annotation to include when merging
        self.selected_keys = reactive(set(self.missing_annot.keys()))
        # whether to delete the old file
        self.delete_old = reactive(False)

        # widgets we will create in on_mount
        self._preview_area: Optional[Static] = None
        self._keys_container: Optional[Vertical] = None

    # ------------------ helper methods ------------------
    def _compute_preview(self) -> Dict[str, Any]:
        """Return the annotation that will be written to the target based on current UI state."""
        if self.mode == "overwrite":
            # write only the old annotation
            return dict(self.missing_annot)

        # merge mode: start with target, then add selected keys from missing (overwriting keys if present)
        merged = dict(self.target_annot)
        for k in self.selected_keys:
            merged[k] = self.missing_annot.get(k)
        return merged

    def _format_stats(self, annot: Dict[str, Any]) -> str:
        """Return a short multi-line stat summary for an annotation dict."""
        if not annot:
            return "<no annotation>"
        lines = [f"keys: {len(annot)}"]
        # show a sample of keys
        sample = list(annot.keys())[:10]
        lines.append("sample keys: " + ", ".join(map(str, sample)))
        return "\n".join(lines)

    # ------------------ textual lifecycle ------------------
    async def on_mount(self) -> None:  # type: ignore[override]
        """Build the UI. Called after mount by Textual."""
        # Left: old file stats
        left = Vertical(
            Static(
                f"Old file\n{self.missing.get('name', self.missing.get('id', 'unknown'))}",
                id="old-title",
            ),
            Static(self._format_stats(self.missing_annot), id="old-stats"),
            id="left-column",
        )

        # Right: new file stats
        right = Vertical(
            Static(
                f"New file\n{self.target.get('name', self.target.get('id', 'unknown'))}",
                id="new-title",
            ),
            Static(self._format_stats(self.target_annot), id="new-stats"),
            id="right-column",
        )

        # Middle: controls + preview
        # keys checkboxes (for merge)
        keys_label = Label("Choose keys from old to add when in Merge mode:")
        keys_container = Vertical(id="keys-container")
        self._keys_container = keys_container
        if not self.missing_annot:
            keys_container.mount(Static("(no keys available in old annotation)"))
        else:
            # create checkboxes for each key
            for k in self.missing_annot.keys():
                cb = Checkbox(label=str(k), value=True)
                # store key name on widget for callback
                cb.key_name = k  # type: ignore[attr-defined]
                cb.checked = True
                keys_container.mount(cb)

        # mode buttons
        overwrite_btn = Button(
            "Overwrite with old (replace target annotation)", id="btn-overwrite"
        )
        merge_btn = Button("Merge selected keys into target", id="btn-merge")

        update_preview_btn = Button("Update preview", id="btn-update-preview")

        delete_checkbox = Checkbox(
            label="Delete old file after merge", value=False, id="cb-delete-old"
        )

        preview_area = Static(
            self._pretty_annot(self._compute_preview()), id="preview-area"
        )
        self._preview_area = preview_area

        controls = Vertical(
            overwrite_btn,
            merge_btn,
            keys_label,
            keys_container,
            update_preview_btn,
            delete_checkbox,
            Label("Preview (what will be written into target):"),
            ScrollView(preview_area, id="preview-scroll", auto_width=True),
            id="middle-column",
        )

        # Confirm / Cancel buttons
        confirm = Button("Confirm merge", id="btn-confirm")
        cancel = Button("Cancel", id="btn-cancel")

        bottom = Horizontal(confirm, cancel, id="bottom-row")

        layout = Grid(left, controls, right, bottom, id="merge-grid")

        await self.mount(layout)

        # store some widget references for event handlers
        self._overwrite_btn = overwrite_btn
        self._merge_btn = merge_btn
        self._update_preview_btn = update_preview_btn
        self._delete_checkbox = delete_checkbox
        self._confirm_btn = confirm
        self._cancel_btn = cancel

        # set initial visual mode
        self._apply_mode_visuals()

    # ------------------ UI helpers ------------------
    def _pretty_annot(self, annot: Dict[str, Any]) -> str:
        # simple pretty printer
        import json

        try:
            return json.dumps(annot, indent=2, ensure_ascii=False)
        except Exception:
            return str(annot)

    def _apply_mode_visuals(self) -> None:
        # update button labels / styles to show active mode
        if getattr(self, "_overwrite_btn", None):
            self._overwrite_btn.disabled = self.mode == "overwrite"
        if getattr(self, "_merge_btn", None):
            self._merge_btn.disabled = self.mode == "merge"

    # ------------------ event handlers ------------------
    async def on_button_pressed(self, event: Button.Pressed) -> None:  # type: ignore[override]
        btn = event.button
        if btn.id == "btn-overwrite":
            self.mode = "overwrite"
            self._apply_mode_visuals()
            # when switching to overwrite, we don't need to change selected keys
            await self._update_preview()

        elif btn.id == "btn-merge":
            self.mode = "merge"
            self._apply_mode_visuals()
            await self._update_preview()

        elif btn.id == "btn-update-preview":
            await self._update_preview()

        elif btn.id == "btn-confirm":
            await self._on_confirm()

        elif btn.id == "btn-cancel":
            await self._on_cancel()

    async def _update_preview(self) -> None:
        # refresh selected_keys from checkboxes in keys_container
        if self._keys_container is not None:
            keys = set()
            for child in self._keys_container.children:
                # Checkbox widget on textual has attribute value/checked depending on version
                val = getattr(child, "value", None)
                if val is None:
                    val = getattr(child, "checked", False)
                if val:
                    # child.key_name was set in on_mount
                    key_name = getattr(child, "key_name", None)
                    if key_name is not None:
                        keys.add(key_name)
            self.selected_keys = keys

        # update delete flag
        delete_val = getattr(self._delete_checkbox, "value", None)
        if delete_val is None:
            delete_val = getattr(self._delete_checkbox, "checked", False)
        self.delete_old = bool(delete_val)

        preview = self._compute_preview()
        if self._preview_area is not None:
            self._preview_area.update(self._pretty_annot(preview))

    async def _on_confirm(self) -> None:
        # compute final result and set future
        result = {"annot": self._compute_preview(), "delete_old": bool(self.delete_old)}
        if not self.result_future.done():
            self.result_future.set_result(result)
        # optionally unmount self
        await self.remove()

    async def _on_cancel(self) -> None:
        if not self.result_future.done():
            self.result_future.set_result(None)
        await self.remove()

    async def action_cancel(self) -> None:  # bound to Escape
        await self._on_cancel()

    # If the widget is removed/destroyed without an explicit set, make sure future resolves.
    async def on_unmount(self) -> None:  # type: ignore[override]
        if not self.result_future.done():
            self.result_future.set_result(None)
