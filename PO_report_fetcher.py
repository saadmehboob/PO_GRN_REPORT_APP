"""
PO Report Fetcher - Oracle BIP Integration
Provides functions to schedule and download PO reports from Oracle BI Publisher
"""

import base64
import os
import time
import datetime
from requests import Session
from zeep import Client, Settings
from zeep.transports import Transport
from zeep.wsse.username import UsernameToken
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from dotenv import load_dotenv
load_dotenv()

# -------------------------------
# CONFIGURATION
# -------------------------------
BIP_WSDL = "https://ehkp.fa.em2.oraclecloud.com/xmlpserver/services/PublicReportService?wsdl"
SCHEDULE_WSDL = "https://ehkp.fa.em2.oraclecloud.com/xmlpserver/services/v2/ScheduleService?wsdl"
USERNAME = os.getenv("ORACLE_USERNAME")    
PASSWORD = os.getenv("ORACLE_PASSWORD")
REPORT_PATH = "/Custom/Procurement/Purchasing/PO Report/PO_RECP_INV_V8.xdo"

# Default date range
DEFAULT_FROM_DATE = "01-01-2020"

# -------------------------------
# SETUP CLIENTS
# -------------------------------
session = Session()
session.verify = False
transport = Transport(session=session, timeout=12000)
settings = Settings(strict=False, xml_huge_tree=True)

# Schedule client for scheduling and downloading reports
schedule_client = Client(wsdl=SCHEDULE_WSDL, wsse=UsernameToken(USERNAME, PASSWORD))


def _make_param_dict(name, val):
    """Helper function to create a parameter dictionary"""
    return {
        "name": name,
        "values": {"item": [val]},
        "dataType": "xsd:string",
        "UIType": "text",
        "multiValuesAllowed": False,
        "refreshParamOnChange": False,
        "selectAll": False,
        "templateParam": False,
        "useNullForAll": False
    }


def _schedule_report(from_date, to_date):
    """
    Internal function to schedule a PO report.
    
    Args:
        from_date (str): Start date in format MM-DD-YYYY
        to_date (str): End date in format MM-DD-YYYY
    
    Returns:
        str: Job ID of the scheduled report
    """
    params = [
        _make_param_dict("p_business_group", "Saudi Arabia BU"),
        _make_param_dict("p_po_number", "*"),
        _make_param_dict("p_From_date", from_date),
        _make_param_dict("p_To_date", to_date)
    ]

    report_req_dict = {
        "reportAbsolutePath": REPORT_PATH,
        "sizeOfDataChunkDownload": -1,
        "attributeFormat": "excel",
        "attributeLocale": "en-US",
        "attributeCalendar": "Gregorian",
        "parameterNameValues": {"listOfParamNameValues": {"item": params}},
        "byPassCache": True,
        "flattenXML": False
    }
    
    schedule_req_dict = {
        "reportRequest": report_req_dict,
        "saveOutputOption": True,
        "compressDeliveryOutputOption": False,
        "bookBindingOutputOption": False,
        "saveDataOption": False,
        "mergeOutputOption": False,
        "enableConsolidatedJobDiagnostic": False,
        "enableDataEngineDiagnostic": False,
        "enableReportProcessorDiagnostic": False,
        "enableSQLExplainPlan": False,
        "enableXmlPruning": False,
        "notificationPassword": None,
        "notificationServer": None,
        "notificationTo": None,
        "notificationUserName": None,
        "notifyHttpWhenFailed": False,
        "notifyHttpWhenSkipped": False,
        "notifyHttpWhenSuccess": False,
        "notifyHttpWhenWarning": False,
        "notifyWhenFailed": False,
        "notifyWhenSkipped": False,
        "notifyWhenSuccess": False,
        "notifyWhenWarning": False,
        "endDate": None,
        "jobLocale": "en-US",
        "jobTZ": "UTC",
        "recurrenceExpression": None,
        "recurrenceExpressionType": None,
        "repeatCount": 0,
        "repeatInterval": 0,
        "startDate": None,
        "scheduleBurstingOption": False,
        "scheduleChunkingOption": False,
        "schedulePublicOption": True,
        "useUTF8Option": True,
        "scheduleBurstringOption": False,
        "userJobName": f"PO_Report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "userJobDesc": "PO Report generated via Python API"
    }
    
    resp = schedule_client.service.scheduleReport(
        scheduleRequest=schedule_req_dict,
        userID=USERNAME,
        password=PASSWORD
    )
    
    # Extract job ID from response
    if isinstance(resp, str):
        job_id = resp
    elif hasattr(resp, 'requestId'):
        job_id = resp.requestId
    elif hasattr(resp, 'jobId'):
        job_id = resp.jobId
    else:
        job_id = str(resp)
    
    return job_id


def _resolve_instance_id(job_id):
    """
    Internal function to resolve job ID to instance ID with fallback logic.
    
    Args:
        job_id (str): Job ID to resolve
        
    Returns:
        str: Resolved instance ID
    """
    try:
        # Try to get instance IDs
        # Note: using submittedJobId based on WSDL requirement
        instances = schedule_client.service.getAllJobInstanceIDs(
            submittedJobId=str(job_id),
            userID=USERNAME,
            password=PASSWORD
        )
        
        if instances and hasattr(instances, 'item'):
            instance_list = instances.item if isinstance(instances.item, list) else [instances.item]
            if instance_list:
                instance_id = instance_list[0]
                print(f"Resolved Job ID {job_id} to Instance ID {instance_id}")
                return instance_id
                
    except Exception as e:
        print(f"Warning: Could not resolve instance ID for {job_id}: {e}")
        
    # Fallback: increment by 1
    fallback_id = str(int(job_id) + 1)
    print(f"Using fallback Instance ID: {fallback_id} (Job ID + 1)")
    return fallback_id


def _wait_for_completion(job_id, poll_interval=10, timeout=3600):
    """
    Internal function to wait for report completion.
    
    Args:
        job_id (str): Job ID to monitor
        poll_interval (int): Seconds between status checks
        timeout (int): Maximum seconds to wait
    
    Returns:
        str: Job instance ID when complete
    
    Raises:
        Exception: If job fails or times out
    """
    start_time = time.time()
    
    while True:
        if time.time() - start_time > timeout:
            raise Exception(f"Timeout waiting for job {job_id}")
        
        status_resp = schedule_client.service.getScheduledReportStatus(
            scheduledJobID=job_id,
            userID=USERNAME,
            password=PASSWORD
        )
        
        status = status_resp.jobStatus
        status_upper = status.upper() if status else ""
        
        # SUCCESS or PROBLEM status means output is available
        # PROBLEM typically means delivery failed but report generation succeeded
        if status_upper in ['SUCCESS', 'PROBLEM']:
            # Resolve the instance ID (with fallback to job_id + 1)
            return _resolve_instance_id(job_id)
        elif status_upper in ['FAILED', 'CANCELLED', 'CANCELED', 'SKIPPED']:
            raise Exception(f"Job failed with status: {status}")
        
        time.sleep(poll_interval)


def _download_output(job_instance_id):
    """
    Internal function to download report output.
    
    Args:
        job_instance_id (str): Job instance ID
    
    Returns:
        bytes: Raw Excel file data
    """
    # Get output info
    output_info = schedule_client.service.getScheduledReportOutputInfo(
        jobInstanceID=job_instance_id,
        userID=USERNAME,
        password=PASSWORD
    )
    
    if hasattr(output_info, 'item'):
        outputs = output_info.item if isinstance(output_info.item, list) else [output_info.item]
    else:
        outputs = [output_info]
    
    # Get the first output
    if not outputs:
        raise Exception("No output found for job")
    
    output = outputs[0]
    output_id = getattr(output, 'outputId', None)
    
    if not output_id:
        raise Exception("No output ID found")
    
    # Download the document
    doc_resp = schedule_client.service.getDocumentData(
        jobOutputID=str(output_id),
        userID=USERNAME,
        password=PASSWORD
    )
    
    file_data = doc_resp
    
    # Handle base64 decoding if needed
    if isinstance(file_data, str):
        missing = len(file_data) % 4
        if missing:
            file_data += "=" * (4 - missing)
        file_data = base64.b64decode(file_data)
    
    return file_data


# -------------------------------
# PUBLIC API FUNCTIONS
# -------------------------------

def run_po_report(to_date=None, from_date=DEFAULT_FROM_DATE):
    """
    Schedule, wait for completion, and download a PO report.
    
    Args:
        to_date (str, optional): End date in format MM-DD-YYYY. Defaults to today.
        from_date (str, optional): Start date in format MM-DD-YYYY. Defaults to 01-01-2020.
    
    Returns:
        tuple: (job_id, file_data) where file_data is bytes of the Excel file
    
    Example:
        job_id, excel_data = run_po_report(to_date="12-04-2025")
        with open("report.xlsx", "wb") as f:
            f.write(excel_data)
    """
    if to_date is None:
        to_date = datetime.datetime.now().strftime("%m-%d-%Y")
    
    # Schedule the report
    job_id = _schedule_report(from_date, to_date)
    
    # Wait for completion
    job_instance_id = _wait_for_completion(job_id)
    
    # Download the output
    file_data = _download_output(job_instance_id)
    
    return job_id, file_data


def download_po_report(job_id):
    """
    Download a PO report from an existing job ID.
    
    Args:
        job_id (str): The job ID of a previously scheduled report
    
    Returns:
        bytes: Raw Excel file data
    
    Example:
        excel_data = download_po_report("2995978")
        with open("report.xlsx", "wb") as f:
            f.write(excel_data)
    """
    # Resolve instance ID (with fallback)
    job_instance_id = _resolve_instance_id(job_id)
    file_data = _download_output(job_instance_id)
    return file_data


if __name__ == "__main__":
    # Test the functions
    print("Testing PO Report Fetcher...")
    print("=" * 80)
    
    # Test 1: Schedule and download
    print("\nTest 1: Schedule, wait, and download")
    job_id, data = run_po_report(to_date="12-04-2025")
    print(f"Job ID: {job_id}")
    print(f"Downloaded {len(data)} bytes")
    
    # Test 2: Download from existing job
    print("\nTest 2: Download from existing job ID")
    data2 = download_po_report(job_id)
    print(f"Downloaded {len(data2)} bytes")
