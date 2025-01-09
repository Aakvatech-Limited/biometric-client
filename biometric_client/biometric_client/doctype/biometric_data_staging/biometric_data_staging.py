# Copyright (c) 2025, Asha Melius Kisonga and contributors
# For license information, please see license.txt


import frappe
from frappe.utils import now
from frappe import _
from frappe.model.document import Document

class BiometricDataStaging(Document):
    pass

def validate_biometric_data(doc, method):

    try:
        frappe.log_error(f"Validating Biometric Data for: {doc.name}", "Debug Log")
        
        # Mapping between Biometric Data Staging and Employee
        employee = frappe.db.get_value('Employee', {'attendance_device_id': doc.attendance_device_id}, 'name')
        
        if not employee:
            frappe.log_error(f"No employee found for attendance device ID: {doc.attendance_device_id}", "Debug Log")
            doc.status = "Ignored"
            return
        
        
        frappe.log_error(f"Employee {employee} found for device ID: {doc.attendance_device_id}", "Debug Log")
        
        # Check if there is a duplicate check-in record
        existing_checkin = frappe.db.exists('Employee Checkin', {
            'employee': employee,
            'time': doc.timestamp
        })
        
        if existing_checkin:
            frappe.log_error(f"Duplicate Check-in Detected: Employee {employee} at {doc.timestamp}", "Debug Log")
            doc.status = "Ignored"
            return
        
        # If validation passes, create an Employee Checkin record
        checkin = frappe.get_doc({
            'doctype': 'Employee Checkin',
            'employee': employee,
            'time': doc.timestamp,
            'log_type': doc.punch_type  
        })
        
        
        checkin.insert()
        
        # When sucessfully processed
        doc.status = "Processed"
        frappe.log_error(f"Check-in Processed for Employee: {employee} at {doc.timestamp}", "Debug Log")
        
    except Exception as e:
        frappe.log_error(f"Error during validation of Biometric Data for {doc.name}: {str(e)}", "Biometric Data Validation Error")
        doc.status = "Ignored"
        raise e  

    
    frappe.db.commit()
