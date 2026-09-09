from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
from typing import Final

from worldzero.pilot_playable import (
    GALLERY_SITE,
    GATE_SITE,
    PILOT_I1_PREHISTORY_MINUTES,
    UPPER_REACH_SITE,
    create_pilot_i1_loop,
)


class PilotI1Gui:
    """Minimal visual layer over existing playable I1 loop."""

    _SITE_LABELS: Final[dict[str, str]] = {
        UPPER_REACH_SITE: "The Underpeak Reach",
        GATE_SITE: "The Sealed River Gate",
        GALLERY_SITE: "The Old Gallery",
    }

    _SITE_ORDER: Final[tuple[str, ...]] = (
        UPPER_REACH_SITE,
        GATE_SITE,
        GALLERY_SITE,
    )

    _NODE_X: Final[int] = 220
    _NODE_Y: Final[dict[str, int]] = {
        UPPER_REACH_SITE: 80,
        GATE_SITE: 200,
        GALLERY_SITE: 320,
    }

    def __init__(self, *, seed: int, prehistory_minutes: int, serial_actions: bool) -> None:
        self.loop = create_pilot_i1_loop(
            seed=seed,
            prehistory_minutes=prehistory_minutes,
            serial_actions=serial_actions,
        )
        self.root = tk.Tk()
        self.root.title("World Zero - Pilot I1")
        self.root.geometry("980x740")
        self.root.minsize(900, 680)

        self._effort: float = 1.0
        self._create_ui()
        self._refresh(force_log=True)
        self._wire_controls()

    def run(self) -> None:
        self.root.mainloop()

    def _create_ui(self) -> None:
        self.root.configure(bg="#0f1116")

        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=8)

        self.time_var = tk.StringVar(value="")
        self.location_var = tk.StringVar(value="")

        ttk.Label(top, text="World Zero I1", font=("Segoe UI", 15, "bold")).pack(
            side="left", padx=(0, 16)
        )
        ttk.Label(top, textvariable=self.time_var, font=("Segoe UI", 11)).pack(
            side="left", padx=(0, 12)
        )
        ttk.Label(top, textvariable=self.location_var, font=("Segoe UI", 11)).pack(side="left")

        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)

        left_panel = ttk.LabelFrame(main, text="Map")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        self.canvas = tk.Canvas(left_panel, width=320, height=420, bg="#1a1f2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)

        right_panel = ttk.LabelFrame(main, text="World & HUD")
        right_panel.grid(row=0, column=1, sticky="nsew")
        right_panel.rowconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=0)
        right_panel.rowconfigure(2, weight=0)
        right_panel.columnconfigure(0, weight=1)

        self.info_text = scrolledtext.ScrolledText(
            right_panel,
            width=72,
            height=24,
            wrap="word",
            font=("Consolas", 10),
            state="disabled",
        )
        self.info_text.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        hud = ttk.Frame(right_panel)
        hud.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        hud.columnconfigure(0, weight=1)
        hud.columnconfigure(1, weight=1)
        hud.columnconfigure(2, weight=1)
        self.hud_projects_var = tk.StringVar(value="")
        self.hud_probe_var = tk.StringVar(value="")
        self.hud_gate_var = tk.StringVar(value="")
        self.hud_minute_var = tk.StringVar(value="")
        ttk.Label(hud, textvariable=self.hud_minute_var, font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        ttk.Label(hud, textvariable=self.hud_projects_var, font=("Segoe UI", 10)).grid(row=0, column=1, sticky="w")
        ttk.Label(hud, textvariable=self.hud_gate_var, font=("Segoe UI", 10)).grid(row=0, column=2, sticky="w")
        ttk.Label(hud, textvariable=self.hud_probe_var, font=("Segoe UI", 10)).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))

        actions_snapshot = ttk.Frame(right_panel)
        actions_snapshot.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        actions_snapshot.columnconfigure(0, weight=1)
        ttk.Label(actions_snapshot, text="Available actions:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.actions_list = scrolledtext.ScrolledText(
            actions_snapshot,
            width=72,
            height=6,
            wrap="word",
            font=("Consolas", 10),
            state="disabled",
        )
        self.actions_list.pack(fill="both", expand=True, pady=(4, 0))

        controls = ttk.Frame(self.root)
        controls.pack(fill="x", padx=10, pady=(0, 10))
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(2, weight=1)
        controls.columnconfigure(3, weight=1)
        controls.columnconfigure(4, weight=1)

        move_box = ttk.LabelFrame(controls, text="Movement")
        move_box.grid(row=0, column=0, sticky="nsew", padx=(0, 4), ipadx=3, ipady=3)
        self.move_up_button = ttk.Button(
            move_box, text="↑ W / Up", command=lambda: self._move("up")
        )
        self.move_up_button.pack(fill="x", padx=6, pady=(6, 2))
        self.move_down_button = ttk.Button(
            move_box, text="↓ S / Down", command=lambda: self._move("down")
        )
        self.move_down_button.pack(fill="x", padx=6, pady=(0, 6))

        action_box = ttk.LabelFrame(controls, text="Actions")
        action_box.grid(row=0, column=1, sticky="nsew", padx=4)
        self.inspect_button = ttk.Button(action_box, text="Inspect", command=self._inspect)
        self.inspect_button.pack(fill="x", padx=6, pady=(6, 2))
        self.pray_button = ttk.Button(action_box, text="Pray", command=self._pray)
        self.pray_button.pack(fill="x", padx=6, pady=2)
        self.wait_button = ttk.Button(action_box, text="Wait 60m", command=lambda: self._wait(60))
        self.wait_button.pack(fill="x", padx=6, pady=2)
        self.settle_button = ttk.Button(
            action_box, text="Settle 60m", command=lambda: self._settle(60)
        )
        self.settle_button.pack(fill="x", padx=6, pady=(2, 6))

        probe_box = ttk.LabelFrame(controls, text="Divine")
        probe_box.grid(row=0, column=2, sticky="nsew", padx=4)
        self.probe_button = ttk.Button(probe_box, text="Reveal probe", command=self._probe)
        self.probe_button.pack(fill="x", padx=6, pady=(6, 2))
        self.answer_entry = ttk.Entry(probe_box)
        self.answer_entry.pack(fill="x", padx=6, pady=(2, 2))
        self.answer_button = ttk.Button(probe_box, text="Answer", command=self._answer)
        self.answer_button.pack(fill="x", padx=6, pady=(0, 6))

        self.gate_box = ttk.LabelFrame(controls, text="Gate work")
        self.gate_box.grid(row=0, column=3, sticky="nsew", padx=4)
        ttk.Label(self.gate_box, text="Effort").pack(anchor="w", padx=6, pady=(6, 0))
        self.effort_scale = ttk.Scale(
            self.gate_box,
            from_=0.1,
            to=1.0,
            orient="horizontal",
            command=self._on_effort_change,
        )
        self.effort_scale.set(1.0)
        self.effort_scale.pack(fill="x", padx=6)
        self.effort_label = ttk.Label(self.gate_box, text="1.0")
        self.effort_label.pack(anchor="w", padx=6)
        self.gate_work_button = ttk.Button(self.gate_box, text="Work gate", command=self._work_gate)
        self.gate_work_button.pack(fill="x", padx=6, pady=(2, 6))

        controls_right = ttk.Frame(controls)
        controls_right.grid(row=0, column=4, sticky="nsew", padx=(4, 0))
        ttk.Button(controls_right, text="Journal", command=self._journal).pack(fill="x", padx=6, pady=(6, 2))
        ttk.Button(controls_right, text="Map text", command=self._show_map_text).pack(fill="x", padx=6, pady=2)
        ttk.Button(controls_right, text="Exit", command=self.root.destroy).pack(fill="x", padx=6, pady=(2, 6))

        status_box = ttk.LabelFrame(self.root, text="Controls")
        status_box.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(
            status_box,
            text=(
                "Move: W/S or ↑/↓, and pray -> probe -> answer -> settle flow. "
                "The settle button is disabled while a probe is unanswered. "
                "Press Enter in the answer field to send your response."
            ),
            wraplength=920,
        ).pack(fill="x", padx=8, pady=6)

    def _wire_controls(self) -> None:
        self.root.bind("<Up>", lambda _event: self._move("up"))
        self.root.bind("<Down>", lambda _event: self._move("down"))
        self.root.bind("<w>", lambda _event: self._move("up"))
        self.root.bind("<W>", lambda _event: self._move("up"))
        self.root.bind("<s>", lambda _event: self._move("down"))
        self.root.bind("<S>", lambda _event: self._move("down"))
        self.root.bind("<a>", lambda _event: self._move("up"))
        self.root.bind("<A>", lambda _event: self._move("up"))
        self.root.bind("<d>", lambda _event: self._move("down"))
        self.root.bind("<D>", lambda _event: self._move("down"))
        self.root.bind("<Return>", lambda _event: self._answer())

    def _on_effort_change(self, value: str) -> None:
        self._effort = max(0.1, min(1.0, float(value)))
        self.effort_label.config(text=f"{self._effort:.2f}")

    def _set_widget_state(self, widget: tk.Widget, enabled: bool) -> None:
        if isinstance(widget, (ttk.Button, ttk.Checkbutton, ttk.Radiobutton, ttk.Scale)):
            widget.state(["!disabled"] if enabled else ["disabled"])
            return
        if isinstance(widget, (ttk.Entry, tk.Entry)):
            widget.configure(state="normal" if enabled else "disabled")
            return
        if isinstance(widget, tk.Widget):
            try:
                widget.state(["!disabled"] if enabled else ["disabled"])
            except Exception:
                pass

    def _append_log(self, text: str) -> None:
        self.info_text.config(state="normal")
        self.info_text.insert("end", text + "\n\n")
        self.info_text.see("end")
        self.info_text.config(state="disabled")

    def _set_scene_text(self, text: str) -> None:
        self.info_text.config(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", text)
        self.info_text.see("1.0")
        self.info_text.config(state="disabled")

    def _neighbors(self, site_id: str) -> list[str]:
        try:
            index = self._SITE_ORDER.index(site_id)
        except ValueError:
            return []
        neighbors = []
        if index - 1 >= 0:
            neighbors.append(self._SITE_ORDER[index - 1])
        if index + 1 < len(self._SITE_ORDER):
            neighbors.append(self._SITE_ORDER[index + 1])
        return neighbors

    def _move(self, direction: str) -> None:
        view = self.loop.player_view()
        if not self._neighbors(view.location_id):
            self._append_log("No place to go from here.")
            return

        if direction == "up":
            if view.location_id == UPPER_REACH_SITE:
                self._append_log("You cannot move higher from here.")
                return
            if view.location_id == GATE_SITE:
                destination = UPPER_REACH_SITE
            else:
                destination = GATE_SITE
        elif direction == "down":
            if view.location_id == GALLERY_SITE:
                self._append_log("You cannot move lower from here.")
                return
            if view.location_id == UPPER_REACH_SITE:
                destination = GATE_SITE
            else:
                destination = GALLERY_SITE
        else:
            self._append_log("Unknown movement direction.")
            return

        result = self.loop.move(destination)
        self._append_log(result.message)
        self._refresh()

    def _inspect(self) -> None:
        result = self.loop.inspect()
        self._append_log(result.message)
        self._refresh()

    def _pray(self) -> None:
        result = self.loop.pray_to_death()
        self._append_log(result.message)
        self._refresh()

    def _wait(self, minutes: int) -> None:
        result = self.loop.wait(minutes)
        self._append_log(result.message)
        self._refresh()

    def _settle(self, minutes: int) -> None:
        result = self.loop.settle(minutes)
        self._append_log(result.message)
        self._refresh()

    def _probe(self) -> None:
        result = self.loop.probe()
        self._append_log(result.message)
        self._refresh()

    def _answer(self) -> None:
        text = self.answer_entry.get().strip()
        if not text:
            return
        self.answer_entry.delete(0, "end")
        result = self.loop.answer(text)
        self._append_log(result.message)
        self._refresh()

    def _work_gate(self) -> None:
        result = self.loop.work_gate_silt(f"{self._effort}")
        self._append_log(result.message)
        self._refresh()

    def _journal(self) -> None:
        result = self.loop.execute("journal")
        self._append_log(result.message)
        self._refresh()

    def _show_map_text(self) -> None:
        view = self.loop.player_view()
        self._append_log("\n".join(self._format_map_lines(view)))

    def _format_map_lines(self, view) -> list[str]:
        return [
            "Map:",
            f"{self._format_site(UPPER_REACH_SITE, view.location_id)}",
            " | 15m",
            " v",
            f"{self._format_site(GATE_SITE, view.location_id)}",
            " | 15m",
            " v",
            f"{self._format_site(GALLERY_SITE, view.location_id)}",
        ]

    def _format_site(self, site_id: str, current_id: str) -> str:
        current = " *" if site_id == current_id else ""
        return f"[{self._SITE_LABELS.get(site_id, site_id)}{current}]"

    def _set_button_matrix(self, view) -> None:
        self._set_widget_state(self.move_up_button, view.location_id != UPPER_REACH_SITE)
        self._set_widget_state(self.move_down_button, view.location_id != GALLERY_SITE)
        self._set_widget_state(self.inspect_button, True)
        self._set_widget_state(self.pray_button, True)

        self._set_widget_state(self.wait_button, True)

        can_settle = not view.probe_pending
        self._set_widget_state(self.settle_button, can_settle)
        self._set_widget_state(self.probe_button, view.probe_pending)

        self._set_widget_state(self.answer_entry, view.probe_pending)
        self._set_widget_state(self.answer_button, view.probe_pending)
        if not view.probe_pending:
            self.answer_entry.delete(0, "end")

        can_work_gate = view.location_id == GATE_SITE
        self._set_widget_state(self.gate_work_button, can_work_gate)

    def _render_available_actions(self, view) -> None:
        lines = [" - " + action for action in view.available_actions] if view.available_actions else ["  (none)"]
        self.actions_list.config(state="normal")
        self.actions_list.delete("1.0", "end")
        self.actions_list.insert("1.0", "\n".join(lines))
        self.actions_list.config(state="disabled")

    def _refresh(self, force_log: bool = False) -> None:
        view = self.loop.player_view()
        self.time_var.set(f"Time: {view.time}")
        self.location_var.set(f"Location: {view.location}")
        self.hud_minute_var.set(f"Minute: {view.game_minute}")
        self.hud_projects_var.set("Projects: " + ", ".join(view.project_statuses))
        self.hud_gate_var.set(
            self._format_gate_status(view.gate_debris_load, view.gate_sluice_position)
        )
        probe_state = "pending" if view.probe_pending else "none"
        self.hud_probe_var.set(f"Unanswered probe: {probe_state}")

        scene_lines = [
            "SCENE:",
            view.description,
            "",
            f"Visible: {', '.join(view.visible_objects)}" if view.visible_objects else "Visible: nothing notable",
            f"People: {', '.join(view.visible_subjects)}" if view.visible_subjects else "People: none",
            f"Observation: {', '.join(view.observations)}" if view.observations else "Observation: no new notes",
        ]
        if view.received_words:
            scene_lines.append("Words received:")
            scene_lines.extend(f"  - {item}" for item in view.received_words)
        if view.spoken_words:
            scene_lines.append("Your words:")
            scene_lines.extend(f"  - {item}" for item in view.spoken_words)

        if not force_log:
            self._set_scene_text("\n".join(scene_lines))
        else:
            self._set_scene_text("\n".join(scene_lines + ["", "Press controls or keys to start action."]))

        self._redraw_map(view)
        self._render_available_actions(view)
        self._set_button_matrix(view)

    def _redraw_map(self, view) -> None:
        self.canvas.delete("all")

        for top, bottom in ((UPPER_REACH_SITE, GATE_SITE), (GATE_SITE, GALLERY_SITE)):
            x = self._NODE_X
            self.canvas.create_line(
                x,
                self._NODE_Y[top] + 42,
                x,
                self._NODE_Y[bottom] - 42,
                fill="#6f7d8f",
                width=4,
            )
            self.canvas.create_text(
                x,
                (self._NODE_Y[top] + self._NODE_Y[bottom]) // 2,
                text="15m",
                fill="#9fb2ca",
                font=("Consolas", 9),
            )

        for site_id, (x, y) in {
            UPPER_REACH_SITE: (self._NODE_X, self._NODE_Y[UPPER_REACH_SITE]),
            GATE_SITE: (self._NODE_X, self._NODE_Y[GATE_SITE]),
            GALLERY_SITE: (self._NODE_X, self._NODE_Y[GALLERY_SITE]),
        }.items():
            if site_id == view.location_id:
                fill = "#2ecc71"
                text = f"{self._SITE_LABELS[site_id]} ✦"
            else:
                fill = "#8ca0b8"
                text = self._SITE_LABELS[site_id]
            self.canvas.create_oval(
                x - 44,
                y - 28,
                x + 44,
                y + 28,
                outline=fill,
                width=3,
                fill="#2a3647",
            )
            self.canvas.create_text(
                x,
                y,
                text=text,
                fill=fill,
                font=("Segoe UI", 10, "bold"),
                width=100,
            )

    def _format_gate_status(self, debris_load: float | None, sluice_position: float | None) -> str:
        if debris_load is None and sluice_position is None:
            return "Gate: not here"
        parts = [f"Debris: {debris_load * 100:.0f}%" if debris_load is not None else None]
        if sluice_position is not None:
            parts.append(f"Sluice: {sluice_position * 100:.0f}% open")
        return "Gate: " + ", ".join(part for part in parts if part is not None)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Play Pilot I1 in a visual Tkinter window"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--prehistory-minutes",
        type=int,
        default=PILOT_I1_PREHISTORY_MINUTES,
    )
    parser.add_argument("--serial-actions", action="store_true")
    args = parser.parse_args()

    app = PilotI1Gui(
        seed=args.seed,
        prehistory_minutes=args.prehistory_minutes,
        serial_actions=args.serial_actions,
    )
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
