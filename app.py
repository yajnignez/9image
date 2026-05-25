import os
import sys
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, StringVar
from tkinter import ttk

from PIL import Image

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    TkinterDnD = None
    DND_FILES = None
    DND_AVAILABLE = False


GRIDS = [(2, "4 张 (2x2)"), (3, "9 张 (3x3)"), (4, "16 张 (4x4)"), (5, "25 张 (5x5)")]
SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def split_image(image_path: Path, n: int) -> Path:
    img = Image.open(image_path)
    w, h = img.size
    tile_w = w // n
    tile_h = h // n

    out_dir = image_path.parent / f"{image_path.stem}_{n}x{n}"
    out_dir.mkdir(exist_ok=True)

    src_ext = image_path.suffix.lower()
    # webp → png on output; unknown → png
    if src_ext == ".webp" or src_ext not in SUPPORTED:
        out_ext = ".png"
    else:
        out_ext = src_ext

    # If converting webp→png and the source has no alpha, drop to RGB so the PNG isn't bloated
    if out_ext == ".png" and img.mode not in ("RGB", "RGBA", "L", "LA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")

    idx = 1
    for r in range(n):
        for c in range(n):
            left = c * tile_w
            top = r * tile_h
            right = w if c == n - 1 else left + tile_w
            bottom = h if r == n - 1 else top + tile_h
            tile = img.crop((left, top, right, bottom))
            # JPEG can't hold alpha
            if out_ext in (".jpg", ".jpeg") and tile.mode in ("RGBA", "LA", "P"):
                tile = tile.convert("RGB")
            tile.save(out_dir / f"{idx:02d}{out_ext}")
            idx += 1
    return out_dir


class App:
    def __init__(self, root):
        self.root = root
        root.title("宫格拆图")
        root.geometry("380x300")
        root.resizable(False, False)

        self.image_path: Path | None = None
        self.path_var = StringVar(value="未选择图片")
        self.status_var = StringVar(value="")

        frm = ttk.Frame(root, padding=14)
        frm.pack(fill="both", expand=True)

        # Drop zone
        drop_text = "拖拽图片到此处\n或点击选择" if DND_AVAILABLE else "点击选择图片\n（拖拽功能未启用）"
        self.drop = ttk.Label(
            frm,
            text=drop_text,
            anchor="center",
            relief="ridge",
            padding=20,
            foreground="#666",
        )
        self.drop.pack(fill="x")
        self.drop.bind("<Button-1>", lambda e: self.pick())

        if DND_AVAILABLE:
            self.drop.drop_target_register(DND_FILES)
            self.drop.dnd_bind("<<Drop>>", self.on_drop)

        ttk.Label(frm, textvariable=self.path_var, foreground="#555").pack(
            fill="x", pady=(6, 10)
        )

        ttk.Label(frm, text="拆分为:").pack(anchor="w")
        grid_frm = ttk.Frame(frm)
        grid_frm.pack(fill="x", pady=4)
        for i, (n, label) in enumerate(GRIDS):
            b = ttk.Button(grid_frm, text=label, command=lambda n=n: self.run(n))
            b.grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)
        grid_frm.columnconfigure(0, weight=1)
        grid_frm.columnconfigure(1, weight=1)

        ttk.Label(frm, textvariable=self.status_var, foreground="#0a7").pack(
            fill="x", pady=(10, 0)
        )

    def set_image(self, path_str: str):
        path = Path(path_str)
        if not path.exists():
            messagebox.showwarning("提示", f"文件不存在: {path_str}")
            return
        if path.suffix.lower() not in SUPPORTED:
            messagebox.showwarning(
                "提示", f"不支持的格式: {path.suffix}\n支持 png/jpg/jpeg/webp/bmp"
            )
            return
        self.image_path = path
        self.path_var.set(path.name)
        self.status_var.set("")

    def pick(self):
        path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[
                ("图片", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("所有文件", "*.*"),
            ],
        )
        if path:
            self.set_image(path)

    def on_drop(self, event):
        # event.data is a string like '{C:/path with spaces/img.png}' or 'C:/img.png C:/img2.png'
        raw = event.data.strip()
        files = self._parse_drop(raw)
        if files:
            self.set_image(files[0])

    @staticmethod
    def _parse_drop(raw: str) -> list[str]:
        files = []
        i = 0
        while i < len(raw):
            if raw[i] == "{":
                end = raw.find("}", i)
                if end == -1:
                    break
                files.append(raw[i + 1 : end])
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

    def run(self, n: int):
        if not self.image_path or not self.image_path.exists():
            messagebox.showwarning("提示", "请先选择图片")
            return
        try:
            out_dir = split_image(self.image_path, n)
        except Exception as e:
            messagebox.showerror("出错了", str(e))
            return
        self.status_var.set(f"完成: {out_dir.name}")
        try:
            if sys.platform == "win32":
                os.startfile(out_dir)  # type: ignore[attr-defined]
        except Exception:
            pass


def main():
    root = TkinterDnD.Tk() if DND_AVAILABLE else Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
