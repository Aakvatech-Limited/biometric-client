import frappe
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
from frappe.utils import now

@frappe.whitelist(allow_guest=True)
def upload_bulk_biometric_data():
    """
    Handles bulk upload of biometric data via API endpoint.
    Uses UUID-based unique names instead of a sequential number.
    """
    if frappe.request.method != "POST":
        frappe.response["http_status_code"] = 405
        return {"success": False, "message": "Method not allowed"}

    try:
        records = json.loads(frappe.request.data)
        
        if not isinstance(records, list) or not records:
            return {
                "success": True,
                "message": "No records to process",
                "details": {"success": [], "failed": []}
            }

        # Process the records and perform bulk insert
        results = process_bulk_records(records)

        if not results["success"] and results["failed"]:
            first_error = results["failed"][0]["error"]
            frappe.response["http_status_code"] = 400
            return {
                "success": False,
                "message": f"All records failed. First error: {first_error}",
                "details": results
            }

        return {
            "success": True,
            "message": f"Processed {len(results['success'])} records successfully. Failed: {len(results['failed'])}",
            "details": results
        }

    except Exception as e:
        frappe.log_error(
            title="Bulk Biometric Upload Failed",
            message=f"Error: {str(e)}\nPayload: {frappe.request.data}"
        )
        frappe.response["http_status_code"] = 400
        return {
            "success": False,
            "message": str(e),
            "details": {"success": [], "failed": [{"error": str(e)}]}
        }

def process_bulk_records(records: List[Dict[str, Any]]) -> Dict[str, List]:
    """
    Process biometric records efficiently and insert them in bulk.
    Uses UUIDs for unique names instead of sequential numbering.
    """
    results = {"success": [], "failed": []}
    valid_records = []

    try:
        for record in records:
            try:
                validate_record(record)

                # Generate unique name using UUID
                unique_name = f"BDS-{uuid.uuid4().hex[:12].upper()}"

                # Prepare record for bulk insert
                valid_records.append([
                    unique_name,
                    record["attendance_device_id"],
                    record["timestamp"],
                    record["punch_type"],
                    record.get("device_id"),
                    record.get("status", "Pending"),
                    now()
                ])

                results["success"].append(record)

            except Exception as e:
                results["failed"].append({"record": record, "error": str(e)})

        if valid_records:
            # Perform bulk insert
            frappe.db.bulk_insert(
                "Biometric Data Staging",
                fields=["name", "attendance_device_id", "timestamp", "punch_type", "device_id", "status", "creation"],
                values=valid_records
            )
            frappe.db.commit()

    except Exception as e:
        error_msg = str(e)
        results["failed"].extend([{"record": rec, "error": f"Bulk insert failed: {error_msg}"} for rec in valid_records])
        results["success"] = []

        frappe.log_error(
            title="Bulk Biometric Data Processing Failed",
            message=f"Error: {error_msg}\nRecords: {json.dumps(valid_records, default=str)}"
        )

    return results

def validate_record(record: Dict[str, Any]) -> None:
    """
    Validate biometric record fields.
    """
    required_fields = ["attendance_device_id", "timestamp", "punch_type"]
    for field in required_fields:
        if field not in record:
            raise ValueError(f"Missing required field: {field}")

    # Validate timestamp
    try:
        if isinstance(record["timestamp"], str):
            datetime.fromisoformat(record["timestamp"].replace('Z', '+00:00'))
    except ValueError:
        raise ValueError("Invalid timestamp format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")

    # Validate punch_type
    valid_punch_types = ["IN", "OUT", "AUTO", ""]
    if record["punch_type"] not in valid_punch_types:
        raise ValueError(f"Invalid punch_type. Must be one of: {', '.join(valid_punch_types)}")

    # Validate status (if provided)
    if "status" in record:
        valid_statuses = ["Pending", "Processed", "Ignored", "Duplicate", ""]
        if record["status"] not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
