"""Auto Train Mil và Cổ Mộ — 8 ô độc lập, giao diện nhân vật xuyên nền."""
import ctypes
import math
import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from license_core import hwid, validate, saved_license, license_file
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageTk

if not hasattr(ctypes, 'windll'):
    raise SystemExit('Chỉ chạy trên Windows.')
user32 = ctypes.windll.user32
CALLBACK = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
user32.EnumWindows.argtypes = [CALLBACK, ctypes.c_void_p]
user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
user32.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
user32.IsWindow.argtypes = [ctypes.c_void_p]
user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
user32.PostMessageW.restype = ctypes.c_bool
WM_KEYDOWN, WM_KEYUP = 0x100, 0x101
TAB, SPACE = 0x09, 0x20
MAX_INTERVAL = 10800.0
W, H = 650, 790
CARD_W, CARD_H = 307, 149
CARD_X = (12, 331)
CARD_Y = (143, 302, 461, 620)
ASSET = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


def list_windows():
    found = []
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n < 1:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        title = buf.value.strip()
        if title and 'Auto Train Mil và Cổ Mộ' not in title:
            found.append((f'{title[:28]} [HWND {int(hwnd)}]', int(hwnd)))
        return True
    fn = CALLBACK(cb)
    user32.EnumWindows(fn, None)
    return found


def post_key(hwnd, vk):
    if not user32.IsWindow(hwnd):
        return False
    return bool(user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 1) and
                user32.PostMessageW(hwnd, WM_KEYUP, vk, 0xC0000001))


def font_path():
    """Prefer Windows fonts with full Vietnamese glyph coverage.

    Decorative Segoe Script fonts may render 'ổ'/'ộ' as missing-glyph boxes.
    Arial Bold Italic keeps the soft italic look while supporting Vietnamese.
    """
    options = [
        Path('C:/Windows/Fonts/arialbi.ttf'),  # Arial Bold Italic
        Path('C:/Windows/Fonts/ariali.ttf'),   # Arial Italic
        Path('C:/Windows/Fonts/segoeuiz.ttf'), # Segoe UI Bold Italic
        Path('C:/Windows/Fonts/segoeui.ttf'),
        Path('C:/Windows/Fonts/arial.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    ]
    return next((str(p) for p in options if p.is_file()), None)


def make_background():
    """Precompose translucent glass cards with the character, so Tk widgets don't hide it."""
    import numpy as np
    yy = np.linspace(0, 1, H)[:, None, None]
    top = np.array([218, 244, 255.0])[None, None, :]
    bottom = np.array([244, 239, 255.0])[None, None, :]
    arr = np.repeat((top * (1 - yy) + bottom * yy).astype('uint8'), W, axis=1)
    base = Image.fromarray(arr, 'RGB').convert('RGBA')
    path = ASSET / 'nhan_vat.png'
    if path.exists():
        character = Image.open(path).convert('RGBA')
        # The provided artwork has a white backdrop; make near-white pixels transparent.
        import numpy as np
        pixels = np.asarray(character).copy()
        rgb = pixels[:, :, :3].astype('float32')
        distance = np.min(rgb, axis=2)
        alpha = np.clip((252 - distance) / 25 * 255, 0, 255).astype('uint8')
        pixels[:, :, 3] = np.minimum(pixels[:, :, 3], alpha)
        character = Image.fromarray(pixels, 'RGBA')
        character.thumbnail((560, 690), Image.Resampling.LANCZOS)
        # Character is intentionally central and extends across the 8 panels.
        base.alpha_composite(character, ((W - character.width)//2, 100))
    # Subtle tinted-glass panels; art remains visible through the center.
    layer = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(layer)
    for r in range(4):
        for c in range(2):
            x, y = CARD_X[c], CARD_Y[r]
            d.rounded_rectangle((x, y, x + CARD_W, y + CARD_H), radius=12,
                                fill=(255, 255, 255, 175), outline=(91, 146, 196, 160), width=2)
    base = Image.alpha_composite(base, layer)
    # Header with soft shadow and translucent sheen.
    overlay = Image.new('RGBA', (W, H))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle((18, 12, W-18, 76), radius=20, fill=(255,255,255,165), outline=(255,255,255,230), width=2)
    title = 'Auto Train Mil và Cổ Mộ'
    selected_font = font_path()
    font = ImageFont.truetype(selected_font, 27) if selected_font else ImageFont.load_default()
    # Keep the full title inside the header at different font metrics.
    if selected_font:
        while ImageDraw.Draw(overlay).textbbox((0, 0), title, font=font)[2] > W - 64 and font.size > 16:
            font = ImageFont.truetype(selected_font, font.size - 1)
    bounds = od.textbbox((0,0), title, font=font)
    tx = (W - (bounds[2] - bounds[0])) // 2
    shadow = Image.new('RGBA', (W,H))
    sd = ImageDraw.Draw(shadow)
    sd.text((tx+2, 24), title, font=font, fill=(25,55,108,210), stroke_width=1)
    shadow = shadow.filter(ImageFilter.GaussianBlur(3))
    overlay = Image.alpha_composite(overlay, shadow)
    od = ImageDraw.Draw(overlay)
    od.text((tx, 21), title, font=font, fill=(26,91,156,255), stroke_width=1, stroke_fill=(255,255,255,220))
    od.line((tx+10, 58, W-tx-10, 58), fill=(255,255,255,190), width=2)
    base = Image.alpha_composite(base, overlay)
    return base.convert('RGB')


class Slot:
    def __init__(self, app, number):
        self.app, self.number = app, number
        self.running = False
        self.hwnd = None
        self.event = threading.Event()
        self.selection = tk.StringVar()
        self.status = tk.StringVar(value='Đã dừng')
        self.delays = [tk.StringVar(value='2') for _ in range(7)]
        self.enabled = [tk.BooleanVar(value=True) for _ in range(7)]
        self.find_monsters = tk.BooleanVar(value=True)
        col, row = (number - 1) % 2, (number - 1) // 2
        x, y = CARD_X[col], CARD_Y[row]
        # Controls float above a precomposed glass card (no opaque parent frame).
        self.app.canvas.create_text(x+12, y+11, text=f'NHÂN VẬT {number}', anchor='w',
                                    font=('Segoe UI', 9, 'bold'), fill='#174776')
        self.combo = ttk.Combobox(app.root, textvariable=self.selection, state='readonly', width=29)
        self.app.canvas.create_window(x+10, y+23, window=self.combo, anchor='nw', width=CARD_W-20, height=22)
        self.button = tk.Button(app.root, text='▶ BẬT AUTO', command=self.toggle,
                                bg='#168453', fg='white', activebackground='#0d6841',
                                relief='flat', bd=0, font=('Segoe UI', 8, 'bold'), cursor='hand2')
        self.app.canvas.create_window(x+10, y+48, window=self.button, anchor='nw', width=CARD_W-20, height=23)
        # Four rows per column: Tìm Quái + 6 skills + Bay chỗ khác (7).
        labels = ['Tìm Quái', 'Skill 1', 'Skill 2', 'Skill 3',
                  'Skill 4', 'Skill 5', 'Skill 6', 'Bay chỗ khác (7)']
        for index, label in enumerate(labels):
            cc, rr = divmod(index, 4)
            px, py = x + 8 + cc * 150, y + 76 + rr * 15
            is_find = index == 0
            skill_index = index - 1 if 1 <= index <= 3 else index - 1
            # Skill 4–6 and Bay use the same keyboard index as their key.
            if index >= 4:
                skill_index = index - 1
            variable = self.find_monsters if is_find else self.enabled[skill_index]
            check = tk.Checkbutton(app.root, text=label, variable=variable,
                                   font=('Segoe UI', 7 if index == 7 else 8),
                                   fg='#173b59', bg='#f0f7fc',
                                   activebackground='#f0f7fc', bd=0,
                                   highlightthickness=0, padx=0, pady=0)
            self.app.canvas.create_window(px, py, window=check, anchor='nw',
                                          width=105 if index == 7 else 91, height=16)
            if not is_find:
                entry = ttk.Entry(app.root, textvariable=self.delays[skill_index],
                                  width=5, font=('Segoe UI', 8))
                self.app.canvas.create_window(px+108 if index == 7 else px+94,
                                              py, window=entry, anchor='nw',
                                              width=30 if index == 7 else 45, height=17)
        self.app.canvas.create_text(x+CARD_W-12, y+137, text='s', anchor='e',
                                    font=('Segoe UI', 7), fill='#476a86')
        # Status is shown on button; keeps the panel compact.

    def refresh(self, windows):
        if not self.running:
            names = [name for name, _ in windows]
            self.combo['values'] = names
            if self.selection.get() not in names:
                self.selection.set('')

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        hwnd = dict(self.app.windows).get(self.selection.get())
        if hwnd is None or not user32.IsWindow(hwnd):
            messagebox.showwarning('Chưa chọn game', f'Hãy chọn nhân vật/game cho ô {self.number}.')
            return
        if any(s.running and s.hwnd == hwnd for s in self.app.slots if s is not self):
            messagebox.showwarning('Trùng nhân vật', 'Game này đang chạy ở một ô khác.')
            return
        schedule = {SPACE: 1.0}
        if self.find_monsters.get():
            schedule[TAB] = 3.5
        for i in range(7):
            if not self.enabled[i].get():
                continue
            try:
                interval = float(self.delays[i].get().replace(',', '.'))
                if not math.isfinite(interval) or not 0.1 <= interval <= MAX_INTERVAL:
                    raise ValueError
            except ValueError:
                messagebox.showerror('Thời gian không hợp lệ', f'{"Bay chỗ khác (7)" if i == 6 else f"Skill {i+1}"}: nhập 0,1–10800 giây.')
                return
            schedule[0x31 + i] = interval
        self.hwnd = hwnd
        self.running = True
        self.event = threading.Event()
        self.combo.config(state='disabled')
        self.button.config(text='■ TẮT AUTO', bg='#bb343f', activebackground='#a72430')
        threading.Thread(target=self.worker, args=(hwnd, schedule, self.event), daemon=True).start()

    def worker(self, hwnd, schedule, event):
        due = {key: time.monotonic() for key in schedule}
        reason = 'Đã dừng'
        while not event.is_set():
            if not user32.IsWindow(hwnd):
                reason = 'Game đã đóng'
                break
            now = time.monotonic()
            for vk, interval in schedule.items():
                if event.is_set():
                    break
                if now >= due[vk]:
                    if not post_key(hwnd, vk):
                        reason = 'Không gửi được phím'
                        event.set()
                        break
                    due[vk] = now + interval
            event.wait(0.025)
        try:
            self.app.root.after(0, lambda: self.finish(event, reason))
        except RuntimeError:
            pass

    def finish(self, event, reason):
        if self.event is event:
            self.stop(reason)

    def stop(self, reason='Đã dừng'):
        self.event.set()
        self.running = False
        self.hwnd = None
        self.combo.config(state='readonly')
        self.button.config(text='▶ BẬT AUTO', bg='#168453', activebackground='#0d6841')
        self.status.set(reason)


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.license_expiry = None
        self.root.withdraw()
        if not self.check_activation():
            self.root.destroy()
            self.root = None
            return
        self.root.deiconify()
        self.root.title('Auto Train Mil và Cổ Mộ')
        self.root.geometry(f'{W}x{H}')
        self.root.resizable(False, False)
        self.bg = ImageTk.PhotoImage(make_background())
        self.canvas = tk.Canvas(self.root, width=W, height=H, bd=0, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)
        self.canvas.create_image(0, 0, image=self.bg, anchor='nw')
        self.canvas.create_text(W//2, 89, text='8 NHÂN VẬT  •  SKILL 1–6  •  BAY CHỖ KHÁC (7)',
                                fill='#235778', font=('Segoe UI', 9, 'bold'))
        self.refresh_button = ttk.Button(self.root, text='↻ Làm mới danh sách game', command=self.refresh)
        self.canvas.create_window(W//2, 106, window=self.refresh_button, anchor='n', width=220, height=27)
        self.windows = []
        self.slots = [Slot(self, n) for n in range(1, 9)]
        self.canvas.create_text(W//2, 779, text='Zalo: TuanHo  •  0398438721',
                                fill='#174776', font=('Segoe UI', 9, 'bold'))
        self.refresh()
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.after(60000, self.check_expiry)

    def check_activation(self):
        token = saved_license()
        if token:
            try:
                self.license_expiry = validate(token)
                return True
            except ValueError:
                pass
        dialog = tk.Toplevel(self.root)
        dialog.title('Kích hoạt Auto Train Mil và Cổ Mộ')
        dialog.geometry('510x290')
        dialog.resizable(False, False)
        dialog.configure(bg='#f3f8fd')
        dialog.grab_set()
        tk.Label(dialog, text='KÍCH HOẠT BẢN QUYỀN', font=('Segoe UI', 15, 'bold'),
                 fg='#20598c', bg='#f3f8fd').pack(pady=(14, 6))
        tk.Label(dialog, text='Mã máy (HWID) - gửi mã này cho người cấp phép:',
                 bg='#f3f8fd').pack()
        machine = hwid()
        hwid_var = tk.StringVar(value=machine)
        tk.Entry(dialog, textvariable=hwid_var, state='readonly', width=46,
                 justify='center').pack(pady=5)
        tk.Button(dialog, text='Sao chép HWID', command=lambda: (dialog.clipboard_clear(), dialog.clipboard_append(machine))).pack()
        tk.Label(dialog, text='Dán mã kích hoạt được cấp:', bg='#f3f8fd').pack(pady=(12, 2))
        token_entry = tk.Text(dialog, height=3, width=58, wrap='word')
        token_entry.pack()
        result = {'ok': False}
        def activate():
            token = token_entry.get('1.0', 'end').strip()
            try:
                expiry = validate(token, machine)
                license_file().write_text(token, encoding='utf-8')
            except (ValueError, OSError) as exc:
                messagebox.showerror('Không thể kích hoạt', str(exc), parent=dialog)
                return
            self.license_expiry = expiry
            result['ok'] = True
            dialog.destroy()
        tk.Button(dialog, text='KÍCH HOẠT', command=activate, bg='#168453',
                  fg='white', font=('Segoe UI', 10, 'bold')).pack(pady=10)
        tk.Label(dialog, text='Zalo: TuanHo - 0398438721', bg='#f3f8fd').pack()
        dialog.protocol('WM_DELETE_WINDOW', dialog.destroy)
        self.root.wait_window(dialog)
        return result['ok']

    def check_expiry(self):
        try:
            self.license_expiry = validate(saved_license())
        except ValueError as exc:
            for slot in self.slots:
                slot.stop('Bản quyền hết hạn')
            messagebox.showwarning('Bản quyền', str(exc))
            self.close()
            return
        self.root.after(60000, self.check_expiry)

    def refresh(self):
        self.windows = list_windows()
        for slot in self.slots:
            slot.refresh(self.windows)

    def close(self):
        for slot in self.slots:
            slot.event.set()
        self.root.destroy()

    def run(self):
        if self.root is not None:
            self.root.mainloop()


if __name__ == '__main__':
    App().run()
