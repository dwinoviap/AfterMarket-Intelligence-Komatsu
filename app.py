import streamlit as st
import pandas as pd
import random
import time
from datetime import date
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

CUSTOMER_LIST = ['KMSI', 'KCIC', 'KPAC', 'KMM', 'KME', 'KEPO', 'KAC', 'KMSA', 'KSAF', 'KLTD']
SUPPLIER_LIST = ['PT. United Tractors Pandu Eng', 'PT. Astra Otoparts', 'PT. Komatsu Undercarriage', 'Local Workshop A', 'Local Workshop B']

# ================= HELPER FUNC =================
def calculate_financials(cost_price, target_profit_percent=10.0):
    sdc = cost_price * 0.03
    svc = cost_price + sdc
    profit_decimal = target_profit_percent / 100
    denominator = 1 - 0.038 - profit_decimal - 0.03
    if denominator <= 0: sales_price = 0
    else: sales_price = svc / denominator
    op_profit_val = sales_price * profit_decimal
    return {"SDC": round(sdc, 2), "SVC": round(svc, 2), "Sales Price": round(sales_price, 2), "Op Profit Val": round(op_profit_val, 2)}

# ================= UI SIDEBAR =================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Komatsu_logo.svg/2560px-Komatsu_logo.svg.png", width=200)
st.sidebar.markdown("### Navigation Menu")

menu = st.sidebar.radio("", 
    ["🏠 Home", "📊 Dashboard", "🛠️ Master Data Parts", "🌏 Customer Inquiry Portal", 
     "1. Inquiry Validation", "⚙️ Localization Development", "2. Cost & Procurement", 
     "3. Superior Approval", "4. Result & Email"])

st.sidebar.markdown("---")
st.sidebar.caption("© 2026 PT Komatsu Indonesia - AfterMarket Division")

# ================= MENU: HOME =================
if menu == "🏠 Home":
    st.markdown("""
    <style>
    .hero-title { font-size: 3em; font-weight: bold; color: #1a237e; text-align: center; margin-bottom: 0px; }
    .hero-subtitle { font-size: 1.5em; color: #555; text-align: center; margin-bottom: 30px; }
    .icon-caption { font-size: 1.2em; font-weight: 600; color: #333; text-align: center; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<p class="hero-title">Welcome to AfterMarket Intelligence</p>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">Integrated System for Parts Localization, Costing & Procurement</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.image("https://img.icons8.com/fluency/240/excavator.png", width=200)
        st.markdown('<p class="icon-caption">Parts Supply</p>', unsafe_allow_html=True)
        st.caption("Manage Local & Import Parts Availability efficiently.")
    with col2:
        st.image("https://img.icons8.com/fluency/240/dump-truck.png", width=200)
        st.markdown('<p class="icon-caption">Mining Support</p>', unsafe_allow_html=True)
        st.caption("Support for HD785, PC2000, and other heavy equipments.")
    with col3:
        st.image("https://img.icons8.com/fluency/240/maintenance.png", width=200)
        st.markdown('<p class="icon-caption">Localization Dev</p>', unsafe_allow_html=True)
        st.caption("Integrated workflow for Parts Localization Development.")
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.info("📡 System: **Online**")
    c2.success("💾 Database: **Connected**")
    c3.warning("🤖 AI Engine: **Ready**")

# ================= MENU: DASHBOARD =================
elif menu == "📊 Dashboard":
    st.title("📊 Executive Dashboard")
    all_quotes = db.get_full_results()
    col1, col2, col3 = st.columns(3)
    total_completed = len(all_quotes)
    total_sales = f"${all_quotes['sales_price'].sum():,.2f}" if not all_quotes.empty else "$0"
    avg_profit = f"{all_quotes['profit_percentage'].mean():.1f}%" if not all_quotes.empty else "0%"
    col1.metric("Total Completed Inquiries", total_completed)
    col2.metric("Total Sales Potential", total_sales)
    col3.metric("Avg. Profit Margin", avg_profit)
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Inquiry by Customer")
        if not all_quotes.empty:
            chart_data = all_quotes.groupby("customer_name")["sales_price"].sum()
            st.bar_chart(chart_data, color="#2962FF") 
        else:
            st.info("No sales data available.")
    with c2:
        st.subheader("Process Status")
        inq_data = db.get_inquiries_by_status(["Pending Validation", "Ready for Costing", "Need Feasibility Check", "Waiting Approval", "Finished", "Needs Localization", "In Development"])
        if not inq_data.empty:
            status_counts = inq_data['status'].value_counts()
            st.bar_chart(status_counts, color="#FF4B4B") 
        else:
            st.info("No transaction data.")
    st.subheader("Finished Transaction History")
    if not all_quotes.empty:
        display_df = all_quotes[['quote_id', 'customer_name', 'part_number', 'sales_price', 'status', 'leadtime']]
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No finished transactions yet.")

# ================= MENU: MASTER DATA PARTS =================
elif menu == "🛠️ Master Data Parts":
    st.title("🛠️ Master Data Parts")
    tab1, tab2, tab3 = st.tabs(["View Master Data", "Add New Part", "🌏 Sales Price Comparison"])
    
    with tab1:
        st.write("Daftar lengkap Parts dengan kalkulasi standar (Profit 10%).")
        df_parts = db.get_all_parts()
        if not df_parts.empty:
            calc_data = df_parts['cost_price'].apply(lambda x: pd.Series(calculate_financials(x)))
            # Drop kolom harga region agar tidak penuh, fokus di tab comparison
            cols_to_drop = ['price_bkc', 'price_prpd', 'price_kipl', 'price_ksc', 'price_kac']
            df_parts_clean = df_parts.drop(columns=cols_to_drop, errors='ignore')
            df_display = pd.concat([df_parts_clean, calc_data], axis=1)
            st.dataframe(df_display, use_container_width=True)
        else:
            st.warning("Database Kosong.")

    with tab2:
        st.subheader("Input New Item")
        with st.form("add_part_form"):
            col_a, col_b = st.columns(2)
            new_pn = col_a.text_input("Part Number")
            new_desc = col_b.text_input("Description")
            new_unit = col_a.selectbox("Unit", ["PCS", "SET", "KIT", "MTR", "ASSY"])
            new_type = col_b.selectbox("Item Type", ["Local", "Import"])
            new_stock = col_a.number_input("Initial Stock", min_value=0)
            new_cost = col_b.number_input("Cost Price ($)", min_value=0.0, format="%.2f")
            st.markdown("---")
            if st.form_submit_button("Save to Master"):
                if new_pn and new_desc:
                    success, msg = db.add_part(new_pn, new_desc, new_unit, new_stock, new_type, new_cost)
                    if success:
                        st.success(f"Part {new_pn} berhasil ditambahkan!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Part Number & Description wajib diisi.")
    
    # --- FITUR BARU: SALES PRICE COMPARISON ---
    with tab3:
        st.subheader("Regional Sales Price Comparison")
        st.info("Komparasi harga 'KI' (Standard Profit 10%) dengan Region lain.")
        
        df_comp = db.get_all_parts()
        if not df_comp.empty:
            # Hitung harga KI standar (Profit 10%)
            df_comp['KI (Std)'] = df_comp['cost_price'].apply(lambda x: calculate_financials(x, 10.0)['Sales Price'])
            
            # Rename kolom supaya sesuai requirement
            rename_map = {
                'part_number': 'Part Number',
                'description': 'Description',
                'KI (Std)': 'KI',
                'price_bkc': 'BKC',
                'price_prpd': 'PRPD',
                'price_kipl': 'KIPL',
                'price_ksc': 'KSC',
                'price_kac': 'KAC'
            }
            cols_show = ['Part Number', 'Description', 'KI', 'BKC', 'PRPD', 'KIPL', 'KSC', 'KAC']
            
            df_show = df_comp.rename(columns=rename_map)[cols_show]
            
            # Styling: Highlight jika KI lebih murah (Green) atau Mahal (Red) dibanding rata-rata region
            def highlight_ki(row):
                avg_region = (row['BKC'] + row['PRPD'] + row['KIPL'] + row['KSC'] + row['KAC']) / 5
                if row['KI'] < avg_region:
                    return ['background-color: #d4edda']*len(row) # Greenish
                else:
                    return ['']*len(row)

            st.dataframe(df_show, use_container_width=True)
            st.caption("*KI Price calculated based on standard 10% Profit Formula.")
        else:
            st.warning("No data.")

# ================= MENU: CUSTOMER PORTAL =================
elif menu == "🌏 Customer Inquiry Portal":
    st.title("🌏 Customer Portal")
    selected_customer = st.selectbox("Login as Customer Entity:", CUSTOMER_LIST)
    st.divider()
    tab1, tab2, tab3 = st.tabs(["📝 Submit New Inquiry", "📋 My Inquiries (Cancel)", "🧾 Create PO"])
    with tab1:
        st.subheader(f"New Inquiry Request for {selected_customer}")
        parts_list = db.get_all_parts()['part_number'].tolist()
        with st.form("cust_form"):
            c1, c2 = st.columns(2)
            part_select = c1.selectbox("Select Part Number", parts_list)
            qty_req = c2.number_input("Quantity Required", min_value=1)
            if st.form_submit_button("Send Inquiry Request"):
                db.add_inquiry(selected_customer, part_select, qty_req, "Pending Validation")
                st.success(f"Inquiry sent for {part_select}!")
    with tab2:
        st.subheader("Active Inquiries")
        my_inquiries = db.get_inquiries_by_customer(selected_customer)
        active_inq = my_inquiries[~my_inquiries['status'].isin(['Cancelled', 'PO Created', 'Finished'])]
        if not active_inq.empty:
            for idx, row in active_inq.iterrows():
                with st.expander(f"Req #{row['id']}: {row['part_number']} - {row['status']}"):
                    st.write(f"Date: {row['date']} | Qty: {row['qty']}")
                    if st.button("❌ Cancel Request", key=f"cncl_{row['id']}"):
                        db.cancel_inquiry(row['id'])
                        st.rerun()
        else:
            st.info("No active inquiries found.")
    with tab3:
        st.subheader("Ready for Purchasing (Approved Quotations)")
        all_approved = db.get_approved_with_po_check()
        my_ready_quotes = all_approved[(all_approved['customer_name'] == selected_customer) & (all_approved['inquiry_status'] != 'PO Created')]
        if not my_ready_quotes.empty:
            st.dataframe(my_ready_quotes[['quote_id', 'part_number', 'sales_price', 'moq', 'leadtime']])
            with st.form("po_form"):
                q_id_select = st.selectbox("Select Quotation to Process", my_ready_quotes['quote_id'].tolist())
                po_num_input = st.text_input("Enter PO Number (e.g. PO-KMSI-001)")
                if st.form_submit_button("Submit Purchase Order"):
                    inq_id_val = my_ready_quotes[my_ready_quotes['quote_id'] == q_id_select]['inquiry_id'].values[0]
                    db.create_po(inq_id_val, po_num_input)
                    st.balloons()
                    st.success(f"PO {po_num_input} created successfully!")
                    time.sleep(2)
                    st.rerun()
        else:
            st.info("No approved quotations waiting for PO.")

# ================= MENU: INQUIRY VALIDATION =================
elif menu == "1. Inquiry Validation":
    st.title("📋 Inquiry Validation Process")
    pending_items = db.get_inquiries_by_status(["Pending Validation"])
    if pending_items.empty:
        st.info("No new inquiries to validate.")
    else:
        for idx, row in pending_items.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                part_detail = db.get_part_details(row['part_number'])
                c1.markdown(f"**{row['customer_name']}** requesting **{row['part_number']}** ({row['qty']} pcs)")
                c1.caption(f"Desc: {part_detail['description']} | Type: {part_detail['item_type']}")
                if part_detail['item_type'] == "Local":
                    if c2.button("✅ Validate Local", key=f"v_{row['id']}"):
                        db.update_inquiry_status(row['id'], "Ready for Costing")
                        st.rerun()
                else:
                    if c2.button("🛠️ Needs Localization", key=f"loc_{row['id']}"):
                        db.update_inquiry_status(row['id'], "Needs Localization")
                        st.success("Sent to Development Team.")
                        time.sleep(1)
                        st.rerun()
                    if c3.button("❌ Reject", key=f"r_{row['id']}"):
                        db.update_inquiry_status(row['id'], "Cancelled")
                        st.rerun()

# ================= MENU: LOCALIZATION DEVELOPMENT =================
elif menu == "⚙️ Localization Development":
    st.title("⚙️ Localization Project Management")
    tab_dev1, tab_dev2 = st.tabs(["New Projects", "On Progress"])
    with tab_dev1:
        needs_dev = db.get_inquiries_by_status(["Needs Localization"])
        if not needs_dev.empty:
            for i, row in needs_dev.iterrows():
                with st.form(f"dev_start_{row['id']}"):
                    st.write(f"**Project Setup:** {row['part_number']} ({row['customer_name']})")
                    c1, c2 = st.columns(2)
                    supplier_sel = c1.selectbox("Select Supplier / Workshop", SUPPLIER_LIST)
                    target_date = c2.date_input("Est. Completion Date")
                    notes = st.text_area("Development Notes")
                    if st.form_submit_button("Start Development Project"):
                        db.start_localization(row['id'], row['part_number'], supplier_sel, str(target_date), notes)
                        db.update_inquiry_status(row['id'], "In Development") 
                        st.success("Project Started! Check 'On Progress' tab.")
                        st.rerun()
        else:
            st.info("No new parts waiting for localization setup.")
    with tab_dev2:
        on_progress = db.get_localization_projects()
        if not on_progress.empty:
            for i, row in on_progress.iterrows():
                with st.expander(f"Project #{row['project_id']} - {row['part_number']} ({row['supplier_name']})"):
                    st.write(f"Target Date: {row['target_finish_date']}")
                    st.info(f"Notes: {row['notes']}")
                    if st.button("✅ Finish Development & Release to Costing", key=f"fin_{row['project_id']}"):
                        db.finish_localization(row['project_id'], row['inquiry_id'])
                        st.success("Development Finished. Data moved to Cost Control.")
                        time.sleep(1)
                        st.rerun()
        else:
            st.info("No active development projects.")

# ================= MENU: COST & PROCUREMENT =================
elif menu == "2. Cost & Procurement":
    st.title("💰 Cost Control & Procurement")
    tasks = db.get_inquiries_by_status(["Ready for Costing", "Revise Required"])
    
    if not tasks.empty:
        task_opts = {f"ID {r['id']} - {r['part_number']} ({r['customer_name']})": r['id'] for i, r in tasks.iterrows()}
        sel_label = st.selectbox("Select Task", list(task_opts.keys()))
        sel_id = task_opts[sel_label]
        inquiry = tasks[tasks['id'] == sel_id].iloc[0]
        part = db.get_part_details(inquiry['part_number'])
        
        if inquiry['revision_count'] > 0:
            st.warning(f"⚠️ REVISION REQUESTED (Rev: {inquiry['revision_count']})")
            
        with st.form("cost_form"):
            c1, c2 = st.columns(2)
            c1.markdown("### Costing")
            cost_in = c1.number_input("Cost Price ($)", value=part['cost_price'])
            profit_in = c1.slider("Profit (%)", 5.0, 50.0, 10.0)
            fin = calculate_financials(cost_in, profit_in)
            c1.info(f"SDC: ${fin['SDC']} | SVC: ${fin['SVC']} | **Sales Price: ${fin['Sales Price']}**")
            
            # --- FITUR BARU: REGIONAL BENCHMARK DI COSTING ---
            st.markdown("### 🌏 Regional Price Benchmark")
            comp_data = {
                'Region': ['KI (You)', 'BKC', 'PRPD', 'KIPL', 'KSC', 'KAC'],
                'Price': [fin['Sales Price'], part['price_bkc'], part['price_prpd'], part['price_kipl'], part['price_ksc'], part['price_kac']]
            }
            df_chart = pd.DataFrame(comp_data)
            st.bar_chart(df_chart.set_index('Region'), color="#2962FF")
            
            # Highlight jika harga KI terlalu tinggi
            avg_market = sum(comp_data['Price'][1:]) / 5
            if fin['Sales Price'] > avg_market:
                st.warning(f"⚠️ Warning: Your price (${fin['Sales Price']}) is higher than market average (${avg_market:.2f}). Consider lowering profit.")
            else:
                st.success(f"✅ Competitive: Your price is below market average (${avg_market:.2f}).")
            # ------------------------------------------------
            
            c2.markdown("### Procurement")
            if c2.form_submit_button("🤖 AI Predict"):
                moq, lt = ai.predict(cost_in, part['item_type'], part['stock_on_hand'])
                st.session_state['ai_res'] = (moq, lt)
            ai_vals = st.session_state.get('ai_res', (50, 30))
            moq_in = c2.number_input("MOQ", value=ai_vals[0])
            lt_in = c2.number_input("Leadtime (Days)", value=ai_vals[1])
            
            if st.form_submit_button("Submit to Superior"):
                q_data = {
                    "quote_id": f"Q-{random.randint(10000,99999)}",
                    "inquiry_id": int(sel_id),
                    "customer": inquiry['customer_name'],
                    "part_number": inquiry['part_number'],
                    "sales_price": fin['Sales Price'],
                    "profit": profit_in,
                    "cost": cost_in,
                    "sdc": fin['SDC'],
                    "svc": fin['SVC'],
                    "moq": moq_in,
                    "leadtime": lt_in,
                    "status": "Draft"
                }
                db.create_quotation(q_data)
                db.update_inquiry_status(sel_id, "Waiting Approval")
                st.success("Draft submitted.")
                st.rerun()
    else:
        st.info("No pending costing tasks.")

# ================= MENU: SUPERIOR APPROVAL =================
elif menu == "3. Superior Approval":
    st.title("✅ Superior Approval")
    drafts = db.get_quotations_by_status("Draft")
    
    if not drafts.empty:
        for i, row in drafts.iterrows():
            with st.expander(f"APPROVAL NEEDED: Quote {row['quote_id']} - {row['customer_name']}", expanded=True):
                col_d1, col_d2, col_d3 = st.columns(3)
                col_d1.markdown("#### Item Info")
                col_d1.write(f"Part: **{row['part_number']}**")
                col_d1.write(f"MOQ: {row['moq']} pcs")
                col_d1.write(f"Leadtime: {row['leadtime']} days")
                col_d2.markdown("#### Cost Structure")
                col_d2.write(f"Base Cost: ${row['cost_price']}")
                col_d2.write(f"SDC: ${row['sdc']}")
                col_d2.write(f"SVC: ${row['svc']}")
                col_d3.markdown("#### Pricing & Profit")
                col_d3.metric("Sales Price", f"${row['sales_price']}")
                col_d3.metric("Profit Margin", f"{row['profit_percentage']}%")
                
                # --- FITUR BARU: BENCHMARK DI APPROVAL ---
                st.divider()
                st.markdown("#### 🌏 Market Price Comparison")
                # Ambil data parts untuk compare
                part_master = db.get_part_details(row['part_number'])
                
                # Buat Dataframe compare simple
                bench_data = {
                    'Entity': ['KI (Proposed)', 'BKC', 'PRPD', 'KIPL', 'KSC', 'KAC'],
                    'Price ($)': [
                        row['sales_price'], 
                        part_master['price_bkc'], 
                        part_master['price_prpd'], 
                        part_master['price_kipl'], 
                        part_master['price_ksc'], 
                        part_master['price_kac']
                    ]
                }
                st.dataframe(pd.DataFrame(bench_data).T, use_container_width=True)
                # -----------------------------------------
                
                st.divider()
                b1, b2 = st.columns(2)
                if b1.button("✅ APPROVE", key=f"ap_{row['quote_id']}"):
                    db.update_quotation_status(row['quote_id'], "Approved")
                    db.update_inquiry_status(row['inquiry_id'], "Finished") 
                    st.success("Approved!")
                    st.rerun()
                if b2.button("❌ REVISE", key=f"rv_{row['quote_id']}"):
                    db.update_quotation_status(row['quote_id'], "Rejected")
                    db.update_inquiry_status(row['inquiry_id'], "Revise Required", increment_revision=True)
                    st.error("Sent back for revision.")
                    st.rerun()
    else:
        st.info("All clear. No documents to approve.")

# ================= MENU: RESULT & EMAIL =================
elif menu == "4. Result & Email":
    st.title("📧 Result & Customer Notification")
    approved = db.get_quotations_by_status("Approved")
    if not approved.empty:
        st.dataframe(approved[['quote_id', 'customer_name', 'part_number', 'sales_price', 'status']])
        st.subheader("Compose Email")
        q_sel = st.selectbox("Select Quote", approved['quote_id'].tolist())
        if q_sel:
            q_data = approved[approved['quote_id'] == q_sel].iloc[0]
            recipient_email = st.text_input("Customer Email Address", value="purchasing@customer.com")
            body = f"""
            Dear {q_data['customer_name']},
            We are pleased to submit our offer:
            Ref: {q_data['quote_id']}
            Part Number : {q_data['part_number']}
            Price       : ${q_data['sales_price']}
            MOQ         : {q_data['moq']}
            Leadtime    : {q_data['leadtime']} Days
            Please Create PO through the Customer Portal.
            Regards,
            Komatsu AMI
            """
            st.text_area("Preview", body, height=200)
            if st.button("Send Email"):
                success, msg = send_quotation_email_simulation(recipient_email, q_sel, "OFFER")
                st.success(f"Email sent to {recipient_email}!")
    else:
        st.info("No approved quotations available.")
