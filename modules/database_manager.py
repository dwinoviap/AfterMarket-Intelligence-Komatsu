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
        # Tabel Parts Master
        c.execute('''CREATE TABLE IF NOT EXISTS parts (
                        part_number TEXT PRIMARY KEY,
                        description TEXT,
                        unit TEXT,
                        stock_on_hand INTEGER,
                        item_type TEXT,
                        cost_price REAL
                    )''')
        
        # Tabel Inquiries (Updated with Customer Name)
        c.execute('''CREATE TABLE IF NOT EXISTS inquiries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT,
                        customer_name TEXT, 
                        part_number TEXT,
                        qty INTEGER,
                        status TEXT,
                        revision_count INTEGER DEFAULT 0,
                        FOREIGN KEY(part_number) REFERENCES parts(part_number)
                    )''')

        # Tabel Quotations
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
        self.conn.commit()

    def populate_dummy_data(self):
        """Mengisi data parts termasuk permintaan khusus (Bolt, Pin, Hose)"""
        c = self.conn.cursor()
        c.execute("SELECT count(*) FROM parts")
        if c.fetchone()[0] == 0:
            # Data Wajib
            specific_items = [
                ("101-22-3331", "Bolt", "PCS", 100, "Local", 5.5),
                ("202-44-5552", "Pin", "PCS", 50, "Local", 12.0),
                ("303-66-7773", "Hose", "MTR", 200, "Import", 45.0)
            ]
            
            # Data Random Tambahan
            part_prefixes = ['600', '14X', '708', '070', '20Y']
            descriptions = ['Hydraulic Filter', 'O-Ring Seal', 'Piston Pump', 'Fuel Injector', 'Bushing bucket']
            
            # Insert Specific Items
            for item in specific_items:
                c.execute("INSERT OR IGNORE INTO parts VALUES (?, ?, ?, ?, ?, ?)", item)

            # Insert Random Items
            for _ in range(15):
                p_num = f"{random.choice(part_prefixes)}-{random.randint(100,999)}-{random.randint(1000,9999)}"
                desc = random.choice(descriptions)
                cost = round(random.uniform(20.0, 500.0), 2)
                item_type = random.choice(["Local", "Import"])
                try:
                    c.execute("INSERT INTO parts VALUES (?, ?, ?, ?, ?, ?)",
                              (p_num, desc, "PCS", random.randint(0, 100), item_type, cost))
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
    
    def get_part_details(self, part_number):
        return pd.read_sql(f"SELECT * FROM parts WHERE part_number='{part_number}'", self.conn).iloc[0]

    def update_inquiry_status(self, inquiry_id, new_status, increment_revision=False):
        c = self.conn.cursor()
        c.execute("UPDATE inquiries SET status = ? WHERE id = ?", (new_status, inquiry_id))
        if increment_revision:
            c.execute("UPDATE inquiries SET revision_count = revision_count + 1 WHERE id = ?", (inquiry_id,))
        self.conn.commit()

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
    
    def get_full_results(self):
        # Join Inquiry and Quotation for Dashboard/Result
        return pd.read_sql("SELECT * FROM quotations WHERE status = 'Approved'", self.conn)

    def update_quotation_status(self, quote_id, status):
        c = self.conn.cursor()
        c.execute("UPDATE quotations SET status = ? WHERE quote_id = ?", (status, quote_id))
        self.conn.commit()