"""
PO Report Fetcher - Streamlit App
Web interface for scheduling and downloading PO reports from Oracle BI Publisher
"""

import streamlit as st
import datetime
import io
import os
import pandas as pd
import gc
from PO_report_fetcher import run_po_report, download_po_report, DEFAULT_FROM_DATE
from PO_report_processor_optimized import process_po_report_streaming, save_reports_streaming

# Page configuration
st.set_page_config(
    page_title="PO GRN Report Fetcher",
    page_icon="📊",
    layout="wide"
)

# -------------------------------
# AUTHENTICATION
# -------------------------------
def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == os.getenv("APP_PASSWORD", "cenomi123"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.text_input(
            "🔐 Enter Password", type="password", on_change=password_entered, key="password"
        )
        st.info("Please enter the application password to continue.")
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error
        st.text_input(
            "🔐 Enter Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True

if not check_password():
    st.stop()

# Header
st.title("📊 PO GRN Report Fetcher & Processor")
st.markdown("Oracle BI Publisher - Purchase Order GRN Report Management & Processing")
st.divider()

# Create tabs
tab1, tab2 = st.tabs(["🔄 Schedule & Download", "📥 Download from Job ID"])

# -------------------------------
# TAB 1: Schedule & Download
# -------------------------------
with tab1:
    st.subheader("Schedule New Report")
    
    # Info box
    st.info(f"""
    **Report Parameters:**
    - **Business Unit:** Saudi Arabia BU
    - **PO Number:** All
    - **From Date:** {DEFAULT_FROM_DATE} (fixed)
    - **To Date:** Select below
    """)
    
    # Date selector
    col1, col2 = st.columns([2, 3])
    
    with col1:
        to_date = st.date_input(
            "Select To Date",
            value=datetime.date.today(),
            max_value=datetime.date.today(),
            help="Select the end date for the report"
        )
        
        # Convert to MM-DD-YYYY format
        to_date_str = to_date.strftime("%m-%d-%Y")
        
        st.caption(f"📅 Date Range: {DEFAULT_FROM_DATE} to {to_date_str}")
        
        # Processing option
        process_report = st.checkbox(
            "Process Report (Generate 3 files)",
            value=True,
            help="Generate Combined, Processed, and ProcessedDetailed reports"
        )
    
    with col2:
        st.markdown("### Report Preview")
        if process_report:
            st.info(f"""
            **Report Name:** PO_RECP_INV_V8  
            **Format:** CSV  
            **Output Files:** 3 (Combined, Processed, ProcessedDetailed)  
            **Expected Processing Time:** 15-20 minutes
            """)
        else:
            st.info(f"""
            **Report Name:** PO_RECP_INV_V8  
            **Format:** Excel (.xls)  
            **Output Files:** 1 (Raw report)  
            **Expected Processing Time:** 15-20 minutes
            """)
    
    # Run button
    if st.button("🚀 Schedule & Download Report", type="primary", use_container_width=True):
        try:
            # Create progress placeholder
            progress_text = st.empty()
            progress_bar = st.progress(0)
            
            progress_text.text("Step 1/4: Scheduling report with Oracle BIP...")
            progress_bar.progress(10)
            
            # Schedule and download
            job_id, file_data = run_po_report(to_date=to_date_str)
            
            progress_text.text(f"Step 2/4: Report scheduled (Job ID: {job_id}). Waiting for completion...")
            progress_bar.progress(50)
            
            progress_text.text("Step 3/4: Downloading report data...")
            progress_bar.progress(70)
            
            # Success message for raw download
            st.success(f"""
            ✅ **Report Downloaded Successfully!**
            - **Job ID:** {job_id}
            - **File Size:** {len(file_data):,} bytes ({len(file_data) / 1024 / 1024:.2f} MB)
            - **Date Range:** {DEFAULT_FROM_DATE} to {to_date_str}
            """)
            
            # Store in session state
            st.session_state['last_job_id'] = job_id
            st.session_state['last_file_data'] = file_data
            st.session_state['last_to_date'] = to_date_str
            st.session_state['last_from_date'] = DEFAULT_FROM_DATE
            
            if process_report:
                progress_text.text("Step 4/4: Processing report (generating 3 files)...")
                progress_bar.progress(80)
                
                # Process the report using streaming (memory optimized)
                reports_dict = process_po_report_streaming(
                    file_data,
                    DEFAULT_FROM_DATE,
                    to_date_str
                )
                
                progress_bar.progress(90)
                
                # Format filenames
                reports = save_reports_streaming(
                    reports_dict,
                    DEFAULT_FROM_DATE,
                    to_date_str
                )
                
                progress_bar.progress(100)
                progress_text.empty()
                progress_bar.empty()
                
                # Store ONLY CSV bytes in session state (not DataFrames!)
                st.session_state['processed_reports'] = reports
                
                # Clear the reports_dict to free memory
                del reports_dict
                gc.collect()
                
                st.success("✅ All reports processed successfully!")
                
            else:
                # Just provide raw file download
                progress_bar.progress(100)
                progress_text.empty()
                progress_bar.empty()
                
                filename = f"PO_Report_Raw_{to_date_str.replace('-', '')}_{job_id}.xls"
                st.download_button(
                    label="⬇️ Download Raw Excel File",
                    data=file_data,
                    file_name=filename,
                    mime="application/vnd.ms-excel",
                    use_container_width=True
                )
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.exception(e)

    # Display download buttons if reports are available (outside button click block)
    if 'processed_reports' in st.session_state:
        st.markdown("### 📥 Download Processed Reports")
        
        reports = st.session_state['processed_reports']
        col1, col2, col3 = st.columns(3)
        
        for idx, (filename, data) in enumerate(reports.items()):
            col = [col1, col2, col3][idx]
            with col:
                report_type = filename.split('_')[0]
                st.download_button(
                    label=f"⬇️ {report_type}",
                    data=data,
                    file_name=filename,
                    mime="text/csv",
                    use_container_width=True,
                    key=f"download_{idx}"
                )
        
        # Show preview of processed report (load on-demand from CSV bytes)
        if 'processed_reports' in st.session_state:
            st.markdown("### 📊 Report Preview")
            
            reports = st.session_state['processed_reports']
            
            tab_preview1, tab_preview2, tab_preview3 = st.tabs([
                "Combined Report",
                "Processed Report",
                "ProcessedDetailed Report"
            ])
            
            # Load only first 10 rows for preview (memory efficient)
            with tab_preview1:
                csv_data = [v for k, v in reports.items() if 'Combined' in k][0]
                df = pd.read_csv(io.BytesIO(csv_data), nrows=10)
                total_rows = sum(1 for _ in io.BytesIO(csv_data)) - 1  # Count rows without loading all
                st.info(f"**Rows:** {total_rows:,} | **Columns:** {len(df.columns)}")
                st.dataframe(df, use_container_width=True)
                del df
                gc.collect()
            
            with tab_preview2:
                csv_data = [v for k, v in reports.items() if 'Processed_PO' in k][0]
                df = pd.read_csv(io.BytesIO(csv_data), nrows=10)
                total_rows = sum(1 for _ in io.BytesIO(csv_data)) - 1
                st.info(f"**Rows:** {total_rows:,} | **Columns:** {len(df.columns)}")
                st.dataframe(df, use_container_width=True)
                del df
                gc.collect()
            
            with tab_preview3:
                csv_data = [v for k, v in reports.items() if 'ProcessedDetailed' in k][0]
                df = pd.read_csv(io.BytesIO(csv_data), nrows=10)
                total_rows = sum(1 for _ in io.BytesIO(csv_data)) - 1
                st.info(f"**Rows:** {total_rows:,} | **Columns:** {len(df.columns)}")
                st.dataframe(df, use_container_width=True)
                del df
                gc.collect()


# -------------------------------
# TAB 2: Download from Job ID
# -------------------------------
with tab2:
    st.subheader("Download from Existing Job ID")
    
    st.info("""
    **About Job IDs:**  
    If you have previously scheduled a report, you can download it again using its Job ID.
    The Job ID can be found in the Oracle BI Publisher interface or from previous downloads.
    """)
    
    # Show last job ID if available
    if 'last_job_id' in st.session_state:
        st.success(f"💡 Last generated Job ID: **{st.session_state['last_job_id']}** (Date range: {st.session_state.get('last_from_date', 'N/A')} to {st.session_state.get('last_to_date', 'N/A')})")
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        job_id_input = st.text_input(
            "Enter Job ID",
            placeholder="e.g., 2995978",
            help="Enter the Job ID of the report you want to download"
        )
        
        process_existing = st.checkbox(
            "Process Report (Generate 3 files)",
            value=True,
            help="Generate Combined, Processed, and ProcessedDetailed reports",
            key="process_existing"
        )
        
        if st.button("📥 Download Report", type="primary", use_container_width=True):
            if not job_id_input:
                st.error("⚠️ Please enter a Job ID")
            else:
                job_id_input = str(int(job_id_input) - 1)
                
                try:
                    with st.spinner(f"Downloading report for Job ID: {job_id_input}..."):
                        file_data = download_po_report(job_id_input)
                        
                        # Success message
                        st.success(f"""
                        ✅ **Report Downloaded Successfully!**
                        - **Job ID:** {job_id_input}
                        - **File Size:** {len(file_data):,} bytes ({len(file_data) / 1024 / 1024:.2f} MB)
                        """)
                        
                        if process_existing:
                            with st.spinner("Processing report..."):
                                # Use default dates for processing
                                from_date_default = DEFAULT_FROM_DATE
                                to_date_default = datetime.date.today().strftime("%m-%d-%Y")
                                
                                # Process the report using streaming (memory optimized)
                                reports_dict = process_po_report_streaming(
                                    file_data,
                                    from_date_default,
                                    to_date_default
                                )
                                
                                # Format filenames
                                reports = save_reports_streaming(
                                    reports_dict,
                                    from_date_default,
                                    to_date_default
                                )
                                
                                st.success("✅ All reports processed successfully!")
                                
                                # Store ONLY CSV bytes in session state
                                st.session_state['processed_reports_tab2'] = reports
                                
                                # Clear memory
                                del reports_dict
                                del file_data
                                gc.collect()
                                
                        else:
                            # Just provide raw download
                            filename = f"PO_Report_{job_id_input}.xls"
                            st.download_button(
                                label="⬇️ Download Raw Excel File",
                                data=file_data,
                                file_name=filename,
                                mime="application/vnd.ms-excel",
                                use_container_width=True
                            )
                    
                except Exception as e:
                    st.error(f"❌ Error downloading report: {str(e)}")
                    st.exception(e)
    
    with col2:
        st.markdown("### 📝 Instructions")
        st.markdown("""
        1. Enter the Job ID in the text field
        2. Choose whether to process the report
        3. Click the "Download Report" button
        4. Wait for processing to complete
        5. Download the generated files
        
        **Note:** The report must have been previously generated and completed successfully.
        The date range in the processed files will use default values (01-01-2020 to today).
        """)

    # Display download buttons for Tab 2 (outside button click block)
    if 'processed_reports_tab2' in st.session_state:
        st.markdown("### 📥 Download Processed Reports")
        
        reports = st.session_state['processed_reports_tab2']
        col1, col2, col3 = st.columns(3)
        
        for idx, (filename, data) in enumerate(reports.items()):
            col = [col1, col2, col3][idx]
            with col:
                report_type = filename.split('_')[0]
                st.download_button(
                    label=f"⬇️ {report_type}",
                    data=data,
                    file_name=filename,
                    mime="text/csv",
                    use_container_width=True,
                    key=f"download_existing_{idx}"
                )
        
        # Show preview (load on-demand from CSV bytes)
        st.markdown("### 📊 Report Preview")
        tab_p1, tab_p2, tab_p3 = st.tabs([
            "Combined", "Processed", "ProcessedDetailed"
        ])
        
        with tab_p1:
            csv_data = [v for k, v in reports.items() if 'Combined' in k][0]
            df = pd.read_csv(io.BytesIO(csv_data), nrows=10)
            total_rows = sum(1 for _ in io.BytesIO(csv_data)) - 1
            st.info(f"**Rows:** {total_rows:,} | **Columns:** {len(df.columns)}")
            st.dataframe(df, use_container_width=True)
            del df
            gc.collect()
            
        with tab_p2:
            csv_data = [v for k, v in reports.items() if 'Processed_PO' in k][0]
            df = pd.read_csv(io.BytesIO(csv_data), nrows=10)
            total_rows = sum(1 for _ in io.BytesIO(csv_data)) - 1
            st.info(f"**Rows:** {total_rows:,} | **Columns:** {len(df.columns)}")
            st.dataframe(df, use_container_width=True)
            del df
            gc.collect()
            
        with tab_p3:
            csv_data = [v for k, v in reports.items() if 'ProcessedDetailed' in k][0]
            df = pd.read_csv(io.BytesIO(csv_data), nrows=10)
            total_rows = sum(1 for _ in io.BytesIO(csv_data)) - 1
            st.info(f"**Rows:** {total_rows:,} | **Columns:** {len(df.columns)}")
            st.dataframe(df, use_container_width=True)
            del df
            gc.collect()


# Footer
st.divider()
st.caption("🔒 Connected to Oracle BI Publisher | 📍 Saudi Arabia BU")
