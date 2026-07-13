"""Reusable, theme-aware Tkinter widgets for a modern fintech-style UI.

Tkinter's stock ``Button``/``Entry`` widgets look like Windows 98. The
Canvas-backed widgets here give us pill shapes, hover states and a flat dark
palette without pulling in any heavyweight GUI toolkit — the app stays a
single ``python app.py`` away from running.
"""

import tkinter as tk
from tkinter import font as tkfont

# --- Palette -----------------------------------------------------------------
# A dark, high-contrast fintech theme. ACCENT is the brand blue the whole UI
# is built around.
ACCENT = "#109dff"
ACCENT_HOVER = "#38aeff"
ACCENT_PRESSED = "#0d84d9"

BG = "#0d0f14"          # window background
SURFACE = "#161a23"     # cards / raised panels
SURFACE_HI = "#20242f"  # secondary buttons, hovered surfaces
FIELD_BG = "#1b1f2a"    # input fields

TEXT = "#f4f6fb"        # primary text
TEXT_MUTED = "#8b93a7"  # secondary text / placeholders
TEXT_ON_ACCENT = "#ffffff"

SUCCESS = "#2ecc8f"
ERROR = "#ff5c72"
WARN = "#ffb547"

# Preferred font families, best first. The first one actually installed wins,
# so this looks native on Windows/macOS and still fine on plain Linux.
_FONT_STACK = (
    "Segoe UI",
    "SF Pro Display",
    "SF Pro Text",
    "Helvetica Neue",
    "Inter",
    "Roboto",
    "DejaVu Sans",
    "Helvetica",
    "Arial",
)


def resolve_family(root: tk.Misc) -> str:
    """Return the first font family from ``_FONT_STACK`` that is installed."""
    available = {f.lower() for f in tkfont.families(root)}
    for family in _FONT_STACK:
        if family.lower() in available:
            return family
    return "TkDefaultFont"


def font(root: tk.Misc, size: int, weight: str = "normal") -> tkfont.Font:
    return tkfont.Font(family=resolve_family(root), size=size, weight=weight)


def _round_rect_points(x1, y1, x2, y2, r):
    """Corner points for a rounded rectangle, for ``create_polygon(smooth=True)``."""
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]


class RoundedButton(tk.Canvas):
    """A flat, pill-shaped button with hover / pressed / disabled states."""

    def __init__(
        self,
        parent,
        text,
        command=None,
        *,
        height=52,
        radius=26,
        bg=ACCENT,
        fg=TEXT_ON_ACCENT,
        hover_bg=ACCENT_HOVER,
        pressed_bg=ACCENT_PRESSED,
        disabled_bg=SURFACE_HI,
        disabled_fg=TEXT_MUTED,
        font_spec=("Helvetica", 13, "bold"),
        surface=BG,
    ):
        super().__init__(
            parent,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=surface,
            takefocus=1,
        )
        self._text = text
        self._command = command
        self._radius = radius
        self._bg = bg
        self._fg = fg
        self._hover_bg = hover_bg
        self._pressed_bg = pressed_bg
        self._disabled_bg = disabled_bg
        self._disabled_fg = disabled_fg
        self._font = font_spec
        self._enabled = True
        self._hovering = False

        self._shape = self.create_polygon(0, 0, 0, 0, 0, 0, fill=bg, smooth=True)
        self._label = self.create_text(0, 0, text=text, fill=fg, font=font_spec)

        self.bind("<Configure>", lambda _e: self._redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _current_bg(self):
        if not self._enabled:
            return self._disabled_bg
        if self._pressed:
            return self._pressed_bg
        if self._hovering:
            return self._hover_bg
        return self._bg

    _pressed = False

    def _redraw(self):
        w = self.winfo_width()
        h = self.winfo_height()
        r = min(self._radius, h // 2)
        self.coords(self._shape, *_round_rect_points(1, 1, w - 1, h - 1, r))
        self.itemconfigure(self._shape, fill=self._current_bg())
        self.coords(self._label, w // 2, h // 2)
        self.itemconfigure(
            self._label,
            text=self._text,
            fill=self._fg if self._enabled else self._disabled_fg,
        )

    def _on_enter(self, _e):
        if self._enabled:
            self._hovering = True
            self.configure(cursor="hand2")
            self._redraw()

    def _on_leave(self, _e):
        self._hovering = False
        self._pressed = False
        self.configure(cursor="")
        self._redraw()

    def _on_press(self, _e):
        if self._enabled:
            self._pressed = True
            self._redraw()

    def _on_release(self, _e):
        was_pressed = self._pressed
        self._pressed = False
        self._redraw()
        if self._enabled and was_pressed and self._hovering and self._command:
            self._command()

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if not enabled:
            self._hovering = False
            self._pressed = False
        self._redraw()

    def set_text(self, text: str):
        self._text = text
        self._redraw()


class RoundedEntry(tk.Canvas):
    """A rounded text field with placeholder text and an accent focus ring."""

    def __init__(
        self,
        parent,
        *,
        placeholder="",
        height=60,
        radius=16,
        font_spec=("Helvetica", 18),
        surface=BG,
        on_return=None,
    ):
        super().__init__(parent, height=height, highlightthickness=0, bd=0, bg=surface)
        self._radius = radius
        self._placeholder = placeholder
        self._showing_placeholder = False

        self._shape = self.create_polygon(0, 0, 0, 0, 0, 0, fill=FIELD_BG, smooth=True)

        self.entry = tk.Entry(
            self,
            bd=0,
            relief="flat",
            highlightthickness=0,
            bg=FIELD_BG,
            fg=TEXT,
            disabledbackground=FIELD_BG,
            insertbackground=ACCENT,
            justify="center",
            font=font_spec,
        )
        self._window = self.create_window(0, 0, window=self.entry, anchor="center")

        if placeholder:
            self._set_placeholder()

        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        # Clear the placeholder only once the user actually types, so the
        # format hint stays visible even while the field is focused.
        self.entry.bind("<KeyPress>", self._on_key)
        if on_return:
            self.entry.bind("<Return>", lambda _e: on_return())
        self.bind("<Configure>", lambda _e: self._redraw())
        # Clicking anywhere on the padded canvas should focus the entry.
        self.bind("<Button-1>", lambda _e: self.entry.focus_set())

    def _redraw(self):
        w = self.winfo_width()
        h = self.winfo_height()
        r = min(self._radius, h // 2)
        self.coords(self._shape, *_round_rect_points(1, 1, w - 1, h - 1, r))
        self._draw_border(focused=self.focus_get() is self.entry)
        self.coords(self._window, w // 2, h // 2)
        self.itemconfigure(self._window, width=w - 36)

    def _draw_border(self, focused: bool):
        self.itemconfigure(
            self._shape,
            outline=ACCENT if focused else FIELD_BG,
            width=2 if focused else 1,
        )

    def _set_placeholder(self):
        self._showing_placeholder = True
        self.entry.delete(0, "end")
        self.entry.insert(0, self._placeholder)
        self.entry.configure(fg=TEXT_MUTED)

    def _clear_placeholder(self):
        if self._showing_placeholder:
            self._showing_placeholder = False
            self.entry.delete(0, "end")
            self.entry.configure(fg=TEXT)

    def _on_focus_in(self, _e):
        self._draw_border(focused=True)

    def _on_focus_out(self, _e):
        if self._placeholder and (self._showing_placeholder or not self.entry.get().strip()):
            self._set_placeholder()
        self._draw_border(focused=False)

    def _on_key(self, event):
        # Only a printable key should dismiss the placeholder; arrows, tab,
        # shift, etc. carry an empty ``char`` and are left alone.
        if self._showing_placeholder and event.char and event.char.isprintable():
            self._clear_placeholder()

    def value(self) -> str:
        if self._showing_placeholder:
            return ""
        return self.entry.get().strip()

    def focus(self):
        self.entry.focus_set()


class Pill(tk.Canvas):
    """A small static rounded status badge, e.g. LIVE / DRY RUN."""

    def __init__(self, parent, *, font_spec=("Helvetica", 9, "bold"), surface=BG):
        super().__init__(parent, height=24, highlightthickness=0, bd=0, bg=surface)
        self._font = font_spec
        self._shape = self.create_polygon(0, 0, 0, 0, 0, 0, fill=SURFACE_HI, smooth=True)
        self._dot = self.create_oval(0, 0, 0, 0, fill=TEXT_MUTED, outline="")
        self._label = self.create_text(0, 0, text="", fill=TEXT, font=font_spec, anchor="w")

    def set(self, text, color):
        tmp = tkfont.Font(font=self._font)
        text_w = tmp.measure(text)
        pad_x = 12
        dot_r = 4
        gap = 7
        total = pad_x + dot_r * 2 + gap + text_w + pad_x
        h = 24
        self.configure(width=total)
        self.coords(self._shape, *_round_rect_points(1, 1, total - 1, h - 1, h // 2))
        cy = h // 2
        dx = pad_x
        self.coords(self._dot, dx, cy - dot_r, dx + dot_r * 2, cy + dot_r)
        self.itemconfigure(self._dot, fill=color)
        self.coords(self._label, dx + dot_r * 2 + gap, cy)
        self.itemconfigure(self._label, text=text, fill=color)


class ConfirmDialog(tk.Toplevel):
    """A themed modal confirmation dialog (replaces the native messagebox)."""

    def __init__(self, parent, title, message, confirm_text="Call", cancel_text="Cancel"):
        super().__init__(parent, bg=SURFACE)
        self.result = False
        self.overrideredirect(True)  # frameless, keeps the flat aesthetic
        self.transient(parent)
        self.configure(highlightthickness=1, highlightbackground=SURFACE_HI)

        wrap = tk.Frame(self, bg=SURFACE, padx=28, pady=26)
        wrap.pack(fill="both", expand=True)

        tk.Label(
            wrap, text=title, bg=SURFACE, fg=TEXT, font=font(self, 15, "bold"), anchor="w"
        ).pack(fill="x")
        tk.Label(
            wrap,
            text=message,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=font(self, 11),
            anchor="w",
            justify="left",
            wraplength=280,
        ).pack(fill="x", pady=(10, 22))

        row = tk.Frame(wrap, bg=SURFACE)
        row.pack(fill="x")
        row.columnconfigure(0, weight=1, uniform="btn")
        row.columnconfigure(1, weight=1, uniform="btn")

        cancel = RoundedButton(
            row,
            cancel_text,
            command=self._cancel,
            height=46,
            radius=23,
            bg=SURFACE_HI,
            fg=TEXT,
            hover_bg="#2a2f3d",
            pressed_bg="#2a2f3d",
            font_spec=font(self, 12, "bold"),
            surface=SURFACE,
        )
        # Small intrinsic width; grid weights expand them to fill the dialog.
        cancel.configure(width=120)
        cancel.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        confirm = RoundedButton(
            row,
            confirm_text,
            command=self._confirm,
            height=46,
            radius=23,
            font_spec=font(self, 12, "bold"),
            surface=SURFACE,
        )
        confirm.configure(width=120)
        confirm.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.bind("<Escape>", lambda _e: self._cancel())
        self.bind("<Return>", lambda _e: self._confirm())

        self.update_idletasks()
        self._center_on(parent)
        self.grab_set()
        self.focus_set()

    def _center_on(self, parent):
        pw, ph = parent.winfo_width(), parent.winfo_height()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        # Frameless (overrideredirect) windows don't honour the requested size
        # on their own, so pin width/height explicitly as well as position.
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _confirm(self):
        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()


def ask_confirm(parent, title, message, confirm_text="Call") -> bool:
    dialog = ConfirmDialog(parent, title, message, confirm_text=confirm_text)
    parent.wait_window(dialog)
    return dialog.result
