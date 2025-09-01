import frappe
import json
from datetime import datetime
from typing import List, Dict, Any, Set, Tuple

@frappe.whitelist(allow_guest=True)
def upload_bulk_biometric_data():
    """
    Handles bulk upload of biometric data via API endpoint with strict duplicate prevention.
    Only unique records based on (attendance_device_id, timestamp, device_id) are logged.
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
                "details": {"success": [], "failed": [], "duplicates": []}
            }

        # Process the records with strict duplicate checking
        results = process_bulk_records_with_strict_duplicate_check(records)

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
            "message": f"Processed {len(results['success'])} unique records successfully. "
                      f"Duplicates skipped: {len(results['duplicates'])}. "
                      f"Failed: {len(results['failed'])}",
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
            "details": {"success": [], "failed": [{"error": str(e)}], "duplicates": []}
        }

def process_bulk_records_with_strict_duplicate_check(records: List[Dict[str, Any]]) -> Dict[str, List]:
    """
    Process biometric records with strict duplicate checking before bulk insert.
    Ensures only unique records based on (attendance_device_id, timestamp, device_id) are processed.
    """
    results = {"success": [], "failed": [], "duplicates": []}
    
    # Get all existing records from database using Frappe ORM
    existing_records = get_existing_records_with_orm(records)
    
    # Track records in current batch to prevent intra-batch duplicates
    current_batch_keys = set()
    
    try:
        for record in records:
            try:
                # Validate record structure and data
                validate_record(record)
                
                # Create unique key for this record
                record_key = create_record_key(record)
                
                # Check for duplicate in existing database records
                if record_key in existing_records:
                    results["duplicates"].append({
                        "record": record,
                        "reason": "Already exists in database",
                        "key": f"attendance_device_id:{record_key[0]}, timestamp:{record_key[1]}, device_id:{record_key[2]}"
                    })
                    continue
                
                # Check for duplicate within current batch
                if record_key in current_batch_keys:
                    results["duplicates"].append({
                        "record": record,
                        "reason": "Duplicate within current batch",
                        "key": f"attendance_device_id:{record_key[0]}, timestamp:{record_key[1]}, device_id:{record_key[2]}"
                    })
                    continue
                
                # Record is unique - create new document
                insert_unique_record(record)
                
                results["success"].append(record)
                current_batch_keys.add(record_key)

            except Exception as e:
                results["failed"].append({
                    "record": record, 
                    "error": str(e)
                })

        # Commit all successful insertions
        if results["success"]:
            frappe.db.commit()
            frappe.logger().info(f"Successfully inserted {len(results['success'])} unique biometric records")

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            title="Bulk Biometric Data Processing Failed",
            message=f"Error: {str(e)}\nRecords: {len(records)}"
        )
        # Mark all successful records as failed due to rollback
        for record in results["success"]:
            results["failed"].append({
                "record": record, 
                "error": f"Transaction rollback: {str(e)}"
            })
        results["success"] = []

    return results

def get_existing_records_with_orm(records: List[Dict[str, Any]]) -> Set[Tuple[str, str, str]]:
    """
    Get existing records from database using Frappe ORM methods.
    Returns a set of tuples (attendance_device_id, timestamp, device_id) for O(1) lookup.
    """
    if not records:
        return set()
    
    try:
        # Extract unique attendance_device_ids for filtering
        attendance_device_ids = list({str(r["attendance_device_id"]) for r in records})
        
        if not attendance_device_ids:
            return set()
        
        # Use Frappe ORM to get existing records
        existing_docs = frappe.get_all(
            "Biometric Data Staging",
            filters={
                "attendance_device_id": ["in", attendance_device_ids]
            },
            fields=["attendance_device_id", "timestamp", "device_id"],
            limit=None  # Get all matching records
        )
        
        # Convert to set of normalized tuples
        existing_keys = set()
        for doc in existing_docs:
            key = (
                str(doc.get("attendance_device_id", "")),
                normalize_timestamp(doc.get("timestamp", "")),
                str(doc.get("device_id") or "")
            )
            existing_keys.add(key)
        
        return existing_keys
        
    except Exception as e:
        frappe.log_error(
            title="Failed to fetch existing biometric records",
            message=f"Error: {str(e)}"
        )
        # Return empty set to be safe - will result in potential duplicates but won't crash
        return set()

def insert_unique_record(record: Dict[str, Any]) -> None:
    """
    Insert a single unique record using Frappe ORM.
    """
    # Create new Biometric Data Staging document
    doc = frappe.new_doc("Biometric Data Staging")
    
    # Set field values
    doc.attendance_device_id = record["attendance_device_id"]
    doc.timestamp = normalize_timestamp_for_db(record["timestamp"])
    doc.punch_type = record["punch_type"]
    doc.device_id = record.get("device_id")
    doc.status = record.get("status", "Pending")
    doc.latitude = float(record.get("latitude", 0.0000))  
    doc.longitude = float(record.get("longitude", 0.0000))  
    
    # Insert the document
    doc.insert(ignore_permissions=True)

def create_record_key(record: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Create a standardized key tuple from a record for duplicate checking.
    """
    return (
        str(record["attendance_device_id"]),
        normalize_timestamp(record["timestamp"]),
        str(record.get("device_id", ""))
    )

def normalize_timestamp(timestamp: Any) -> str:
    """
    Normalize timestamp to consistent string format for comparison.
    """
    if isinstance(timestamp, str):
        # Parse and reformat to ensure consistent format
        try:
            # Handle various ISO formats
            timestamp_clean = timestamp.replace('Z', '+00:00')
            dt = datetime.fromisoformat(timestamp_clean)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            # If parsing fails, return as-is and let validation catch it
            return str(timestamp)
    elif isinstance(timestamp, datetime):
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    else:
        return str(timestamp)

def normalize_timestamp_for_db(timestamp: Any) -> str:
    """
    Normalize timestamp for database insertion.
    """
    if isinstance(timestamp, str):
        try:
            # Parse and return in Frappe's expected format
            timestamp_clean = timestamp.replace('Z', '+00:00')
            dt = datetime.fromisoformat(timestamp_clean)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {timestamp}")
    elif isinstance(timestamp, datetime):
        return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    else:
        raise ValueError(f"Unsupported timestamp type: {type(timestamp)}")

def validate_record(record: Dict[str, Any]) -> None:
    """
    Validate biometric record fields with enhanced checks.
    """
    if not isinstance(record, dict):
        raise ValueError("Record must be a dictionary")
    
    # Check required fields
    required_fields = ["attendance_device_id", "timestamp", "punch_type", "latitude", "longitude"]  
    missing_fields = [field for field in required_fields if field not in record or record[field] is None]
    
    if missing_fields:
        raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate attendance_device_id
    if not str(record["attendance_device_id"]).strip():
        raise ValueError("attendance_device_id cannot be empty")

    # Validate timestamp format
    try:
        normalize_timestamp_for_db(record["timestamp"])
    except ValueError as e:
        raise ValueError(f"Invalid timestamp: {str(e)}")

    # Validate punch_type
    valid_punch_types = ["IN", "OUT", "AUTO", ""]
    if record["punch_type"] not in valid_punch_types:
        raise ValueError(f"Invalid punch_type '{record['punch_type']}'. Must be one of: {', '.join(valid_punch_types)}")

    # Validate status (if provided)
    if "status" in record and record["status"] is not None:
        valid_statuses = ["Pending", "Processed", "Ignored", "Duplicate", ""]
        if record["status"] not in valid_statuses:
            raise ValueError(f"Invalid status '{record['status']}'. Must be one of: {', '.join(valid_statuses)}")

    # Validate device_id format if provided
    if "device_id" in record and record["device_id"] is not None:
        device_id = str(record["device_id"]).strip()
        if len(device_id) > 100:
            raise ValueError("device_id too long (max 100 characters)")

    # Validate latitude and longitude
    try:
        latitude = float(record["latitude"])
        longitude = float(record["longitude"])
        if not (-90 <= latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not (-180 <= longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180 degrees")
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid latitude or longitude: {str(e)}")


def check_record_exists(attendance_device_id: str, timestamp: str, device_id: str = None) -> bool:
    """
    Utility function to check if a specific record already exists using Frappe ORM.
    """
    try:
        filters = {
            "attendance_device_id": attendance_device_id,
            "timestamp": normalize_timestamp_for_db(timestamp)
        }
        
        # Handle device_id - check for both null and empty string cases
        if device_id is not None and str(device_id).strip():
            filters["device_id"] = device_id
        else:
            # For null/empty device_id, we need to check using get_all with custom logic
            # since Frappe ORM doesn't handle null checks as elegantly
            existing_records = frappe.get_all(
                "Biometric Data Staging",
                filters={
                    "attendance_device_id": attendance_device_id,
                    "timestamp": normalize_timestamp_for_db(timestamp)
                },
                fields=["device_id"],
                limit=1
            )
            
            for record in existing_records:
                db_device_id = record.get("device_id") or ""
                input_device_id = str(device_id or "")
                if db_device_id == input_device_id:
                    return True
            return False
        
        # For non-null device_id, simple existence check
        return frappe.db.exists("Biometric Data Staging", filters)
        
    except Exception as e:
        frappe.log_error(
            title="Error checking record existence",
            message=f"Error: {str(e)}\nFilters: {filters}"
        )
        return False

def get_duplicate_records(attendance_device_id: str = None, device_id: str = None, limit: int = 100) -> List[Dict]:
    """
    Get duplicate records using Frappe ORM for analysis purposes.
    """
    try:
        filters = {}
        if attendance_device_id:
            filters["attendance_device_id"] = attendance_device_id
        if device_id is not None:
            filters["device_id"] = device_id
            
        return frappe.get_all(
            "Biometric Data Staging",
            filters=filters,
            fields=["name", "attendance_device_id", "timestamp", "device_id", "status", "creation"],
            order_by="timestamp desc",
            limit=limit
        )
        
    except Exception as e:
        frappe.log_error(
            title="Error fetching duplicate records",
            message=f"Error: {str(e)}"
        )
        return []

def cleanup_duplicate_records(dry_run: bool = True) -> Dict[str, Any]:
    """
    Identify and optionally remove duplicate records using Frappe ORM.
    Set dry_run=False to actually delete duplicates.
    """
    try:
        # Get all records ordered by creation time
        all_records = frappe.get_all(
            "Biometric Data Staging",
            fields=["name", "attendance_device_id", "timestamp", "device_id", "creation"],
            order_by="creation asc"
        )
        
        seen_keys = set()
        duplicates = []
        
        for record in all_records:
            key = (
                str(record["attendance_device_id"]),
                normalize_timestamp(record["timestamp"]),
                str(record.get("device_id") or "")
            )
            
            if key in seen_keys:
                duplicates.append(record)
            else:
                seen_keys.add(key)
        
        result = {
            "total_records": len(all_records),
            "unique_records": len(seen_keys),
            "duplicate_count": len(duplicates),
            "duplicates": duplicates[:50],  # Show first 50 duplicates
            "dry_run": dry_run
        }
        
        if not dry_run and duplicates:
            # Delete duplicates
            for duplicate in duplicates:
                frappe.delete_doc("Biometric Data Staging", duplicate["name"], ignore_permissions=True)
            
            frappe.db.commit()
            result["deleted_count"] = len(duplicates)
        
        return result
        
    except Exception as e:
        frappe.log_error(
            title="Error during duplicate cleanup",
            message=f"Error: {str(e)}"
        )
        return {"error": str(e)}