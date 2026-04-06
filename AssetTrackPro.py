import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from datetime import datetime
import hashlib
import os
import shutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image
import sys
import tempfile

DB_NAME = "data/inventory.db"

# ---------------- Setup Folders ----------------
def setup_folders():
    os.makedirs("data", exist_ok=True)
    os.makedirs("backup", exist_ok=True)

# ---------------- Security ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ---------------- Database ----------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS inventory(
        id INTEGER PRIMARY KEY,
        name TEXT,
        sku TEXT,
        quantity INTEGER,
        cost REAL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS sales(
        id INTEGER PRIMARY KEY,
        sku TEXT,
        quantity INTEGER,
        price REAL,
        date TEXT
    )''')

    c.execute("INSERT OR IGNORE INTO users VALUES ('admin', ?, 'Admin')",
              (hash_password("admin"),))

    conn.commit()
    conn.close()

# ---------------- Backup ----------------
def backup_db():
    backup_file = f"backup/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy(DB_NAME, backup_file)
    messagebox.showinfo("Backup", f"Backup created:\n{backup_file}")

# ---------------- Resource Path ----------------
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller temp path
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---------------- Icon (MULTI-SIZE ICO) ----------------
def get_app_icon(root):
    try:
        png_path = resource_path(os.path.join("assets", "AssetTrackPrologodesignconcept.png"))

        if not os.path.exists(png_path):
            print("PNG icon not found.")
            return

        # Create temp ico path
        temp_dir = tempfile.gettempdir()
        ico_path = os.path.join(temp_dir, "assettrackpro_icon.ico")

        # Load and convert PNG
        img = Image.open(png_path).convert("RGBA")

        # Generate multi-resolution ICO
        sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
        img.save(ico_path, format='ICO', sizes=sizes)

        root.iconbitmap(ico_path)

    except Exception as e:
        print(f"Icon load failed: {e}")

# ---------------- Login ----------------
class Login:
    def __init__(self, root):
        self.root = root
        self.root.title("AssetTrack Pro - Login")
        self.root.geometry("300x200")
        get_app_icon(self.root)

        tk.Label(root, text="AssetTrack Pro", font=("Arial", 14, "bold")).pack(pady=10)

        tk.Label(root, text="Username").pack()
        self.user = tk.Entry(root)
        self.user.pack()

        tk.Label(root, text="Password").pack()
        self.pw = tk.Entry(root, show="*")
        self.pw.pack()

        tk.Button(root, text="Login", command=self.check).pack(pady=10)

    def check(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        result = c.execute(
            "SELECT role FROM users WHERE username=? AND password=?",
            (self.user.get(), hash_password(self.pw.get()))
        ).fetchone()

        conn.close()

        if result:
            self.root.destroy()
            main = tk.Tk()
            App(main, result[0])
            main.mainloop()
        else:
            messagebox.showerror("Error", "Invalid login")

# ---------------- Main App ----------------
class App:
    def __init__(self, root, role):
        self.root = root
        self.role = role
        root.title(f"AssetTrack Pro ({role})")
        root.geometry("1200x700")
        get_app_icon(root)

        # Top Bar
        top = tk.Frame(root, bg="#2c3e50", height=50)
        top.pack(fill="x")
        tk.Label(top, text="AssetTrack Pro", fg="white", bg="#2c3e50",
                 font=("Arial", 16, "bold")).pack(side="left", padx=10)

        # Sidebar
        sidebar = tk.Frame(root, bg="#34495e", width=200)
        sidebar.pack(side="left", fill="y")

        # Tabs
        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True)

        self.dashboard_tab = tk.Frame(self.tabs)
        self.inv_tab = tk.Frame(self.tabs)
        self.sales_tab = tk.Frame(self.tabs)
        self.report_tab = tk.Frame(self.tabs)

        self.tabs.add(self.dashboard_tab, text="Dashboard")
        self.tabs.add(self.inv_tab, text="Inventory")
        self.tabs.add(self.sales_tab, text="Sales")
        self.tabs.add(self.report_tab, text="Reports")

        tk.Button(sidebar, text="Dashboard", command=lambda: self.tabs.select(self.dashboard_tab)).pack(fill="x")
        tk.Button(sidebar, text="Inventory", command=lambda: self.tabs.select(self.inv_tab)).pack(fill="x")
        tk.Button(sidebar, text="Sales", command=lambda: self.tabs.select(self.sales_tab)).pack(fill="x")
        tk.Button(sidebar, text="Reports", command=lambda: self.tabs.select(self.report_tab)).pack(fill="x")
        tk.Button(sidebar, text="Backup DB", command=backup_db).pack(fill="x", pady=20)

        self.build_dashboard()
        self.build_inventory()
        self.build_sales()
        self.build_reports()

    # ---------------- Dashboard ----------------
    def build_dashboard(self):
        self.dashboard_label = tk.Label(self.dashboard_tab, font=("Arial", 16))
        self.dashboard_label.pack(pady=20)
        self.update_dashboard()

    def update_dashboard(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        total_items = c.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        total_sales = c.execute("SELECT SUM(price*quantity) FROM sales").fetchone()[0] or 0

        conn.close()

        self.dashboard_label.config(
            text=f"Total Items: {total_items}\nTotal Revenue: ${round(total_sales,2)}"
        )

    # ---------------- Inventory ----------------
    def build_inventory(self):
        cols = ("ID", "Name", "SKU", "Qty", "Cost")
        self.tree = ttk.Treeview(self.inv_tab, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
        self.tree.pack(fill="both", expand=True)

        frame = tk.Frame(self.inv_tab)
        frame.pack()

        tk.Button(frame, text="Add", command=self.add_item).pack(side="left")
        tk.Button(frame, text="Delete", command=self.delete_item).pack(side="left")

        self.load_inventory()

    def add_item(self):
        w = tk.Toplevel(self.root)
        get_app_icon(w)

        tk.Label(w, text="Name").pack()
        name = tk.Entry(w); name.pack()

        tk.Label(w, text="SKU").pack()
        sku = tk.Entry(w); sku.pack()

        tk.Label(w, text="Qty").pack()
        qty = tk.Entry(w); qty.pack()

        tk.Label(w, text="Cost").pack()
        cost = tk.Entry(w); cost.pack()

        def save():
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO inventory(name,sku,quantity,cost) VALUES(?,?,?,?)",
                      (name.get(), sku.get(), int(qty.get()), float(cost.get())))
            conn.commit()
            conn.close()
            w.destroy()
            self.load_inventory()
            self.update_dashboard()

        tk.Button(w, text="Save", command=save).pack()

    def delete_item(self):
        sel = self.tree.selection()
        if not sel:
            return

        item_id = self.tree.item(sel[0])["values"][0]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM inventory WHERE id=?", (item_id,))
        conn.commit()
        conn.close()

        self.load_inventory()
        self.update_dashboard()

    def load_inventory(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        for r in self.tree.get_children():
            self.tree.delete(r)

        for row in c.execute("SELECT * FROM inventory"):
            self.tree.insert("", tk.END, values=row)

        conn.close()

    # ---------------- Sales ----------------
    def build_sales(self):
        tk.Button(self.sales_tab, text="Record Sale", command=self.sale_window).pack(pady=20)

    def sale_window(self):
        w = tk.Toplevel(self.root)
        get_app_icon(w)

        tk.Label(w, text="SKU").pack()
        sku = tk.Entry(w); sku.pack()

        tk.Label(w, text="Qty").pack()
        qty = tk.Entry(w); qty.pack()

        tk.Label(w, text="Price").pack()
        price = tk.Entry(w); price.pack()

        def save():
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO sales(sku,quantity,price,date) VALUES(?,?,?,?)",
                      (sku.get(), int(qty.get()), float(price.get()),
                       datetime.now().strftime("%Y-%m-%d")))
            conn.commit()
            conn.close()
            w.destroy()
            self.update_dashboard()

        tk.Button(w, text="Save", command=save).pack()

    # ---------------- Reports ----------------
    def build_reports(self):
        self.fig = plt.Figure(figsize=(6, 4))
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.report_tab)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        tk.Button(self.report_tab, text="Refresh", command=self.update_chart).pack()
        tk.Button(self.report_tab, text="Export CSV", command=self.export_csv).pack()

        self.update_chart()

    def update_chart(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        data = c.execute("SELECT date, SUM(price*quantity) FROM sales GROUP BY date").fetchall()
        conn.close()

        dates = [d[0] for d in data]
        values = [d[1] for d in data]

        self.ax.clear()
        self.ax.plot(dates, values)
        self.ax.set_title("Sales Trend")

        self.canvas.draw()

    def export_csv(self):
        file = filedialog.asksaveasfilename(defaultextension=".csv")
        if not file:
            return

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        with open(file, "w") as f:
            for row in c.execute("SELECT * FROM sales"):
                f.write(",".join(map(str, row)) + "\n")

        conn.close()
        messagebox.showinfo("Export", "CSV Exported")

# ---------------- Run ----------------
if __name__ == "__main__":
    setup_folders()
    init_db()

    root = tk.Tk()
    Login(root)
    root.mainloop()