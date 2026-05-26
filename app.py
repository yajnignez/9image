import os
import sys
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, StringVar, Canvas, Frame, Label, font as tkfont
from tkinter import ttk
import tkinter as tk

from PIL import Image

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    TkinterDnD = None
    DND_FILES = None
    DND_AVAILABLE = False


# (cols, rows, label, tag)
GRIDS = [
    (3, 3, "9格", "3×3"),
    (4, 4, "16格", "4×4"),
    (2, 2, "4格", "2×2"),
    (5, 5, "25格", "5×5"),
    (1, 3, "3格竖", "1×3"),
    (1, 4, "4格竖", "1×4"),
    (4, 5, "20格", "4×5"),
]

SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

# iOS-inspired palette
BG       = "#F2F2F7"   # system grouped background
CARD     = "#FFFFFF"
LABEL1   = "#1C1C1E"   # primary text
LABEL2   = "#8E8E93"   # secondary text
ACCENT   = "#007AFF"   # iOS blue
ACCENT_H = "#0051A8"
SEP      = "#E5E5EA"
SUCCESS  = "#34C759"
DANGER   = "#FF3B30"
RADIUS   = 12


def split_image(image_path: Path, cols: int, rows: int) -> Path:
    img = Image.open(image_path)
    w, h = img.size
    tile_w = w // cols
    tile_h = h // rows

    tag = f"{cols}x{rows}"
    out_dir = image_path.parent / f"{image_path.stem}_{tag}"
    out_dir.mkdir(exist_ok=True)

    src_ext = image_path.suffix.lower()
    out_ext = ".png" if src_ext == ".webp" or src_ext not in SUPPORTED else src_ext

    if out_ext == ".png" and img.mode not in ("RGB", "RGBA", "L", "LA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")

    idx = 1
    for r in range(rows):
        for c in range(cols):
            left   = c * tile_w
            top    = r * tile_h
            right  = w if c == cols - 1 else left + tile_w
            bottom = h if r == rows - 1 else top + tile_h
            tile = img.crop((left, top, right, bottom))
            if out_ext in (".jpg", ".jpeg") and tile.mode in ("RGBA", "LA", "P"):
                tile = tile.convert("RGB")
            tile.save(out_dir / f"{idx:02d}{out_ext}")
            idx += 1
    return out_dir


class RoundedButton(tk.Canvas):
    """Flat rounded button drawn on a Canvas — no ttk theming needed."""

    def __init__(self, parent, text, subtext="", command=None,
                 bg=CARD, fg=LABEL1, accent=ACCENT,
                 width=100, height=56, radius=10):
        super().__init__(parent, width=width, height=height,
                         bg=parent["bg"] if hasattr(parent, "__getitem__") else BG,
                         highlightthickness=0, bd=0)
        self._bg = bg
        self._fg = fg
        self._accent = accent
        self._text = text
        self._subtext = subtext
        self._cmd = command
        self._r = radius
        self._bw = width
        self._bh = height
        self._pressed = False

        self._draw()
        self.bind("<ButtonPress-1>",   self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>",           self._on_enter)
        self.bind("<Leave>",           self._on_leave)

    def _draw(self, pressed=False):
        self.delete("all")
        r, w, h = self._r, self._bw, self._bh
        fill = "#E8E8ED" if pressed else self._bg
        # rounded rect via polygon
        self.create_polygon(
            r, 0,  w-r, 0,
            w, 0,  w, r,
            w, h-r, w, h,
            w-r, h, r, h,
            0, h,  0, h-r,
            0, r,  0, 0,
            r, 0,
            smooth=True, fill=fill, outline=SEP, width=1
        )
        # accent top bar
        self.create_rectangle(r, 0, w-r, 3, fill=self._accent, outline="")
        self.create_rectangle(0, 0, r, 3, fill="", outline="")
        self.create_rectangle(w-r, 0, w, 3, fill="", outline="")

        cy = h // 2 - (6 if self._subtext else 0)
        self.create_text(w//2, cy, text=self._text,
                         fill=LABEL1, font=("SF Pro Display", 13, "bold"),
                         anchor="center")
        if self._subtext:
            self.create_text(w//2, cy + 16, text=self._subtext,
                             fill=LABEL2, font=("SF Pro Text", 9),
                             anchor="center")

    def _on_press(self, _):
        self._draw(pressed=True)

    def _on_release(self, e):
        self._draw(pressed=False)
        if self._cmd:
            self._cmd()

    def _on_enter(self, _):
        self.config(cursor="hand2")

    def _on_leave(self, _):
        self._draw(pressed=False)
        self.config(cursor="")


class App:
    def __init__(self, root):
        self.root = root
        root.title("Grid Split")
        root.geometry("420x580")
        root.resizable(False, False)
        root.configure(bg=BG)

        self.image_paths: list[Path] = []
        self.path_var   = StringVar(value="")
        self.status_var = StringVar(value="")
        self.status_ok  = True

        self._build_ui()

    def _build_ui(self):
        root = self.root

        # ── Title bar ──────────────────────────────────────────────
        title_frm = Frame(root, bg=BG)
        title_frm.pack(fill="x", padx=24, pady=(28, 0))
        Label(title_frm, text="Grid Split", bg=BG,
              fg=LABEL1, font=("SF Pro Display", 22, "bold")).pack(anchor="w")
        Label(title_frm, text="拆分图片为宫格", bg=BG,
              fg=LABEL2, font=("SF Pro Text", 12)).pack(anchor="w", pady=(2, 0))

        # ── Drop zone ──────────────────────────────────────────────
        drop_frm = Frame(root, bg=CARD, bd=0, highlightthickness=0)
        drop_frm.pack(fill="x", padx=20, pady=(20, 0))
        self._round_frame(drop_frm, height=100)

        self.drop_canvas = Canvas(drop_frm, bg=CARD, height=100,
                                  highlightthickness=0, bd=0)
        self.drop_canvas.pack(fill="x")
        self._draw_drop_zone(idle=True)
        self.drop_canvas.bind("<Button-1>", lambda e: self.pick())
        self.drop_canvas.bind("<Enter>",    lambda e: self.drop_canvas.config(cursor="hand2"))
        self.drop_canvas.bind("<Leave>",    lambda e: self.drop_canvas.config(cursor=""))

        if DND_AVAILABLE:
            self.drop_canvas.drop_target_register(DND_FILES)
            self.drop_canvas.dnd_bind("<<Drop>>", self.on_drop)

        # file name label
        self.name_label = Label(root, textvariable=self.path_var,
                                bg=BG, fg=LABEL2,
                                font=("SF Pro Text", 11),
                                wraplength=380, justify="center")
        self.name_label.pack(pady=(8, 0))

        # ── Section label ──────────────────────────────────────────
        Label(root, text="选择规格", bg=BG, fg=LABEL2,
              font=("SF Pro Text", 11)).pack(anchor="w", padx=24, pady=(18, 6))

        # ── Grid buttons ───────────────────────────────────────────
        btn_outer = Frame(root, bg=BG)
        btn_outer.pack(fill="x", padx=20)

        cols_per_row = 4
        for i, (cols, rows, label, tag) in enumerate(GRIDS):
            row_idx = i // cols_per_row
            col_idx = i % cols_per_row
            if col_idx == 0:
                row_frm = Frame(btn_outer, bg=BG)
                row_frm.pack(fill="x", pady=3)

            btn = RoundedButton(
                row_frm,
                text=label,
                subtext=tag,
                command=lambda c=cols, r=rows, t=tag: self.run(c, r, t),
                width=88, height=58,
                bg=CARD,
                accent=ACCENT,
            )
            btn.pack(side="left", padx=3)

        # ── Status bar ─────────────────────────────────────────────
        self.status_label = Label(root, textvariable=self.status_var,
                                  bg=BG, fg=SUCCESS,
                                  font=("SF Pro Text", 11))
        self.status_label.pack(pady=(16, 0))

    def _round_frame(self, frm, height=100):
        """Visual only — just sets a consistent height."""
        frm.configure(height=height)

    def _draw_drop_zone(self, idle=True, name=""):
        c = self.drop_canvas
        c.delete("all")
        w = 420 - 40  # padx=20 each side
        h = 100
        r = RADIUS

        fill = CARD
        dash = (6, 4)
        c.create_polygon(
            r, 0,  w-r, 0,
            w, 0,  w, r,
            w, h-r, w, h,
            w-r, h, r, h,
            0, h,  0, h-r,
            0, r,  0, 0,
            r, 0,
            smooth=True, fill=fill, outline=SEP, width=1
        )
        # dashed border overlay
        c.create_line(r, 1, w-r, 1, fill=SEP, dash=dash)
        c.create_line(r, h-1, w-r, h-1, fill=SEP, dash=dash)
        c.create_line(1, r, 1, h-r, fill=SEP, dash=dash)
        c.create_line(w-1, r, w-1, h-r, fill=SEP, dash=dash)

        if idle:
            hint = "拖拽图片 / 点击选择" if DND_AVAILABLE else "点击选择图片"
            c.create_text(w//2, h//2 - 10, text="＋",
                          fill=ACCENT, font=("SF Pro Display", 24, "bold"), anchor="center")
            c.create_text(w//2, h//2 + 18, text=hint,
                          fill=LABEL2, font=("SF Pro Text", 11), anchor="center")
        else:
            c.create_text(w//2, h//2 - 8, text="✓",
                          fill=SUCCESS, font=("SF Pro Display", 20, "bold"), anchor="center")
            c.create_text(w//2, h//2 + 14, text=name,
                          fill=LABEL1, font=("SF Pro Text", 11), anchor="center")

    def _set_paths(self, paths: list[Path]):
        valid   = [p for p in paths if p.exists() and p.suffix.lower() in SUPPORTED]
        skipped = len(paths) - len(valid)
        if not valid:
            messagebox.showwarning("提示", "没有可用的图片文件\n支持 png / jpg / jpeg / webp / bmp")
            return
        self.image_paths = valid
        if len(valid) == 1:
            display = valid[0].name
            self.path_var.set("")
            self._draw_drop_zone(idle=False, name=display)
        else:
            display = f"已选 {len(valid)} 张图片"
            self.path_var.set("")
            self._draw_drop_zone(idle=False, name=display)

        if skipped:
            self._set_status(f"跳过 {skipped} 个不支持的文件", ok=False)
        else:
            self._set_status("", ok=True)

    def _set_status(self, msg: str, ok: bool = True):
        self.status_var.set(msg)
        self.status_label.configure(fg=SUCCESS if ok else DANGER)

    def pick(self):
        paths = filedialog.askopenfilenames(
            title="选择图片（可多选）",
            filetypes=[("图片", "*.png *.jpg *.jpeg *.webp *.bmp"), ("所有文件", "*.*")],
        )
        if paths:
            self._set_paths([Path(p) for p in paths])

    def on_drop(self, event):
        files = self._parse_drop(event.data.strip())
        if files:
            self._set_paths([Path(f) for f in files])

    @staticmethod
    def _parse_drop(raw: str) -> list[str]:
        files, i = [], 0
        while i < len(raw):
            if raw[i] == "{":
                end = raw.find("}", i)
                if end == -1:
                    break
                files.append(raw[i+1:end])
                i = end + 1
            elif raw[i].isspace():
                i += 1
            else:
                end = raw.find(" ", i)
                if end == -1:
                    files.append(raw[i:])
                    break
                files.append(raw[i:end])
                i = end + 1
        return files

    def run(self, cols: int, rows: int, tag: str):
        if not self.image_paths:
            messagebox.showwarning("提示", "请先选择图片")
            return

        errors, last_dir = [], None
        for path in self.image_paths:
            if not path.exists():
                errors.append(f"{path.name}: file not found")
                continue
            try:
                last_dir = split_image(path, cols, rows)
            except Exception as e:
                errors.append(f"{path.name}: {e}")

        total  = len(self.image_paths)
        done   = total - len(errors)

        if errors:
            messagebox.showerror("部分失败", "\n".join(errors))

        if done > 0:
            self._set_status(f"完成 {done}/{total} 张  ·  {tag}", ok=True)
            try:
                if sys.platform == "win32" and last_dir:
                    os.startfile(last_dir.parent)  # type: ignore[attr-defined]
            except Exception:
                pass
        else:
            self._set_status("全部失败", ok=False)


def main():
    root = TkinterDnD.Tk() if DND_AVAILABLE else Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
