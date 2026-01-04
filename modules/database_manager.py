import sqlite3
import pandas as pd
import random
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_name="komatsu_aftermarket.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS parts (
                        part_number TEXT PRIMARY KEY,
                        description TEXT,
                        unit TEXT,
                        stock_on_hand INTEGER,
                        item_type TEXT,
                        cost_price REAL
                    )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS inquiries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        customer_name TEXT, 
                        part_number TEXT,
                        qty INTEGER,
                        status TEXT,
                        revision_count INTEGER DEFAULT 0,
                        po_number TEXT,
                        FOREIGN KEY(part_number) REFERENCES parts(part_number)
                    )''')

        c.execute('''CREATE TABLE IF NOT EXISTS quotations (
                        quote_id TEXT PRIMARY KEY,
                        inquiry_id INTEGER,
                        customer_name TEXT,
                        part_number TEXT,
                        sales_price REAL,
                        profit_percentage REAL,
                        cost_price REAL,
                        sdc REAL,
                        svc REAL,
                        moq INTEGER,
                        leadtime INTEGER,
                        status TEXT,
                        FOREIGN KEY(inquiry_id) REFERENCES inquiries(id)
                    )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS localization_projects (
                        project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        inquiry_id INTEGER,
                        part_number TEXT,
                        supplier_name TEXT,
                        start_date TEXT,
                        target_finish_date TEXT,
                        development_status TEXT,
                        notes TEXT,
                        FOREIGN KEY(inquiry_id) REFERENCES inquiries(id)
                    )''')
        self.conn.commit()

    def populate_dummy_data(self):
        """Mengisi data parts 200 baris"""
        c = self.conn.cursor()
        c.execute("SELECT count(*) FROM parts")
        if c.fetchone()[0] == 0:
            # 1. Data Wajib (Specific Items)
            specific_items = [
                ("101-22-3331", "Bolt", "PCS", 100, "Local", 5.5),
                ("202-44-5552", "Pin", "PCS", 50, "Local", 12.0),
                ("303-66-7773", "Hose", "MTR", 200, "Import", 45.0),
                ("708-2L-00300", "Hydraulic Pump", "ASSY", 5, "Import", 2500.0)
            ]
            for item in specific_items:
                c.execute("INSERT OR IGNORE INTO parts VALUES (?, ?, ?, ?, ?, ?)", item)

            # 2. Generator 200 Data Random
            part_prefixes = ['600', '14X', '708', '070', '20Y', '421', '040', '099']
            descriptions = [
                'Hydraulic Filter', 'O-Ring Seal', 'Piston Pump', 'Fuel Injector', 
                'Bushing bucket', 'Track Shoe', 'Idler Assy', 'Radiator', 'Alternator',
                'Starter Motor', 'Turbocharger', 'Water Pump', 'Oil Cooler', 'Gasket Kit',
                'Solenoid Valve', 'Bearing', 'Cylinder Head', 'Cutting Edge'
            ]
            
            for _ in range(200):
                p_num = f"{random.choice(part_prefixes)}-{random.randint(100,999)}-{random.randint(1000,9999)}"
                desc = random.choice(descriptions)
                unit = random.choice(["PCS", "SET", "KIT", "ASSY"])
                cost = round(random.uniform(10.0, 800.0), 2)
                item_type = random.choice(["Local", "Import"])
                stock = random.randint(0, 150)
                
                try:
                    c.execute("INSERT INTO parts VALUES (?, ?, ?, ?, ?, ?)",
                              (p_num, desc, unit, stock, item_type, cost))
                except sqlite3.IntegrityError:
                    pass 
            self.conn.commit()

    # --- Methods ---
    def get_all_parts(self):
        return pd.read_sql("SELECT * FROM parts", self.conn)

    def add_part(self, p_num, desc, unit, stock, p_type, cost):
        c = self.conn.cursor()
        try:
            c.execute("INSERT INTO parts VALUES (?, ?, ?, ?, ?, ?)", 
                     (p_num, desc, unit, stock, p_type, cost))
            self.conn.commit()
            return True, "Success"
        except sqlite3.IntegrityError:
            return False, "Part Number already exists"

    def add_inquiry(self, cust_name, part_no, qty, status):
        c = self.conn.cursor()
        date_now = datetime.now().strftime("%Y-%m-%d")
        c.execute("INSERT INTO inquiries (date, customer_name, part_number, qty, status) VALUES (?, ?, ?, ?, ?)",
                  (date_now, cust_name, part_no, qty, status))
        self.conn.commit()

    def get_inquiries_by_status(self, status_list):
        placeholders = ','.join('?' for _ in status_list)
        query = f"SELECT * FROM inquiries WHERE status IN ({placeholders})"
        return pd.read_sql(query, self.conn, params=status_list)
    
    def get_inquiries_by_customer(self, customer_name):
        return pd.read_sql("SELECT * FROM inquiries WHERE customer_name = ?", self.conn, params=(customer_name,))
    
    def cancel_inquiry(self, inquiry_id):
        c = self.conn.cursor()
        c.execute("UPDATE inquiries SET status = 'Cancelled' WHERE id = ?", (inquiry_id,))
        self.conn.commit()

    def create_po(self, inquiry_id, po_number):
        c = self.conn.cursor()
        c.execute("UPDATE inquiries SET status = 'PO Created', po_number = ? WHERE id = ?", (po_number, inquiry_id,))
        self.conn.commit()

    def get_part_details(self, part_number):
        return pd.read_sql(f"SELECT * FROM parts WHERE part_number='{part_number}'", self.conn).iloc[0]

    def update_inquiry_status(self, inquiry_id, new_status, increment_revision=False):
        c = self.conn.cursor()
        c.execute("UPDATE inquiries SET status = ? WHERE id = ?", (new_status, inquiry_id))
        if increment_revision:
            c.execute("UPDATE inquiries SET revision_count = revision_count + 1 WHERE id = ?", (inquiry_id,))
        self.conn.commit()

    # --- Localization Methods ---
    def start_localization(self, inquiry_id, part_number, supplier, target_date, notes):
        c = self.conn.cursor()
        date_now = datetime.now().strftime("%Y-%m-%d")
        c.execute("""INSERT INTO localization_projects 
                     (inquiry_id, part_number, supplier_name, start_date, target_finish_date, development_status, notes) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (inquiry_id, part_number, supplier, date_now, target_date, "On Progress", notes))
        self.conn.commit()

    def get_localization_projects(self):
        return pd.read_sql("SELECT * FROM localization_projects WHERE development_status = 'On Progress'", self.conn)

    def finish_localization(self, project_id, inquiry_id):
        c = self.conn.cursor()
        c.execute("UPDATE localization_projects SET development_status = 'Finished' WHERE project_id = ?", (project_id,))
        c.execute("UPDATE inquiries SET status = 'Ready for Costing' WHERE id = ?", (inquiry_id,))
        self.conn.commit()

    # --- Quotation Methods ---
    def create_quotation(self, data):
        c = self.conn.cursor()
        c.execute("""INSERT INTO quotations 
                     (quote_id, inquiry_id, customer_name, part_number, sales_price, profit_percentage, cost_price, sdc, svc, moq, leadtime, status) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (data['quote_id'], data['inquiry_id'], data['customer'], data['part_number'], 
                   data['sales_price'], data['profit'], data['cost'], data['sdc'], data['svc'], 
                   data['moq'], data['leadtime'], data['status']))
        self.conn.commit()

    def get_quotations_by_status(self, status):
        return pd.read_sql("SELECT * FROM quotations WHERE status = ?", self.conn, params=(status,))
    
    def get_approved_with_po_check(self):
        query = """
        SELECT q.*, i.po_number, i.status as inquiry_status 
        FROM quotations q
        JOIN inquiries i ON q.inquiry_id = i.id
        WHERE q.status = 'Approved'
        """
        return pd.read_sql(query, self.conn)
    
    def get_full_results(self):
        return pd.read_sql("SELECT * FROM quotations WHERE status = 'Approved'", self.conn)

    def update_quotation_status(self, quote_id, status):
        c = self.conn.cursor()
        c.execute("UPDATE quotations SET status = ? WHERE quote_id = ?", (status, quote_id))
        self.conn.commit()