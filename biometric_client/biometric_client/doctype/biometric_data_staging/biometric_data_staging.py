# Copyright (c) 2025, Asha Melius Kisonga and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import now
from datetime import datetime, timedelta
from frappe.model.document import Document

class BiometricDataStaging(Document):
    pass

@frappe.whitelist()
def biometric_logs():
    frappe.enqueue(
        'biometric_client.biometric_client.doctype.biometric_data_staging.biometric_data_staging.validate_biometric_data',
        queue='long',
        job_name='Validate Biometric Logs',
        timeout=300
    )
    return "Employee Checkin synchronization started."

def validate_biometric_data():
    """validation logic between Biometric Data Staging and Employee Checkin.
    to ensures data integrity by enforcing related rules during Doctype operations and sychronizing.

    """
    staging_entries = frappe.get_all(
        'Biometric Data Staging',
        filters={'status': 'Pending'},
        fields=['name', 'attendance_device_id', 'timestamp', 'device_id', 'punch_type']
    )

    for entry in staging_entries:
        try:
            employee = frappe.db.get_value('Employee', {'attendance_device_id': entry['attendance_device_id']}, 'name')
            
            if not employee:
                frappe.db.set_value('Biometric Data Staging', entry['name'], {
                    'status': 'Ignored',
                    
                })
                continue
            # Check for duplicate check-in record
            existing_checkin = frappe.db.exists('Employee Checkin', {
                'employee': employee,
                'time': entry['timestamp']
            })
            
            if existing_checkin:
                frappe.db.set_value('Biometric Data Staging', entry['name'], {
                    'status': 'Ignored',
                    
                })
                continue


            # Create a new Employee Checkin record
            checkin = frappe.get_doc({
                'doctype': 'Employee Checkin',
                'employee': employee,
                'time': entry['timestamp'],
                'log_type': entry['punch_type']
            })
            checkin.insert(ignore_permissions=True)
            
            # Mark the staging record as processed
            frappe.db.set_value('Biometric Data Staging', entry['name'], {
                'status': 'Processed',
                
            })
        
        except Exception as e:
            frappe.log_error(message=str(e), title='Biometric Data Synchronization Error')
            frappe.db.set_value('Biometric Data Staging', entry['name'], {
                'status': 'Ignored',
                
            })

@frappe.whitelist()
def get_sync_status_summary():
    """
    Get summary of sync status for dashboard with detailed logs since last sync
    """
    try:
        # Get 7-day summary for specific statuses
        summary = frappe.db.sql("""
            SELECT 
                status,
                COUNT(*) as count,
                DATE(timestamp) as date
            FROM `tabBiometric Data Staging`
            WHERE 
                timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                AND status IN ('Processed', 'Pending', 'Ignored')
            GROUP BY status, DATE(timestamp)
            ORDER BY DATE(timestamp) DESC
        """, as_dict=True)

        # Get device stats with total records and last sync
        device_stats = frappe.db.sql("""
            SELECT 
                device_id,
                COUNT(*) as total_count,
                MAX(timestamp) as last_sync
            FROM `tabBiometric Data Staging`
            GROUP BY device_id
        """, as_dict=True)

        # Get status counts for each device
        for device in device_stats:
            status_details = frappe.db.sql("""
                SELECT 
                    status,
                    COUNT(*) as status_count
                FROM `tabBiometric Data Staging`
                WHERE 
                    device_id = %s
                    AND status IN ('Processed', 'Pending', 'Ignored')
                GROUP BY status
            """, (device.device_id), as_dict=True)
            device['status_details'] = status_details
            device['count'] = device.total_count

        # Get counts since last sync
        last_sync_time = frappe.db.sql("""
            SELECT MAX(timestamp) as last_sync
            FROM `tabBiometric Data Staging`
        """, as_dict=True)[0].last_sync

        if last_sync_time:
            last_sync_summary = frappe.db.sql("""
                SELECT 
                    status,
                    COUNT(*) as count
                FROM `tabBiometric Data Staging`
                WHERE 
                    timestamp = %s
                    AND status IN ('Processed', 'Pending', 'Ignored')
                GROUP BY status
            """, (last_sync_time), as_dict=True)
        else:
            last_sync_summary = []

        return {
            'status_summary': summary,
            'device_stats': device_stats,
            'last_sync_summary': last_sync_summary
        }
    except Exception as e:
        frappe.log_error(f"Error getting sync summary: {str(e)}", "Biometric List View Error")
        return {'error': str(e)}