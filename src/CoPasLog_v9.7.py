import sqlite3
from pynput import keyboard
import pyautogui
import pyperclip
import time
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import threading

def init_db():
    conn = sqlite3.connect("copaslog_data.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS History (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    content TEXT,
                    preview TEXT)""")
    conn.commit()
    conn.close()

class CoPasLogV9:
    def __init__(self, root):
        self.root = root
        self.root.title("CoPasLog_v9.7")
        self.root.geometry("500x700")
        self.root.configure(bg="#1e1e1e") 
        self.root.attributes("-topmost", True)
        
        self.drag_data = None
        
        try:
            self.last_clipboard_content = pyperclip.paste()
        except:
            self.last_clipboard_content = ""

        # Setup UI
        self.create_menu() # Panggil menu sebelum widgets
        self.setup_styles()
        self.create_widgets()
        self.refresh_list()
        
        threading.Thread(target=self.start_hotkeys, daemon=True).start()
        threading.Thread(target=self.monitor_clipboard, daemon=True).start()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Vertical.TScrollbar", background="#333", troughcolor="#1e1e1e")

    def create_menu(self):
        # Membuat Menu Bar dengan warna standar sistem agar terlihat jelas
        menubar = tk.Menu(self.root)
        
        # Menu File
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Export History (.txt)", command=self.export_history)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Menu Setting
        setting_menu = tk.Menu(menubar, tearoff=0)
        # Submenu Transparansi
        trans_menu = tk.Menu(setting_menu, tearoff=0)
        trans_menu.add_command(label="100% (Solid)", command=lambda: self.set_opacity(1.0))
        trans_menu.add_command(label="80% (Glass)", command=lambda: self.set_opacity(0.8))
        trans_menu.add_command(label="60% (Ghost)", command=lambda: self.set_opacity(0.6))
        setting_menu.add_cascade(label="Transparansi Jendela", menu=trans_menu)
        
        setting_menu.add_separator()
        setting_menu.add_command(label="Hapus Semua History", command=self.clear_all, foreground="red")
        menubar.add_cascade(label="Setting", menu=setting_menu)
        
        # Pasang menubar ke root
        self.root.config(menu=menubar)

    def create_widgets(self):
        # Search Bar Area
        search_frame = tk.Frame(self.root, bg="#1e1e1e", pady=10)
        search_frame.pack(fill="x", padx=20)
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_list())
        
        tk.Label(search_frame, text="Pencarian:", bg="#1e1e1e", fg="white", font=("Segoe UI", 9)).pack(side="left", padx=5)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, bg="#2d2d2d", fg="white", 
                                 insertbackground="white", relief="flat", font=("Segoe UI", 10))
        search_entry.pack(side="left", fill="x", expand=True)

        # List Area
        container = tk.Frame(self.root, bg="#1e1e1e")
        container.pack(fill="both", expand=True, padx=5, pady=5)
        self.canvas = tk.Canvas(container, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#1e1e1e")
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=460)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def set_opacity(self, value):
        self.root.attributes("-alpha", value)

    def export_history(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            try:
                conn = sqlite3.connect("copaslog_data.db")
                rows = conn.execute("SELECT content FROM History ORDER BY id DESC").fetchall()
                conn.close()
                with open(file_path, "w", encoding="utf-8") as f:
                    for row in rows:
                        f.write(row[0] + "\n" + "="*40 + "\n")
                messagebox.showinfo("Berhasil", "Data berhasil disimpan!")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal mengekspor: {e}")

    def refresh_list(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        conn = sqlite3.connect("copaslog_data.db")
        c = conn.cursor()
        query = self.search_var.get()
        if query:
            c.execute("SELECT id, preview, content FROM History WHERE content LIKE ? ORDER BY id DESC", ('%'+query+'%',))
        else:
            c.execute("SELECT id, preview, content FROM History ORDER BY id DESC LIMIT 50")
        rows = c.fetchall()
        conn.close()

        for index, row in enumerate(rows, start=1):
            data_id, preview, content = row
            row_frame = tk.Frame(self.scrollable_frame, bg="#1e1e1e")
            row_frame.pack(fill="x", pady=2, padx=5)

            tk.Label(row_frame, text=f"{index}.", bg="#1e1e1e", fg="#555", width=4).pack(side="left")

            lbl = tk.Label(row_frame, text=preview, font=("Segoe UI", 9), anchor="w", 
                          bg="#2d2d2d", fg="#dcdcdc", padx=10, pady=10, cursor="fleur")
            lbl.pack(side="left", fill="x", expand=True)

            # Drag Logic
            lbl.bind("<Button-1>", lambda e, c=content: self.start_manual_drag(c))
            lbl.bind("<ButtonRelease-1>", self.stop_manual_drag)

            tk.Button(row_frame, text=" ✕ ", bg="#2d2d2d", fg="#e74c3c", relief="flat",
                      command=lambda i=data_id: self.delete_single(i)).pack(side="right", padx=2)

    def start_manual_drag(self, content):
        self.drag_data = content
        self.root.config(cursor="hand1")

    def stop_manual_drag(self, event):
        if self.drag_data:
            pyperclip.copy(self.drag_data)
            self.root.withdraw() 
            time.sleep(0.2)
            pyautogui.click() 
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)
            self.root.deiconify()
            self.drag_data = None
            self.root.config(cursor="")

    def delete_single(self, data_id):
        conn = sqlite3.connect("copaslog_data.db")
        conn.execute("DELETE FROM History WHERE id = ?", (data_id,))
        conn.commit()
        conn.close()
        self.refresh_list()

    def monitor_clipboard(self):
        while True:
            try:
                current_content = pyperclip.paste()
                if current_content != self.last_clipboard_content and current_content.strip() != "":
                    self.last_clipboard_content = current_content
                    self.save_to_db(current_content)
                    self.root.after(0, self.refresh_list)
            except: pass
            time.sleep(0.8)

    def save_to_db(self, text):
        conn = sqlite3.connect("copaslog_data.db")
        c = conn.cursor()
        preview_text = (text[:40].replace('\n', ' ') + '...') if len(text) > 40 else text.replace('\n', ' ')
        c.execute("INSERT INTO History (content, preview) VALUES (?, ?)", (text, preview_text))
        conn.commit()
        conn.close()

    def clear_all(self):
        if messagebox.askyesno("Konfirmasi", "Hapus seluruh history secara permanen?"):
            conn = sqlite3.connect("copaslog_data.db")
            conn.execute("DELETE FROM History")
            conn.commit()
            conn.close()
            self.refresh_list()

    def start_hotkeys(self):
        with keyboard.GlobalHotKeys({"<cmd>+<shift>+a": self.focus_window}) as h:
            h.join()

    def focus_window(self):
        time.sleep(0.1)
        pyautogui.press('backspace')
        self.root.after(0, lambda: [self.root.deiconify(), self.root.attributes("-topmost", True), self.root.focus_force()])

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = CoPasLogV9(root)
    root.mainloop()