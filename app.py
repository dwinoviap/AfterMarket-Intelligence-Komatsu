import streamlit as st
import pandas as pd
import random
import time
from modules.database_manager import DatabaseManager
from modules.ai_predictor import ProcurementAI
from modules.email_service import send_quotation_email_simulation

# ================= INIT SYSTEM =================
st.set_page_config(page_title="AMI - Komatsu", layout="wide", page_icon="🚜")

if 'db' not in st.session_state:
    st.session_state.db = DatabaseManager()
    st.session_state.db.populate_dummy_data()

if 'ai' not in st.session_state:
    st.session_state.ai = ProcurementAI()

db = st.session_state.db
ai = st.session_state.ai

# List Customer Sesuai Requirement
CUSTOMER_LIST = ['KMSI', 'KCIC', 'KPAC', 'KMM', 'KME', 'KEPO', 'KAC', 'KMSA', 'KSAF', 'KLTD']

# ================= HELPER FUNC =================
def calculate_financials(cost_price, target_profit_percent=10.0):
    """
    Menghitung SDC, SVC, Sales Price, Op Profit (Value)
    Default profit 10% untuk display di Master Data
    """
    sdc = cost_price * 0.03
    svc = cost_price + sdc
    
    profit_decimal = target_profit_percent / 100
    # Formula: SVC / (1 - 3.8% - Profit% - 3%)
    denominator = 1 - 0.038 - profit_decimal - 0.03
    
    if denominator <= 0: sales_price = 0
    else: sales_price = svc / denominator
    
    op_profit_val = sales_price * profit_decimal
    
    return {
        "SDC": round(sdc, 2),
        "SVC": round(svc, 2),
        "Sales Price": round(sales_price, 2),
        "Op Profit Val": round(op_profit_val, 2)
    }

# ================= UI SIDEBAR =================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Komatsu_logo.svg/2560px-Komatsu_logo.svg.png", width=200)
st.sidebar.markdown("---")

menu = st.sidebar.radio("Navigation", 
    ["Dashboard", "Master Data Parts", "Customer Portal (Input)", "1. Inquiry Validation", "2. Cost & Procurement", "3. Superior Approval", "4. Result & Email"])

# ================= MENU 1: DASHBOARD =================
if menu == "Dashboard":
    st.title("📊 Executive Dashboard")
    
    # Summary Metrics
    all_quotes = db.get_full_results()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Completed Inquiries", len(all_quotes))
    col2.metric("Total Sales Potential", f"${all_quotes['sales_price'].sum():,.2f}" if not all_quotes.empty else "$0")
    col3.metric("Avg. Profit Margin", f"{all_quotes['profit_percentage'].mean():.1f}%" if not all_quotes.empty else "0%")

    st.markdown("---")
    
    # Charts Area
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Sales by Customer")
        if not all_quotes.empty:
            chart_data = all_quotes.groupby("customer_name")["sales_price"].sum()
            st.bar_chart(chart_data)
        else:
            st.info("No data available.")
            
    with c2:
        st.subheader("Process Status")
        # Hitung status dari tabel Inquiries
        inq_data = db.get_inquiries_by_status(["Pending Validation", "Ready for Costing", "Need Feasibility Check", "Waiting Approval", "Finished"])
        if not inq_data.empty:
            status_counts = inq_data['status'].value_counts()
            st.bar_chart(status_counts, color="#FF4B4B")
        else:
            st.info("No transaction data.")

    st.subheader("Finished Transaction History")
    if not all_quotes.empty:
        st.dataframe(all_quotes[['quote_id', 'customer_name', 'part_number', 'sales_price', 'status', 'leadtime']])

# ================= MENU: MASTER DATA =================
elif menu == "Master Data Parts":
    st.title("🛠️ Master Data Parts")
    
    tab1, tab2 = st.tabs(["View Master Data", "Add New Part"])
    
    with tab1:
        st.write("Daftar lengkap Parts dengan kalkulasi standar (Profit 10%).")
        df_parts = db.get_all_parts()
        
        # Tambahkan Kolom Kalkulasi (SDC, SVC, Sales Price, Op Profit) on the fly
        if not df_parts.empty:
            calc_data = df_parts['cost_price'].apply(lambda x: pd.Series(calculate_financials(x)))
            df_display = pd.concat([df_parts, calc_data], axis=1)
            st.dataframe(df_display, use_container_width=True)
        else:
            st.warning("Database Kosong.")

    with tab2:
        st.subheader("Input New Item")
        with st.form("add_part_form"):
            c1, c2 = st.columns(2)
            new_pn = c1.text_input("Part Number")
            new_desc = c2.text_input("Description")
            new_unit = c1.selectbox("Unit", ["PCS", "SET", "KIT", "MTR"])
            new_type = c2.selectbox("Item Type", ["Local", "Import"])
            new_stock = c1.number_input("Initial Stock", min_value=0)
            new_cost = c2.number_input("Cost Price ($)", min_value=0.0, format="%.2f")
            
            if st.form_submit_button("Save to Master"):
                success, msg = db.add_part(new_pn, new_desc, new_unit, new_stock, new_type, new_cost)
                if success:
                    st.success(f"Part {new_pn} berhasil ditambahkan!")
                    st.rerun()
                else:
                    st.error(msg)

# ================= MENU: CUSTOMER PORTAL =================
elif menu == "Customer Portal (Input)":
    st.title("🌏 Customer Inquiry Portal")
    st.caption("Halaman ini diakses oleh Customer/Dealer")
    
    with st.container(border=True):
        st.subheader("Submit Your Inquiry")
        parts_list = db.get_all_parts()['part_number'].tolist()
        
        with st.form("cust_form"):
            col_a, col_b = st.columns(2)
            cust_name = col_a.selectbox("Select Customer Entity", CUSTOMER_LIST)
            part_select = col_b.selectbox("Select Part Number", parts_list)
            qty_req = col_a.number_input("Quantity Required", min_value=1)
            
            submit_inq = st.form_submit_button("Send Inquiry Request")
            
            if submit_inq:
                # Status awal masuk ke "Pending Validation"
                db.add_inquiry(cust_name, part_select, qty_req, "Pending Validation")
                st.success(f"Permintaan Inquiry untuk {part_select} telah dikirim ke Tim Komatsu!")

# ================= MENU 1: INQUIRY VALIDATION (INTERNAL) =================
elif menu == "1. Inquiry Validation":
    st.title("📋 Inquiry Validation Process")
    st.caption("Tim AfterMarket memvalidasi inquiry yang masuk dari Customer.")
    
    pending_items = db.get_inquiries_by_status(["Pending Validation"])
    
    if pending_items.empty:
        st.info("No new inquiries from customers.")
    else:
        for idx, row in pending_items.iterrows():
            with st.expander(f"Req from {row['customer_name']} - {row['part_number']} (Qty: {row['qty']})", expanded=True):
                # Ambil detail part untuk cek Local/Import
                part_detail = db.get_part_details(row['part_number'])
                st.write(f"**Description:** {part_detail['description']} | **Type:** {part_detail['item_type']} | **Stock:** {part_detail['stock_on_hand']}")
                
                c1, c2 = st.columns(2)
                
                # Logic Validasi
                if part_detail['item_type'] == "Local":
                    st.info("✅ Item Local. Bisa langsung proses costing.")
                    if c1.button("Validate & Process", key=f"val_{row['id']}"):
                        db.update_inquiry_status(row['id'], "Ready for Costing")
                        st.rerun()
                else:
                    st.warning("⚠️ Item Import. Butuh pengecekan lokalisasi (Development).")
                    col_act1, col_act2 = st.columns(2)
                    if col_act1.button("Needs Development (Localize)", key=f"dev_{row['id']}"):
                        db.update_inquiry_status(row['id'], "Ready for Costing") # Anggap development disetujui
                        st.success("Masuk ke tahap Study Development -> Costing")
                        time.sleep(1)
                        st.rerun()
                    if col_act2.button("Reject / Still Import", key=f"rej_{row['id']}"):
                        db.update_inquiry_status(row['id'], "Cancelled")
                        st.error("Inquiry ditolak / tetap import murni.")
                        st.rerun()

# ================= MENU 2: COSTING =================
elif menu == "2. Cost & Procurement":
    st.title("💰 Cost Control & Procurement")
    
    tasks = db.get_inquiries_by_status(["Ready for Costing", "Revise Required"])
    
    if tasks.empty:
        st.info("No tasks available.")
    else:
        # Pilihan Task
        task_opts = {f"ID {r['id']} - {r['customer_name']} - {r['part_number']}": r['id'] for i, r in tasks.iterrows()}
        selected_label = st.selectbox("Select Inquiry Task", list(task_opts.keys()))
        sel_id = task_opts[selected_label]
        
        inquiry = tasks[tasks['id'] == sel_id].iloc[0]
        part = db.get_part_details(inquiry['part_number'])
        
        st.markdown(f"**Customer:** {inquiry['customer_name']} | **Part:** {inquiry['part_number']}")
        
        with st.form("costing_procurement_form"):
            c1, c2 = st.columns(2)
            
            # Costing Section
            c1.markdown("### Financial Calculation")
            cost_input = c1.number_input("Supplier Cost ($)", value=part['cost_price'])
            profit_input = c1.slider("Profit Margin (%)", 5.0, 50.0, 10.0)
            
            fin = calculate_financials(cost_input, profit_input)
            
            c1.info(f"""
            **Calculation Result:**
            - SDC: ${fin['SDC']}
            - SVC: ${fin['SVC']}
            - Sales Price: ${fin['Sales Price']}
            """)
            
            # Procurement Section
            c2.markdown("### Procurement Setup")
            if c2.form_submit_button("🤖 Ask AI Prediction"):
                moq, lt = ai.predict(cost_input, part['item_type'], part['stock_on_hand'])
                st.session_state['ai_res'] = (moq, lt)
                st.toast("AI Suggested MOQ & Leadtime updated!")
            
            ai_vals = st.session_state.get('ai_res', (50, 30))
            moq_input = c2.number_input("MOQ (Pcs)", value=ai_vals[0])
            lt_input = c2.number_input("Leadtime (Days)", value=ai_vals[1])
            
            st.divider()
            
            if st.form_submit_button("Submit to Superior Approval"):
                # Simpan Quotation Draft
                q_data = {
                    "quote_id": f"Q-{random.randint(10000,99999)}",
                    "inquiry_id": int(sel_id),
                    "customer": inquiry['customer_name'],
                    "part_number": inquiry['part_number'],
                    "sales_price": fin['Sales Price'],
                    "profit": profit_input,
                    "cost": cost_input,
                    "sdc": fin['SDC'],
                    "svc": fin['SVC'],
                    "moq": moq_input,
                    "leadtime": lt_input,
                    "status": "Draft"
                }
                db.create_quotation(q_data)
                db.update_inquiry_status(sel_id, "Waiting Approval")
                st.success("Draft sent to Superior!")
                st.rerun()

# ================= MENU 3: SUPERIOR APPROVAL =================
elif menu == "3. Superior Approval":
    st.title("✅ Superior Approval")
    
    drafts = db.get_quotations_by_status("Draft")
    
    if drafts.empty:
        st.info("No documents waiting for approval.")
    else:
        for i, row in drafts.iterrows():
            with st.expander(f"Quote {row['quote_id']} - {row['customer_name']}", expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Sales Price", f"${row['sales_price']}")
                c2.metric("Profit", f"{row['profit_percentage']}%")
                c3.metric("Leadtime", f"{row['leadtime']} Days")
                
                b1, b2 = st.columns(2)
                if b1.button("Approve", key=f"app_{row['quote_id']}"):
                    db.update_quotation_status(row['quote_id'], "Approved")
                    db.update_inquiry_status(row['inquiry_id'], "Finished")
                    st.success("Quotation Approved! Check 'Result' menu.")
                    st.rerun()
                    
                if b2.button("Reject (Revise)", key=f"rej_{row['quote_id']}"):
                    db.update_quotation_status(row['quote_id'], "Rejected")
                    db.update_inquiry_status(row['inquiry_id'], "Revise Required", increment_revision=True)
                    st.error("Returned to Cost Control.")
                    st.rerun()

# ================= MENU 4: RESULT & EMAIL =================
elif menu == "4. Result & Email":
    st.title("📧 Result & Customer Notification")
    
    approved_quotes = db.get_full_results()
    
    if approved_quotes.empty:
        st.info("Belum ada Quotation yang Approved.")
    else:
        st.subheader("Approved Quotations Data")
        # Display tabel dengan kolom lengkap sesuai request
        display_cols = ['quote_id', 'customer_name', 'part_number', 'cost_price', 'sdc', 'svc', 'sales_price', 'profit_percentage', 'status']
        st.dataframe(approved_quotes[display_cols])
        
        st.divider()
        st.subheader("Send Email to Customer")
        
        # Select Quote to send
        quote_opts = approved_quotes['quote_id'].tolist()
        selected_quote_id = st.selectbox("Select Quotation to Email", quote_opts)
        
        if selected_quote_id:
            q_data = approved_quotes[approved_quotes['quote_id'] == selected_quote_id].iloc[0]
            
            # Template Email Preview
            email_body = f"""
            To: Purchasing Dept - {q_data['customer_name']}
            Subject: Quotation Offer {q_data['quote_id']} - {q_data['part_number']}
            
            Dear Customer,
            
            Based on your inquiry, we are pleased to offer:
            
            Item        : {q_data['part_number']}
            Price       : ${q_data['sales_price']} / pcs
            MOQ         : {q_data['moq']} pcs
            Leadtime    : {q_data['leadtime']} Days
            
            Please send PO if you agree.
            
            Regards,
            Komatsu After Market
            """
            
            st.text_area("Email Preview", email_body, height=250)
            
            if st.button("🚀 Send Email Now"):
                # Simulasi kirim
                success, msg = send_quotation_email_simulation(q_data['customer_name'], q_data['quote_id'], "OFFER")
                st.success(f"Email sent to {q_data['customer_name']}! System Log: {msg}")