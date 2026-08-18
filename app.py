"""GUI entry point for the BDM outbound dialer.

A deliberately lightweight app (plain Tkinter, no web stack) dressed in a
modern fintech look: flat dark surfaces, pill-shaped controls and a single
brand accent colour. All the custom widgets live in ``ui.py``.
"""

import threading
import tkinter as tk

import ui
from twilio_client import CallError, end_call, is_valid_e164, load_config, place_call

APP_TITLE = "BDM Dialer"


class DialerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("400x580")
        self.minsize(360, 540)
        self.configure(bg=ui.BG)

        self.config_state = load_config()
        self.current_call_sid = None

        self._build_widgets()
        self._show_config_banner()
        self._center_window()

    # -- layout ---------------------------------------------------------------
    def _build_widgets(self):
        outer = tk.Frame(self, bg=ui.BG, padx=28, pady=26)
        outer.pack(fill="both", expand=True)

        # Header: monogram + title on the left, live/dry-run badge on the right.
        header = tk.Frame(outer, bg=ui.BG)
        header.pack(fill="x")

        logo = tk.Canvas(header, width=44, height=44, bg=ui.BG, highlightthickness=0, bd=0)
        logo.create_oval(2, 2, 42, 42, fill=ui.ACCENT, outline="")
        logo.create_text(22, 22, text="↗", fill=ui.TEXT_ON_ACCENT, font=ui.font(self, 18, "bold"))
        logo.pack(side="left")

        titles = tk.Frame(header, bg=ui.BG)
        titles.pack(side="left", padx=14)
        tk.Label(titles, text="Dialer", bg=ui.BG, fg=ui.TEXT, font=ui.font(self, 18, "bold")).pack(anchor="w")
        tk.Label(
            titles, text="Outbound calling", bg=ui.BG, fg=ui.TEXT_MUTED, font=ui.font(self, 10)
        ).pack(anchor="w")

        self.status_pill = ui.Pill(header)
        self.status_pill.pack(side="right", pady=(6, 0))

        # Banner explaining the current mode.
        self.banner_label = tk.Label(
            outer,
            text="",
            bg=ui.BG,
            wraplength=320,
            justify="left",
            anchor="w",
            font=ui.font(self, 10),
        )
        self.banner_label.pack(fill="x", pady=(22, 0))

        # Number entry.
        tk.Label(
            outer,
            text="PHONE NUMBER",
            bg=ui.BG,
            fg=ui.TEXT_MUTED,
            font=ui.font(self, 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(26, 8))

        self.number_entry = ui.RoundedEntry(
            outer,
            placeholder="+1 415 555 2671",
            font_spec=ui.font(self, 19),
            on_return=self._on_call_clicked,
        )
        self.number_entry.pack(fill="x")
        self.number_entry.focus()

        tk.Label(
            outer,
            text="International format, e.g. +14155552671",
            bg=ui.BG,
            fg=ui.TEXT_MUTED,
            font=ui.font(self, 9),
            anchor="w",
        ).pack(fill="x", pady=(8, 0))

        # Call button.
        self.call_button = ui.RoundedButton(
            outer,
            "Call",
            command=self._on_call_clicked,
            font_spec=ui.font(self, 14, "bold"),
        )
        self.call_button.pack(fill="x", pady=(28, 0))

        # Status message.
        self.status_label = tk.Label(
            outer,
            text="",
            bg=ui.BG,
            fg=ui.TEXT_MUTED,
            wraplength=320,
            justify="center",
            font=ui.font(self, 10),
        )
        self.status_label.pack(fill="x", pady=(20, 0))

    def _center_window(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 3
        self.geometry(f"+{x}+{y}")

    def _show_config_banner(self):
        cfg = self.config_state
        if cfg.missing_vars:
            self.status_pill.set("SETUP", ui.WARN)
            self.banner_label.config(
                text=(
                    "Dry-run mode — no real calls are placed. Copy .env.example to .env "
                    "and add your Twilio credentials to go live."
                ),
                fg=ui.WARN,
            )
        elif cfg.dry_run:
            self.status_pill.set("DRY RUN", ui.WARN)
            self.banner_label.config(
                text="Dry-run mode (TWILIO_DRY_RUN is set). No real calls are placed.",
                fg=ui.WARN,
            )
        else:
            self.status_pill.set("LIVE", ui.SUCCESS)
            self.banner_label.config(
                text="Live mode — calls are placed through Twilio.", fg=ui.SUCCESS
            )

    # -- actions --------------------------------------------------------------
    def _on_call_clicked(self):
        number = "".join(self.number_entry.value().split())

        if not number:
            self._set_status("Enter a phone number first.", ui.ERROR)
            return

        if not is_valid_e164(number):
            self._set_status(
                f"'{number}' is not a valid E.164 number. Use +<country code><number>, "
                "e.g. +14155552671.",
                ui.ERROR,
            )
            return

        self._set_calling_state(True)
        self._set_status(f"Calling {number}…", ui.ACCENT)

        thread = threading.Thread(target=self._place_call_worker, args=(number,), daemon=True)
        thread.start()

    def _place_call_worker(self, number: str):
        try:
            result = place_call(number, config=self.config_state)
        except CallError as exc:
            self.after(0, self._on_call_error, str(exc))
        except Exception as exc:  # noqa: BLE001 - last-resort guard so the GUI never crashes
            self.after(0, self._on_call_error, f"Unexpected error: {exc}")
        else:
            self.after(0, self._on_call_success, result)

    def _on_call_success(self, result):
        self._set_active_call_state(result.call_sid)
        self._set_status(result.message, ui.SUCCESS)

    def _on_call_error(self, message: str):
        self._reset_call_state()
        self._set_status(message, ui.ERROR)

    def _on_end_call_clicked(self):
        call_sid = self.current_call_sid
        if not call_sid:
            return

        self.call_button.set_enabled(False)
        self.call_button.set_text("Ending…")
        self._set_status("Ending call…", ui.ACCENT)

        thread = threading.Thread(target=self._end_call_worker, args=(call_sid,), daemon=True)
        thread.start()

    def _end_call_worker(self, call_sid: str):
        try:
            result = end_call(call_sid, config=self.config_state)
        except CallError as exc:
            self.after(0, self._on_end_call_error, str(exc))
        except Exception as exc:  # noqa: BLE001 - last-resort guard so the GUI never crashes
            self.after(0, self._on_end_call_error, f"Unexpected error: {exc}")
        else:
            self.after(0, self._on_end_call_success, result)

    def _on_end_call_success(self, result):
        self._reset_call_state()
        self._set_status(result.message, ui.SUCCESS)

    def _on_end_call_error(self, message: str):
        # Keep the End Call button up so the user can retry the hangup.
        self.call_button.set_enabled(True)
        self.call_button.set_text("End Call")
        self._set_status(message, ui.ERROR)

    def _set_calling_state(self, calling: bool):
        self.call_button.set_enabled(not calling)
        self.call_button.set_text("Calling…" if calling else "Call")

    def _set_active_call_state(self, call_sid):
        self.current_call_sid = call_sid
        self.call_button.set_command(self._on_end_call_clicked)
        self.call_button.set_colors(ui.ERROR, ui.ERROR_HOVER, ui.ERROR_PRESSED)
        self.call_button.set_enabled(True)
        self.call_button.set_text("End Call")

    def _reset_call_state(self):
        self.current_call_sid = None
        self.call_button.set_command(self._on_call_clicked)
        self.call_button.set_colors(ui.ACCENT, ui.ACCENT_HOVER, ui.ACCENT_PRESSED)
        self.call_button.set_enabled(True)
        self.call_button.set_text("Call")

    def _set_status(self, text: str, color: str):
        self.status_label.config(text=text, fg=color)


def main():
    app = DialerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
