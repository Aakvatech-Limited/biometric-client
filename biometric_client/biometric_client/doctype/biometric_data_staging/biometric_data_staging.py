# Copyright (c) 2025, Asha Melius Kisonga and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import now
#from frappe import _
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



            
   
   