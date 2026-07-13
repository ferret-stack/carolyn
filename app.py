"""GUI entry point for the BDM outbound dialer."""

import threading
import tkinter as tk
from tkinter import messagebox

from twilio_client import CallError, is_valid_e164, load_config, place_call

APP_TITLE = "BDM Outbound Dialer"

COLOR_ERROR = "#c62828"
COLOR_OK = "#2e7d32"
COLOR_WARN = "#a15c00"


class DialerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("440x280")
        self.resizable(False, False)

        self.config_state = load_config()

        self._build_widgets()
        self._show_config_banner()

    def _build_widgets(self):
        pad = {"padx": 16, "pady": 8}

        self.banner_label = tk.Label(self, text="", wraplength=400, justify="left", font=("Helvetica", 10))
        self.banner_label.pack(fill="x", **pad)

        tk.Label(self, text="Phone number (E.164, e.g. +14155552671)", anchor="w").pack(fill="x", padx=16)

        self.number_var = tk.StringVar()
        self.number_entry = tk.Entry(self, textvariable=self.number_var, font=("Helvetica", 14))
        self.number_entry.pack(fill="x", padx=16, pady=(0, 8))
        self.number_entry.bind("<Return>", lambda _event: self._on_call_clicked())
        self.number_entry.focus()

        self.call_button = tk.Button(
            self, text="Call", command=self._on_call_clicked, font=("Helvetica", 12, "bold"), width=12
        )
        self.call_button.pack(pady=8)

        self.status_label = tk.Label(self, text="", wraplength=400, justify="left")
        self.status_label.pack(fill="x", **pad)

    def _show_config_banner(self):
        cfg = self.config_state
        if cfg.missing_vars:
            self.banner_label.config(
                text=(
                    "DRY-RUN mode: missing .env values ("
                    + ", ".join(cfg.missing_vars)
                    + "). No real calls will be placed. Copy .env.example to .env and "
                    "fill in your Twilio credentials to go live."
                ),
                fg=COLOR_WARN,
            )
        elif cfg.dry_run:
            self.banner_label.config(
                text="DRY-RUN mode (TWILIO_DRY_RUN is set). No real calls will be placed.",
                fg=COLOR_WARN,
            )
        else:
            self.banner_label.config(text="Live mode: calls will be placed via Twilio.", fg=COLOR_OK)

    def _on_call_clicked(self):
        number = self.number_var.get().strip()

        if not number:
            self._set_status("Enter a phone number first.", error=True)
            return

        if not is_valid_e164(number):
            self._set_status(
                f"'{number}' is not a valid E.164 number. Use the format "
                "+<country code><number>, e.g. +14155552671.",
                error=True,
            )
            return

        if not messagebox.askyesno("Confirm Call", f"Call {number}?"):
            self._set_status("Call cancelled.", error=False)
            return

        self._set_calling_state(True)
        self._set_status(f"Calling {number}...", error=False)

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
        self._set_calling_state(False)
        self._set_status(result.message, error=False)

    def _on_call_error(self, message: str):
        self._set_calling_state(False)
        self._set_status(message, error=True)

    def _set_calling_state(self, calling: bool):
        self.call_button.config(state="disabled" if calling else "normal")

    def _set_status(self, text: str, error: bool):
        self.status_label.config(text=text, fg=COLOR_ERROR if error else COLOR_OK)


def main():
    app = DialerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
