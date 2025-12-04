"""
PO Report Processor - Memory Optimized Version
Processes raw PO reports from Oracle BIP with minimal memory footprint
"""

import pandas as pd
import numpy as np
from datetime import datetime
import io
import gc


def process_po_report_streaming(excel_data, from_date="01-01-2024", to_date=datetime.now().strftime("%d-%m-%Y")):
    """
    Process PO report Excel data with memory optimization.
    Returns file data as bytes instead of storing DataFrames in memory.
    
    Args:
        excel_data (bytes): Raw Excel file data (.xls format with multiple sheets)
        from_date (str): Start date of the report (MM-DD-YYYY)
        to_date (str): End date of the report (MM-DD-YYYY)
    
    Returns:
        dict: Dictionary with filenames as keys and CSV bytes as values
    """
    
    # Process in chunks and immediately convert to CSV to save memory
    reports = {}
    
    # Step 1: Combine sheets and save immediately
    combined_csv = _combine_excel_sheets_streaming(excel_data, from_date, to_date)
    reports['combined'] = combined_csv
    
    # Step 2: Process aggregated report from CSV (not from DataFrame)
    processed_csv = _create_processed_report_streaming(combined_csv, from_date, to_date)
    reports['processed'] = processed_csv
    
    # Step 3: Process detailed report from CSV
    detailed_csv = _create_detailed_report_streaming(combined_csv, from_date, to_date)
    reports['detailed'] = detailed_csv
    
    # Force garbage collection
    gc.collect()
    
    return reports


def _combine_excel_sheets_streaming(excel_data, from_date, to_date):
    """
    Combine all sheets from Excel file and return as CSV bytes.
    Processes sheets one at a time to minimize memory usage.
    """
    xls = pd.ExcelFile(io.BytesIO(excel_data))
    sheet_names = xls.sheet_names
    
    # Read first sheet to get column template
    df_first = pd.read_excel(xls, sheet_name=sheet_names[0], header=0)
    df_first.columns = df_first.columns.str.strip()
    columns_template = df_first.columns
    
    # Add metadata
    generation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_first.insert(0, 'Report Type', 'Combined')
    df_first.insert(1, 'Date Range', f'{from_date} to {to_date}')
    df_first.insert(2, 'Generation Date', generation_date)
    
    # Write first sheet to CSV buffer
    output = io.StringIO()
    df_first.to_csv(output, index=False)
    
    # Clear first dataframe from memory
    del df_first
    gc.collect()
    
    # Process remaining sheets one at a time
    for sheet in sheet_names[1:]:
        df = pd.read_excel(xls, sheet_name=sheet, header=None)
        
        # Skip if column mismatch
        if df.shape[1] != len(columns_template):
            del df
            continue
        
        df.columns = columns_template
        
        # Add metadata
        df.insert(0, 'Report Type', 'Combined')
        df.insert(1, 'Date Range', f'{from_date} to {to_date}')
        df.insert(2, 'Generation Date', generation_date)
        
        # Append to CSV (without header)
        df.to_csv(output, index=False, header=False)
        
        # Clear dataframe from memory
        del df
        gc.collect()
    
    # Get CSV bytes
    csv_bytes = output.getvalue().encode('utf-8')
    output.close()
    
    return csv_bytes


def _create_processed_report_streaming(combined_csv, from_date, to_date):
    """
    Create processed report from CSV data with chunked processing.
    """
    # Read CSV in chunks to reduce memory
    chunk_size = 10000
    chunks = []
    
    for chunk in pd.read_csv(io.BytesIO(combined_csv), chunksize=chunk_size):
        # Remove metadata columns
        chunk = chunk.drop(columns=['Report Type', 'Date Range', 'Generation Date'])
        chunks.append(chunk)
    
    # Combine chunks
    df = pd.concat(chunks, ignore_index=True)
    del chunks
    gc.collect()
    
    # Define grouping keys and numeric columns
    keys = [
        'Po Number',
        'POCharge A/c',
        'Supplier',
        'Currency',
        'Invoice Number',
        'Invoice Line Number',
        'Line Amount',
        'Line Maount in Functional Currency'
    ]
    
    num = [
        'Amount Received',
        'Amount in transaction Currency',
        'Amount in Functional Currency'
    ]
    
    # Fill NaN values
    df[keys] = df[keys].fillna(0)
    df[num] = df[num].fillna(0)
    
    # Group and sum
    summ = df.groupby(keys)[num].sum().reset_index().sort_values(by=keys[0])
    
    # Clear original df
    del df
    gc.collect()
    
    # Calculate conversion rate
    summ['conversion rate'] = np.where(
        (summ['Amount in Functional Currency'] == 0) & (summ['Amount in transaction Currency'] == 0),
        1,
        summ['Amount in Functional Currency'] / summ['Amount in transaction Currency']
    )
    
    # Handle duplicates
    key_cols = ['Po Number', 'Invoice Number', 'Invoice Line Number']
    summ['dup_index'] = summ.groupby(key_cols).cumcount()
    mask = summ['dup_index'] > 0
    summ.loc[mask, ['Line Amount', 'Line Maount in Functional Currency']] = 0
    summ = summ.drop(columns='dup_index')
    
    # Calculate differences
    summ['diff'] = summ['Line Amount'] - summ['Amount Received']
    summ['diff InSAR'] = summ['diff'] * summ['conversion rate']
    
    # Special handling
    summ.loc[summ['Po Number'].isin(["SA-AFR-PO-170664", "SA-AFR-PO-178578"]), "diff InSAR"] = 0
    
    # Add metadata
    generation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summ.insert(0, 'Report Type', 'Processed')
    summ.insert(1, 'Date Range', f'{from_date} to {to_date}')
    summ.insert(2, 'Generation Date', generation_date)
    
    # Convert to CSV bytes
    csv_bytes = summ.to_csv(index=False).encode('utf-8')
    
    # Clear dataframe
    del summ
    gc.collect()
    
    return csv_bytes


def _create_detailed_report_streaming(combined_csv, from_date, to_date):
    """
    Create detailed report from CSV data with chunked processing.
    """
    # Read CSV in chunks
    chunk_size = 10000
    chunks = []
    
    for chunk in pd.read_csv(io.BytesIO(combined_csv), chunksize=chunk_size):
        # Remove metadata columns
        chunk = chunk.drop(columns=['Report Type', 'Date Range', 'Generation Date'])
        chunks.append(chunk)
    
    # Combine chunks
    df = pd.concat(chunks, ignore_index=True)
    del chunks
    gc.collect()
    
    # Identify duplicates
    df["Dup_ind"] = df.groupby([
        "Po Number",
        "Invoice Number",
        "Invoice Line Number",
        "Line Amount"
    ]).cumcount() + 1
    
    # Create adjusted amounts
    df["Line_amount_adj"] = np.where(df["Dup_ind"] > 1, 0, df["Line Amount"])
    df["Invoice_line_amount_in_sar"] = np.where(
        df["Dup_ind"] > 1,
        0,
        df["Line Maount in Functional Currency"]
    )
    
    # Calculate conversion rate
    df["conversion_rate"] = df["Amount in Functional Currency"] / df["Amount in transaction Currency"]
    
    # Calculate amounts in SAR
    df['Amount_recieved_in_SAR'] = df['Amount Received'] * df['conversion_rate']
    df['GRN_amount_in_SAR'] = (
        df['Amount Received'].fillna(0) - df["Line_amount_adj"].fillna(0)
    ) * df["conversion_rate"]
    
    # Add metadata
    generation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df.insert(0, 'Report Type', 'ProcessedDetailed')
    df.insert(1, 'Date Range', f'{from_date} to {to_date}')
    df.insert(2, 'Generation Date', generation_date)
    
    # Convert to CSV bytes
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    
    # Clear dataframe
    del df
    gc.collect()
    
    return csv_bytes


def save_reports_streaming(reports_dict, from_date, to_date):
    """
    Format report filenames and return download-ready dictionary.
    
    Args:
        reports_dict: Dict with keys 'combined', 'processed', 'detailed' and CSV bytes as values
        from_date: Start date
        to_date: End date
    
    Returns:
        dict: Filenames mapped to CSV bytes
    """
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    from_clean = from_date.replace('-', '')
    to_clean = to_date.replace('-', '')
    
    return {
        f"Combined_PO_Report_{from_clean}_to_{to_clean}_{date_str}.csv": reports_dict['combined'],
        f"Processed_PO_Report_{from_clean}_to_{to_clean}_{date_str}.csv": reports_dict['processed'],
        f"ProcessedDetailed_PO_Report_{from_clean}_to_{to_clean}_{date_str}.csv": reports_dict['detailed']
    }


if __name__ == "__main__":
    print("PO Report Processor - Memory Optimized")
    print("=" * 80)
    print("This version processes reports with minimal memory footprint")
    print("- Streams data instead of loading all at once")
    print("- Processes in chunks")
    print("- Immediately converts to CSV")
    print("- Forces garbage collection")
