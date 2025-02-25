# Copyright (c) 2025, Joshua Joseph Michael and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import json
from datetime import datetime, timedelta
from frappe.utils import get_url

@frappe.whitelist()
def get_list_data(filters=None, limit=20, offset=0):
    """
    Get paginated list data with filters
    """
    try:
        if isinstance(filters, str):
            filters = json.loads(filters)
        
        # Convert limit and offset to integers
        limit = int(limit)
        offset = int(offset)
        
        # Base query
        conditions = []
        values = {}
        
        if filters:
            if filters.get('status'):
                conditions.append("status = %(status)s")
                values['status'] = filters['status']
            
            if filters.get('date_range'):
                conditions.append("DATE(timestamp) BETWEEN %(from_date)s AND %(to_date)s")
                values['from_date'] = filters['date_range'][0]
                values['to_date'] = filters['date_range'][1]
            
            if filters.get('device_id'):
                conditions.append("device_id = %(device_id)s")
                values['device_id'] = filters['device_id']

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Get total count
        total_count = frappe.db.sql(
            f"""
            SELECT COUNT(*) as count
            FROM `tabBiometric Data Staging`
            WHERE {where_clause}
            """,
            values=values,
            as_dict=True
        )[0].get('count')

        # Get paginated data with proper parameter handling
        values.update({'start': offset, 'page_length': limit})
        data = frappe.db.sql(
            f"""
            SELECT 
                name,
                attendance_device_id,
                timestamp,
                punch_type,
                device_id,
                status,
                creation,
                modified
            FROM `tabBiometric Data Staging`
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %(page_length)s OFFSET %(start)s
            """,
            values=values,
            as_dict=True
        )

        return {
            'data': data,
            'total_count': total_count,
            'page_length': limit
        }

    except Exception as e:
        frappe.log_error(f"Error in get_list_data: {str(e)}", "Biometric List View Error")
        return {'error': str(e)}
    
@frappe.whitelist()
def bulk_process_records(records, action):
    """
    Process multiple records with specified action
    """
    if isinstance(records, str):
        records = json.loads(records)

    try:
        success_count = 0
        failed_count = 0
        
        # If no records provided but action is retry_sync, get all pending records
        if not records and action == 'retry_sync':
            records = [d.name for d in frappe.get_all("Biometric Data Staging", 
                                                     filters={"status": "Pending"})]

        for record in records:
            try:
                doc = frappe.get_doc("Biometric Data Staging", record)
                
                if action == "retry_sync":
                    # Handle both pending and failed records
                    if doc.status in ["Pending", "Failed", "Ignored"]:
                        # Trigger the sync process from the main module
                        from erpbiometric_sync.erpbiometric_sync.doctype.biometric_data_staging.biometric_data_staging import process_biometric_logs
                        process_biometric_logs(records=[doc.name])
                        success_count += 1
                
                elif action == "mark_processed":
                    if doc.status == "Pending":
                        doc.status = "Processed"
                        doc.save()
                        success_count += 1
                
                elif action == "mark_ignored":
                    doc.status = "Ignored"
                    doc.save()
                    success_count += 1
                
            except Exception as e:
                failed_count += 1
                frappe.log_error(
                    f"Error processing record {record}: {str(e)}",
                    "Bulk Process Error"
                )

        frappe.db.commit()
        
        return {
            'success': True,
            'message': f'Successfully processed {success_count} records. Failed: {failed_count}',
            'success_count': success_count,
            'failed_count': failed_count
        }

    except Exception as e:
        frappe.log_error( "Biometric List View Error", f"Bulk process error: {str(e)}")
        return {'error': str(e)}
    
@frappe.whitelist()
def get_sync_status_summary():
    """
    Get summary of sync status for dashboard
    """
    try:
        summary = frappe.db.sql("""
            SELECT 
                status,
                COUNT(*) as count,
                DATE(timestamp) as date
            FROM `tabBiometric Data Staging`
            WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY status, DATE(timestamp)
            ORDER BY DATE(timestamp) DESC
        """, as_dict=True)

        # Get device stats
        device_stats = frappe.db.sql("""
            SELECT 
                device_id,
                COUNT(*) as count,
                MAX(timestamp) as last_sync
            FROM `tabBiometric Data Staging`
            GROUP BY device_id
        """, as_dict=True)

        return {
            'status_summary': summary,
            'device_stats': device_stats
        }

    except Exception as e:
        frappe.log_error(f"Error getting sync summary: {str(e)}", "Biometric List View Error")
        return {'error': str(e)}

@frappe.whitelist()
def export_data(filters=None, file_format="CSV"):
    """
    Export filtered data to CSV/Excel
    """
    try:
        if isinstance(filters, str):
            filters = json.loads(filters)

        # Get data with filters but no pagination
        data = get_list_data(filters, limit=10000, offset=0)['data']
        
        if not data:
            return {'error': 'No data to export'}

        # Prepare for export
        from frappe.utils.xlsxutils import make_xlsx
        from frappe.utils import now
        
        xlsx_data = [
            ['Attendance Device ID', 'Timestamp', 'Punch Type', 'Device ID', 'Status', 'Created On']
        ]
        
        for row in data:
            xlsx_data.append([
                row.attendance_device_id,
                str(row.timestamp),
                row.punch_type,
                row.device_id,
                row.status,
                str(row.creation)
            ])

        # Generate Excel file
        xlsx_file = make_xlsx(xlsx_data, "Biometric Data Staging")
        
        # Save file in public files
        file_name = f'biometric_data_export_{now().replace(" ", "_")}.xlsx'
        file_url = save_file(file_name, xlsx_file, "Biometric Data Staging", is_private=0)
        
        return {
            'success': True,
            'file_url': file_url
        }

    except Exception as e:
        frappe.log_error(f"Export error: {str(e)}", "Biometric List View Error")
        return {'error': str(e)}

def save_file(fname, content, dt, dn=None, is_private=None, fieldname=None):
    """Save file to ERPNext"""
    from frappe.core.doctype.file.file import create_new_folder
    
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "attached_to_doctype": dt,
        "attached_to_name": dn,
        "content": content,
        "is_private": is_private
    })
    
    file_doc.save()
    return file_doc.file_url