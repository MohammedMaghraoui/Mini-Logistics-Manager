"""Mini Logistics Manager - Desktop app (Tkinter + SQLite).

Uses the same logistics.db as the console versions, as long as the files
sit in the same folder.
"""
import csv
import os
import sqlite3
import tkinter as tk
import uuid
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logistics.db")
STATUSES = ["Pending", "In Transit", "Delivered"]
BASE_FEE = 25.0
PRICE_PER_KG = 8.0

STATUS_COLORS = {"Pending": "#fef3c7", "In Transit": "#dbeafe", "Delivered": "#dcfce7"}
ACCENT = "#2563eb"

SHIPMENT_QUERY = """
    SELECT s.*, d.name AS driver
    FROM shipments s
    LEFT JOIN drivers d ON s.driver_id = d.id
"""


# ====================== Database layer ======================
class Database:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, phone TEXT NOT NULL, vehicle TEXT NOT NULL)"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS shipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_code TEXT UNIQUE NOT NULL,
                customer TEXT NOT NULL, origin TEXT NOT NULL,
                destination TEXT NOT NULL, weight_kg REAL NOT NULL,
                price REAL NOT NULL, status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL,
                driver_id INTEGER REFERENCES drivers(id))"""
        )
        cols = [r["name"] for r in self.conn.execute("PRAGMA table_info(shipments)")]
        if "driver_id" not in cols:
            self.conn.execute(
                "ALTER TABLE shipments ADD COLUMN driver_id INTEGER REFERENCES drivers(id)"
            )
        self.conn.commit()

    def shipments(self, term="", status="All"):
        sql = SHIPMENT_QUERY + " WHERE (s.tracking_code LIKE ? OR s.customer LIKE ?)"
        params = [f"%{term}%", f"%{term}%"]
        if status != "All":
            sql += " AND s.status = ?"
            params.append(status)
        return self.conn.execute(sql + " ORDER BY s.id DESC", params).fetchall()

    def add_shipment(self, customer, origin, destination, weight):
        code = "SHP-" + uuid.uuid4().hex[:6].upper()
        price = round(BASE_FEE + PRICE_PER_KG * weight, 2)
        with self.conn:
            self.conn.execute(
                "INSERT INTO shipments (tracking_code, customer, origin, destination,"
                " weight_kg, price, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (code, customer, origin, destination, weight, price,
                 datetime.now().strftime("%Y-%m-%d %H:%M")),
            )
        return code

    def update_status(self, code, status):
        with self.conn:
            self.conn.execute(
                "UPDATE shipments SET status = ? WHERE tracking_code = ?", (status, code)
            )

    def assign_driver(self, code, driver_id):
        with self.conn:
            self.conn.execute(
                "UPDATE shipments SET driver_id = ? WHERE tracking_code = ?",
                (driver_id, code),
            )

    def delete_shipment(self, code):
        with self.conn:
            self.conn.execute("DELETE FROM shipments WHERE tracking_code = ?", (code,))

    def drivers(self):
        return self.conn.execute("SELECT * FROM drivers ORDER BY id").fetchall()

    def add_driver(self, name, phone, vehicle):
        with self.conn:
            self.conn.execute(
                "INSERT INTO drivers (name, phone, vehicle) VALUES (?, ?, ?)",
                (name, phone, vehicle),
            )

    def delete_driver(self, driver_id):
        with self.conn:
            self.conn.execute(
                "UPDATE shipments SET driver_id = NULL WHERE driver_id = ?", (driver_id,)
            )
            self.conn.execute("DELETE FROM drivers WHERE id = ?", (driver_id,))

    def stats(self):
        total = self.conn.execute("SELECT COUNT(*) FROM shipments").fetchone()[0]
        revenue = self.conn.execute(
            "SELECT COALESCE(SUM(price), 0) FROM shipments"
        ).fetchone()[0]
        per_status = {
            s: self.conn.execute(
                "SELECT COUNT(*) FROM shipments WHERE status = ?", (s,)
            ).fetchone()[0]
            for s in STATUSES
        }
        per_driver = self.conn.execute(
            """SELECT d.name, d.vehicle, COUNT(s.id) AS total
               FROM drivers d LEFT JOIN shipments s ON s.driver_id = d.id
               GROUP BY d.id ORDER BY total DESC"""
        ).fetchall()
        return total, revenue, per_status, per_driver


# ====================== Reusable form dialog ======================
class FormDialog(tk.Toplevel):
    """fields = [(label, key, choices_or_None), ...] -> self.result dict or None"""

    def __init__(self, parent, title, fields):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.result = None
        self.vars = {}

        frame = ttk.Frame(self, padding=18)
        frame.pack()
        for row, (label, key, choices) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 14))
            var = tk.StringVar()
            if choices:
                widget = ttk.Combobox(frame, textvariable=var, values=choices,
                                      state="readonly", width=30)
                widget.current(0)
            else:
                widget = ttk.Entry(frame, textvariable=var, width=32)
            widget.grid(row=row, column=1, pady=5)
            self.vars[key] = var
            if row == 0:
                widget.focus_set()

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="Save", style="Accent.TButton",
                   command=self.on_ok).pack(side="right")

        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.grab_set()
        self.wait_window()

    def on_ok(self):
        self.result = {k: v.get().strip() for k, v in self.vars.items()}
        self.destroy()


# ====================== Main application ======================
class App(tk.Tk):
    def __init__(self, db_path=DB_FILE):
        super().__init__()
        self.db = Database(db_path)
        self.title("Mini Logistics Manager")
        self.geometry("1050x620")
        self.minsize(900, 520)
        self.setup_style()

        header = tk.Frame(self, bg=ACCENT, height=54)
        header.pack(fill="x")
        tk.Label(header, text="Mini Logistics Manager", bg=ACCENT, fg="white",
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=18, pady=10)

        self.status_bar = ttk.Label(self, text="Ready", anchor="w", padding=(12, 4))
        self.status_bar.pack(side="bottom", fill="x")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=10)
        self.build_shipments_tab()
        self.build_drivers_tab()
        self.build_dashboard_tab()
        self.tabs.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())
        self.refresh_all()

    # ---------- styling ----------
    def setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure("Accent.TButton", background=ACCENT, foreground="white",
                        font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#1d4ed8")])

    def say(self, message):
        self.status_bar.config(text=message)

    def make_tree(self, parent, columns):
        """columns = [(key, heading, width), ...]"""
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill="both", expand=True)
        tree = ttk.Treeview(wrapper, columns=[c[0] for c in columns],
                            show="headings", selectmode="browse")
        for key, heading, width in columns:
            tree.heading(key, text=heading)
            tree.column(key, width=width, anchor="w")
        scroll = ttk.Scrollbar(wrapper, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return tree

    # ---------- Shipments tab ----------
    def build_shipments_tab(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="  Shipments  ")

        top = ttk.Frame(tab)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh_shipments())
        ttk.Entry(top, textvariable=self.search_var, width=26).pack(side="left", padx=(6, 16))
        ttk.Label(top, text="Status:").pack(side="left")
        self.filter_var = tk.StringVar(value="All")
        box = ttk.Combobox(top, textvariable=self.filter_var, state="readonly",
                           values=["All"] + STATUSES, width=12)
        box.pack(side="left", padx=6)
        box.bind("<<ComboboxSelected>>", lambda e: self.refresh_shipments())

        ttk.Button(top, text="Export CSV", command=self.export_csv).pack(side="right")
        ttk.Button(top, text="Delete", command=self.delete_shipment).pack(side="right", padx=6)
        ttk.Button(top, text="Assign Driver", command=self.assign_driver).pack(side="right")
        ttk.Button(top, text="Update Status", command=self.update_status).pack(side="right", padx=6)
        ttk.Button(top, text="+ New Shipment", style="Accent.TButton",
                   command=self.add_shipment).pack(side="right")

        self.ship_tree = self.make_tree(tab, [
            ("code", "Tracking code", 110), ("customer", "Customer", 130),
            ("route", "Route", 190), ("weight", "Kg", 60), ("price", "Price", 80),
            ("status", "Status", 100), ("driver", "Driver", 120), ("date", "Created", 130),
        ])
        for status, color in STATUS_COLORS.items():
            self.ship_tree.tag_configure(status, background=color)
        self.ship_tree.bind("<Double-1>", lambda e: self.update_status())

    def refresh_shipments(self):
        self.ship_tree.delete(*self.ship_tree.get_children())
        rows = self.db.shipments(self.search_var.get().strip(), self.filter_var.get())
        for r in rows:
            self.ship_tree.insert("", "end", iid=r["tracking_code"], tags=(r["status"],), values=(
                r["tracking_code"], r["customer"], f"{r['origin']} -> {r['destination']}",
                r["weight_kg"], f"{r['price']:.2f}", r["status"], r["driver"] or "-",
                r["created_at"]))
        self.say(f"{len(rows)} shipment(s) shown")

    def selected_code(self):
        selection = self.ship_tree.selection()
        if not selection:
            messagebox.showinfo("Select a shipment", "Please select a shipment first.")
            return None
        return selection[0]

    def add_shipment(self):
        dialog = FormDialog(self, "New shipment", [
            ("Customer", "customer", None), ("Origin city", "origin", None),
            ("Destination city", "destination", None), ("Weight (kg)", "weight", None)])
        if not dialog.result:
            return
        data = dialog.result
        try:
            weight = float(data["weight"].replace(",", "."))
            if weight <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid weight", "Weight must be a number greater than 0.")
            return
        if not (data["customer"] and data["origin"] and data["destination"]):
            messagebox.showerror("Missing data", "All fields are required.")
            return
        code = self.db.add_shipment(data["customer"], data["origin"], data["destination"], weight)
        self.refresh_all()
        self.say(f"Shipment {code} created")

    def update_status(self):
        code = self.selected_code()
        if not code:
            return
        dialog = FormDialog(self, f"Status of {code}", [("New status", "status", STATUSES)])
        if dialog.result:
            self.db.update_status(code, dialog.result["status"])
            self.refresh_all()
            self.say(f"{code} is now {dialog.result['status']}")

    def assign_driver(self):
        code = self.selected_code()
        if not code:
            return
        drivers = self.db.drivers()
        if not drivers:
            messagebox.showinfo("No drivers", "Add a driver in the Drivers tab first.")
            return
        choices = [f"{d['id']} - {d['name']} ({d['vehicle']})" for d in drivers]
        dialog = FormDialog(self, f"Driver for {code}", [("Driver", "driver", choices)])
        if dialog.result:
            driver_id = int(dialog.result["driver"].split(" - ")[0])
            self.db.assign_driver(code, driver_id)
            self.refresh_all()
            self.say(f"Driver assigned to {code}")

    def delete_shipment(self):
        code = self.selected_code()
        if code and messagebox.askyesno("Delete", f"Delete shipment {code}?"):
            self.db.delete_shipment(code)
            self.refresh_all()
            self.say(f"{code} deleted")

    def export_csv(self):
        rows = self.db.shipments(self.search_var.get().strip(), self.filter_var.get())
        if not rows:
            messagebox.showinfo("Export", "Nothing to export.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", initialfile="shipments_export.csv",
            filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        fields = ["tracking_code", "customer", "origin", "destination",
                  "weight_kg", "price", "status", "driver", "created_at"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r[k] for k in fields})
        self.say(f"Exported {len(rows)} shipments to {path}")

    # ---------- Drivers tab ----------
    def build_drivers_tab(self):
        tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(tab, text="  Drivers  ")

        top = ttk.Frame(tab)
        top.pack(fill="x", pady=(0, 8))
        ttk.Button(top, text="+ New Driver", style="Accent.TButton",
                   command=self.add_driver).pack(side="left")
        ttk.Button(top, text="Delete", command=self.delete_driver).pack(side="left", padx=8)

        self.driver_tree = self.make_tree(tab, [
            ("id", "ID", 50), ("name", "Name", 200),
            ("phone", "Phone", 160), ("vehicle", "Vehicle", 160)])

    def refresh_drivers(self):
        self.driver_tree.delete(*self.driver_tree.get_children())
        for d in self.db.drivers():
            self.driver_tree.insert("", "end", iid=str(d["id"]),
                                    values=(d["id"], d["name"], d["phone"], d["vehicle"]))

    def add_driver(self):
        dialog = FormDialog(self, "New driver", [
            ("Name", "name", None), ("Phone", "phone", None),
            ("Vehicle", "vehicle", ["Van", "Truck", "Motorbike", "Car"])])
        if not dialog.result:
            return
        d = dialog.result
        if not (d["name"] and d["phone"]):
            messagebox.showerror("Missing data", "Name and phone are required.")
            return
        self.db.add_driver(d["name"], d["phone"], d["vehicle"])
        self.refresh_all()
        self.say(f"Driver {d['name']} added")

    def delete_driver(self):
        selection = self.driver_tree.selection()
        if not selection:
            messagebox.showinfo("Select a driver", "Please select a driver first.")
            return
        if messagebox.askyesno("Delete", "Delete this driver? Their shipments become unassigned."):
            self.db.delete_driver(int(selection[0]))
            self.refresh_all()

    # ---------- Dashboard tab ----------
    def build_dashboard_tab(self):
        tab = ttk.Frame(self.tabs, padding=14)
        self.tabs.add(tab, text="  Dashboard  ")

        cards = ttk.Frame(tab)
        cards.pack(fill="x")
        self.card_labels = {}
        for i, (key, title) in enumerate([
            ("total", "Total shipments"), ("revenue", "Revenue"), ("Pending", "Pending"),
            ("In Transit", "In transit"), ("Delivered", "Delivered")]):
            cards.columnconfigure(i, weight=1)
            card = tk.Frame(cards, bg="white", highlightbackground="#d1d5db", highlightthickness=1)
            card.grid(row=0, column=i, padx=6, sticky="nsew")
            tk.Label(card, text=title, bg="white", fg="#6b7280",
                     font=("Segoe UI", 10)).pack(pady=(12, 0))
            value = tk.Label(card, text="0", bg="white", fg=ACCENT,
                             font=("Segoe UI", 22, "bold"))
            value.pack(pady=(0, 12))
            self.card_labels[key] = value

        ttk.Label(tab, text="Shipments per driver",
                  font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(20, 6))
        self.stats_tree = self.make_tree(tab, [
            ("name", "Driver", 220), ("vehicle", "Vehicle", 160), ("total", "Shipments", 100)])

    def refresh_dashboard(self):
        total, revenue, per_status, per_driver = self.db.stats()
        self.card_labels["total"].config(text=str(total))
        self.card_labels["revenue"].config(text=f"{revenue:,.2f}")
        for status in STATUSES:
            self.card_labels[status].config(text=str(per_status[status]))
        self.stats_tree.delete(*self.stats_tree.get_children())
        for r in per_driver:
            self.stats_tree.insert("", "end", values=(r["name"], r["vehicle"], r["total"]))

    def refresh_all(self):
        self.refresh_shipments()
        self.refresh_drivers()
        self.refresh_dashboard()


if __name__ == "__main__":
    App().mainloop()
