"""
PO Report Processor
Processes raw PO reports from Oracle BIP and generates three output files:
1. Combined Report - All sheets merged into one
2. Processed Report - Aggregated and calculated summary
3. Processed Detailed Report - Detailed calculations with adjustments
"""

import pandas as pd
import numpy as np
from datetime import datetime
import io


def process_po_report(excel_data, from_date="01-01-2024", to_date=datetime.now().strftime("%d-%m-%Y")):
    """
    Process PO report Excel data and generate three output files.
    
    Args:
        excel_data (bytes): Raw Excel file data (.xls format with multiple sheets)
        from_date (str): Start date of the report (MM-DD-YYYY)
        to_date (str): End date of the report (MM-DD-YYYY)
    
    Returns:
        tuple: (combined_df, processed_df, ProcessedDetailed_df)
            - combined_df: All sheets combined
            - processed_df: Aggregated summary with calculations
            - ProcessedDetailed_df: Detailed report with line-level adjustments
    """
    
    # Step 1: Combine all sheets from the Excel file
    combined_df = _combine_excel_sheets(excel_data)
    
    # Add metadata columns to combined report
    generation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    combined_df.insert(0, 'Report Type', 'Combined')
    combined_df.insert(1, 'Date Range', f'{from_date} to {to_date}')
    combined_df.insert(2, 'Generation Date', generation_date)
    
    # Step 2: Create processed (aggregated) report
    processed_df = _create_processed_report(combined_df)
    
    # Add metadata columns to processed report
    processed_df.insert(0, 'Report Type', 'Processed')
    processed_df.insert(1, 'Date Range', f'{from_date} to {to_date}')
    processed_df.insert(2, 'Generation Date', generation_date)
    
    # Step 3: Create processed detailed report
    ProcessedDetailed_df = _create_ProcessedDetailed_report(combined_df)
    
    # Add metadata columns to processed detailed report
    ProcessedDetailed_df.insert(0, 'Report Type', 'ProcessedDetailed')
    ProcessedDetailed_df.insert(1, 'Date Range', f'{from_date} to {to_date}')
    ProcessedDetailed_df.insert(2, 'Generation Date', generation_date)
    
    return combined_df, processed_df, ProcessedDetailed_df


def _combine_excel_sheets(excel_data):
    """
    Combine all sheets from a multi-sheet Excel file into one DataFrame.
    
    Args:
        excel_data (bytes): Raw Excel file data
    
    Returns:
        pd.DataFrame: Combined data from all sheets
    """
    # Load workbook
    xls = pd.ExcelFile(io.BytesIO(excel_data))
    sheet_names = xls.sheet_names
    
    # Read first sheet (with headers)
    df_first = pd.read_excel(xls, sheet_name=sheet_names[0], header=0)
    df_first.columns = df_first.columns.str.strip()  # Clean up column names
    columns_template = df_first.columns
    
    # List to hold all dataframes
    df_list = [df_first]
    
    # Process remaining sheets (no headers)
    for sheet in sheet_names[1:]:
        df = pd.read_excel(xls, sheet_name=sheet, header=None)
        
        # If column count mismatches, skip
        if df.shape[1] != len(columns_template):
            print(f"Skipping sheet '{sheet}' due to column mismatch: Expected {len(columns_template)}, got {df.shape[1]}")
            continue
        
        df.columns = columns_template
        df_list.append(df)
    
    # Combine all sheets
    combined_df = pd.concat(df_list, ignore_index=True)
    
    return combined_df


def _create_processed_report(combined_df):
    """
    Create processed (aggregated) report with calculations.
    
    Args:
        combined_df (pd.DataFrame): Combined data from all sheets
    
    Returns:
        pd.DataFrame: Processed report with aggregations and calculations
    """
    # Remove metadata columns for processing
    df = combined_df.drop(columns=['Report Type', 'Date Range', 'Generation Date'])
    
    # Define grouping keys and numeric columns
    keys = [
        'Po Number',
        'POCharge A/c',
        'Supplier',
        'Currency',
        'Invoice Number',
        'Invoice Line Number',
        'Line Amount',
        'Line Maount in Functional Currency'  # Keep original spelling from data
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
    
    # Calculate conversion rate
    summ['conversion rate'] = np.where(
        (summ['Amount in Functional Currency'] == 0) & (summ['Amount in transaction Currency'] == 0),
        1,  # if both are zero → set conversion rate = 1
        summ['Amount in Functional Currency'] / summ['Amount in transaction Currency']
    )
    
    # Handle duplicate invoice lines
    key_cols = ['Po Number', 'Invoice Number', 'Invoice Line Number']
    
    # Identify duplicates by group
    summ['dup_index'] = summ.groupby(key_cols).cumcount()
    
    # For all rows except the first in each group, set amounts to 0
    mask = summ['dup_index'] > 0
    summ.loc[mask, ['Line Amount', 'Line Maount in Functional Currency']] = 0
    
    # Drop helper column
    summ = summ.drop(columns='dup_index')
    
    # Calculate differences
    summ['diff'] = summ['Line Amount'] - summ['Amount Received']
    summ['diff InSAR'] = summ['diff'] * summ['conversion rate']
    
    # Special handling for specific PO numbers (hardcoded as requested)
    summ.loc[summ['Po Number'].isin(["SA-AFR-PO-170664", "SA-AFR-PO-178578"]), "diff InSAR"] = 0
    
    return summ


def _create_ProcessedDetailed_report(combined_df):
    """
    Create processed detailed report with line-level adjustments.
    
    Args:
        combined_df (pd.DataFrame): Combined data from all sheets
    
    Returns:
        pd.DataFrame: Processed detailed report
    """
    # Remove metadata columns for processing
    df = combined_df.drop(columns=['Report Type', 'Date Range', 'Generation Date']).copy()
    
    # Identify duplicates
    df["Dup_ind"] = df.groupby([
        "Po Number",
        "Invoice Number",
        "Invoice Line Number",
        "Line Amount"
    ]).cumcount() + 1
    
    # Create adjusted line amounts (set to 0 for duplicates)
    df["Line_amount_adj"] = np.where(df["Dup_ind"] > 1, 0, df["Line Amount"])
    df["Invoice_line_amount_in_sar"] = np.where(
        df["Dup_ind"] > 1,
        0,
        df["Line Maount in Functional Currency"]  # Keep original spelling
    )
    
    # Calculate conversion rate
    df["conversion_rate"] = df["Amount in Functional Currency"] / df["Amount in transaction Currency"]
    
    # Calculate amounts in SAR
    df['Amount_recieved_in_SAR'] = df['Amount Received'] * df['conversion_rate']
    df['GRN_amount_in_SAR'] = (
        df['Amount Received'].fillna(0) - df["Line_amount_adj"].fillna(0)
    ) * df["conversion_rate"]
    
    return df


def save_reports_to_csv(combined_df, processed_df, ProcessedDetailed_df, from_date, to_date):
    import io
    import pandas as pd
    from datetime import datetime

    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    from_clean = from_date.replace('-', '')
    to_clean = to_date.replace('-', '')

    reports = {}

    def write_df(df):
        return df.to_csv(index=False).encode('utf-8')

    reports[f"Combined_PO_Report_{from_clean}_to_{to_clean}_{date_str}.csv"] = write_df(combined_df)
    reports[f"Processed_PO_Report_{from_clean}_to_{to_clean}_{date_str}.csv"] = write_df(processed_df)
    reports[f"ProcessedDetailed_PO_Report_{from_clean}_to_{to_clean}_{date_str}.csv"] = write_df(ProcessedDetailed_df)

    return reports


if __name__ == "__main__":
    # Test the processor
    print("PO Report Processor Module")
    print("=" * 80)
    print("This module processes PO reports and generates three output files:")
    print("1. Combined Report - All sheets merged")
    print("2. Processed Report - Aggregated summary")
    print("3. Processed Detailed Report - Detailed calculations")
