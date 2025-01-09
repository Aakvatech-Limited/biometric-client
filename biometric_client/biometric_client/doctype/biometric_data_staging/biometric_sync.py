import frappe
from frappe.utils import now
from frappe import _

def synchronize_biometric_data():
    
    # Fetch "Pending" entries from Biometric Data Staging
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
            
            # Check if the punch type is valid
            valid_punch_types = ['IN', 'OUT', 'AUTO']
            if entry['punch_type'] not in valid_punch_types:
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
            checkin.insert()
            
            # Mark the staging record as processed
            frappe.db.set_value('Biometric Data Staging', entry['name'], {
                'status': 'Processed',
                
            })
        
        except Exception as e:
            frappe.log_error(message=str(e), title='Biometric Data Synchronization Error')
            frappe.db.set_value('Biometric Data Staging', entry['name'], {
                'status': 'Ignored',
                
            })
