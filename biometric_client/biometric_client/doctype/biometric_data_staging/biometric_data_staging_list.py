
# Copyright (c) 2025, Joshua Joseph Michael and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from datetime import datetime, timedelta

    
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

