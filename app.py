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


GRIDS = [(2, "4 (2x2)"), (3, "9 (3x3)"), (4, "16 (4x4)"), (5, "25 (5x5)")]
SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def split_image(image_path: Path, n: int) -> Path:
    img = Image.open(image_path)
    w, h = img.size
    tile_w = w // n
    tile_h = h // n

    out_dir = image_path.parent / f"{image_path.stem}_{n}x{n}"
    out_dir.mkdir(exist_ok=True)

    src_ext = image_path.suffix.lower()
    if src_ext == ".webp" or src_ext not in SUPPORTED:
        out_ext = ".png"
    else:
        out_ext = src_ext

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
            if out_ext in (".jpg", ".jpeg") and tile.mode in ("RGBA", "LA", "P"):
                tile = tile.convert("RGB")
            tile.save(out_dir / f"{idx:02d}{out_ext}")
            idx += 1
    return out_dir


class App:
    def __init__(self, root):
        self.root = root
        root.title("宫格拆图")
        root.geometry("380x320")
        root.resizable(False, False)

        self.image_paths: list[Path] = []
        self.path_var = StringVar(value="未选择图片")
        self.status_var = StringVar(value="")

        frm = ttk.Frame(root, padding=14)
        frm.pack(fill="both", expand=True)

        drop_text = "拖拽图片到此处（支持多张）\n或点击选择" if DND_AVAILABLE else "点击选择图片（支持多选）\n（拖拽功能未启用）"
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

    def _set_paths(self, paths: list[Path]):
        valid = [p for p in paths if p.exists() and p.suffix.lower() in SUPPORTED]
        skipped = len(paths) - len(valid)
        if not valid:
            messagebox.showwarning("提示", "没有可用的图片文件\n支持 png/jpg/jpeg/webp/bmp")
            return
        self.image_paths = valid
        if len(valid) == 1:
            self.path_var.set(valid[0].name)
        else:
            self.path_var.set(f"已选 {len(valid)} 张图片")
        if skipped:
            self.status_var.set(f"跳过 {skipped} 个不支持的文件")
        else:
            self.status_var.set("")

    def pick(self):
        paths = filedialog.askopenfilenames(
            title="选择图片（可多选）",
            filetypes=[
                ("图片", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("所有文件", "*.*"),
            ],
        )
        if paths:
            self._set_paths([Path(p) for p in paths])

    def on_drop(self, event):
        raw = event.data.strip()
        files = self._parse_drop(raw)
        if files:
            self._set_paths([Path(f) for f in files])

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
        if not self.image_paths:
            messagebox.showwarning("提示", "请先选择图片")
            return

        errors = []
        last_dir = None
        for path in self.image_paths:
            if not path.exists():
                errors.append(f"{path.name}: file not found")
                continue
            try:
                last_dir = split_image(path, n)
            except Exception as e:
                errors.append(f"{path.name}: {e}")

        total = len(self.image_paths)
        failed = len(errors)
        done = total - failed

        if errors:
            messagebox.showerror("部分失败", "\n".join(errors))

        if done > 0:
            self.status_var.set(f"完成 {done}/{total} 张 → {n}x{n}")
            try:
                if sys.platform == "win32" and last_dir:
                    os.startfile(last_dir.parent)  # type: ignore[attr-defined]
            except Exception:
                pass
        else:
            self.status_var.set("全部失败")


def main():
    root = TkinterDnD.Tk() if DND_AVAILABLE else Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
