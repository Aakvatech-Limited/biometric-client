# -*- coding: utf-8 -*-
# Copyright (c) 2025, Aakvatech and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
import requests
from requests.exceptions import Timeout
import json
from frappe.utils import today, get_datetime, add_to_date, getdate
from time import sleep
from datetime import datetime


class BiometricClientSettings(Document):
	pass


def get_url():
	if frappe.db.get_value("Biometric Client Settings", None, "server_url"):
		url = frappe.db.get_value("Biometric Client Settings", None, "server_url")
		return url
	else:
		frappe.throw(_("Please set server URL"))

def get_bio_token():
	if frappe.db.get_value("Biometric Client Settings", None, "bio_token"):
		bio_token = frappe.db.get_value("Biometric Client Settings", None, "bio_token")
		return bio_token
	else:
		frappe.throw(_("Please make sure you have Bio Token"))

def get_headers():
	headers = {'Authorization': "Token " +  get_bio_token()}
	return headers

def get_user_name():
	if frappe.db.get_value("Biometric Client Settings", None, "user_name"):
		user_name = frappe.db.get_value("Biometric Client Settings", None, "user_name")
		return user_name
	else:
		frappe.throw(_("Please set User Name"))

def get_password():
	if frappe.db.get_value("Biometric Client Settings", None, "password"):
		password = frappe.db.get_value("Biometric Client Settings", None, "password")
		return password
	else:
		frappe.throw(_("Please set Password"))

def get_default_shift_type():
	if frappe.db.get_value("Biometric Client Settings", None, "default_shift_type"):
		default_shift_type = frappe.db.get_value("Biometric Client Settings", None, "default_shift_type")
		return default_shift_type
	else:
		frappe.throw(_("Please set the Default Shift Type"))

def get_employee_default_shift(employee_name= None):
	if not employee_name:
		return
	else:
		if frappe.db.get_value("Employee", employee_name, "default_shift"):
			default_shift_type = frappe.db.get_value("Employee", employee_name, "default_shift")
			return default_shift_type

def get_shift_type(employee_name=None):
	if not employee_name:
		get_default_shift_type()
	else:
		if get_employee_default_shift(employee_name):
			return get_employee_default_shift(employee_name)
		else:
			return get_default_shift_type()


def get_department():
	if frappe.db.get_value("Biometric Client Settings", None, "department"):
		department = frappe.db.get_value("Biometric Client Settings", None, "department")
		if department == 0:
			frappe.throw(_("Please set Default Department Code Other than 0"))
		else:
			return department
	else:
		frappe.throw(_("Please set Default Department Code"))

def get_area_code():
	if frappe.db.get_value("Biometric Client Settings", None, "area_code"):
		area_code = [frappe.db.get_value("Biometric Client Settings", None, "area_code")]
		if area_code == [0] :
			frappe.throw(_("Please set Default Area Code Other than 0"))
		else:
			return area_code
	else:
		frappe.throw(_("Please set Default Area Code"))

def get_employee_name_id(id):
	if id :
		employee_name_list = frappe.db.sql_list("""select name from `tabEmployee`
			where biometric_id=%s """, (id))
		if employee_name_list:
			employee_name = employee_name_list[0]
			return employee_name
	else:
		frappe.throw(_("No employee has this identity: ") + str(id))


def check_master_enable():
	enable_biometric_master = frappe.db.get_value("Biometric Client Settings", None, "enable_biometric_master") or 0
	if int(enable_biometric_master) == 1:
		return True
	else:
		return False


def check_employee_enable(emp):
    if frappe.db.get_value("Employee", emp, "enable_biometric"):
        enable_biometric = frappe.db.get_value("Employee", emp, "enable_biometric") 
        if int(enable_biometric) == 1:
            return True
        else:
            return False
    else:
        return False


@frappe.whitelist()
def auto_shift_assignment_for_active_today():
	if check_master_enable():
		auto_shift = frappe.db.get_value("Biometric Client Settings", None, "auto_shift")
		if int(auto_shift) == 1:
			creat_shift_assignment_for_active_today()


@frappe.whitelist()
def auto_make_employee_checkin():
	if check_master_enable():
		auto_checkin = frappe.db.get_value("Biometric Client Settings", None, "auto_checkin")
		if int(auto_checkin) == 1:
			make_employee_checkin()


@frappe.whitelist()
def auto_get_transactions():
	if check_master_enable():
		auto_transactions = frappe.db.get_value("Biometric Client Settings", None, "auto_transactions")
		if int(auto_transactions) == 1:
			get_transactions()



@frappe.whitelist()
def get_new_bio_token():
	url = get_url() + "/api-token-auth/"
	data  = {
			"username": get_user_name(),
    		"password": get_password()
			} 
	response = requests.post(url = url, data = data)
	if response.status_code == 200 :
		res = json.loads(response.text)
		bio_token = res["token"]
		return bio_token
	else:
		frappe.throw(_("Please double check your username, password and URL"))


@frappe.whitelist()
def check_employee_bio_info(doc, method):
	if check_master_enable() and check_employee_enable(doc.name):
		if doc.company:
				abbr = frappe.get_cached_value('Company',  doc.company,  'abbr')
		if doc.name :
			emp_code = abbr + "-" + doc.name
			if doc.biometric_id:
				biometric_id = doc.biometric_id
				url = get_url() + "/personnel/api/employees/" + biometric_id +"/"
				try:
					response = requests.get(url = url, headers = get_headers(), timeout=5)
				except Timeout:
					frappe.msgprint(_("Error Please check Biotime server Request timeout"))
				else:
					if response.status_code == 200 :
						res = json.loads(response.text)
						emp_id = str(res["id"])
						doc.biometric_id = emp_id
						if not doc.biometric_code:
							doc.biometric_code = str(res["emp_code"])
						if not doc.area:
							for area_item in res["area"]:
								area_row = doc.append('area',{})
								area_row.area = area_item['area_name']
								area_row.area_code = area_item['area_code']
						update_employee_bio(doc,emp_id)
					else:
						add_employee_bio(doc,emp_code)
			else:
				add_employee_bio(doc,emp_code)


def add_employee_bio(doc,emp_code):
	if doc.name :
		if doc.area:
			area = []
			for row in doc.area:
				area_row = row.area_code
				area.append(area_row)
		else:
			area = get_area_code()
		url = get_url() + "/personnel/api/employees/"
		data  ={
				"emp_code": emp_code,
				"first_name": doc.employee_name,
				"area": area,
				"department": get_department()
				}
		try:
			response = requests.post(url = url, headers = get_headers(), data = data, timeout = 5)
		except Timeout:
			frappe.msgprint(_("Error Please check Biotime server Request timeout"))
		else:	
			if response.status_code == 200 or response.status_code == 201 :
				res = json.loads(response.text)
				first_name = res["first_name"]
				emp_id = res["id"]
				doc.biometric_id = emp_id
				doc.biometric_code = emp_code
				frappe.msgprint(_("Creatin Employee biometric ") + str(emp_code))
				return emp_id
			else:
				frappe.throw(_("Error Creating Employee biometric "))

def update_employee_bio(doc,emp_id):
	if doc.name :
		if doc.area:
			area = []
			for row in doc.area:
				area_row = row.area_code
				area.append(area_row)
		else:
			area = get_area_code()
		url = get_url() + "/personnel/api/employees/" + emp_id +"/"
		data  ={
				"first_name": doc.employee_name,
				"emp_code": doc.biometric_code,
				"area": area,
				"department": get_department()
				}
		try:
			response = requests.patch(url = url, headers = get_headers(), data = data, timeout=5)
		except Timeout:
			frappe.msgprint(_("Error Please check Biotime server Request timeout"))
		else:	
			if response.status_code == 200 :
				return emp_id
			else:
				frappe.throw(_("Error Updating Employee biometric info ") +emp_id)

def check_transactions_id_is_unique(id):
		if id :
			names = frappe.db.sql_list("""select name from `tabTransactions Log`
				where id=%s """, (id))
			if names:
				return False
			else:
				return True

def update_default_shift_type_last_sync(name,datetime):
	frappe.db.set_value("Shift Type", name, "last_sync_of_checkin", datetime)

@frappe.whitelist()
def get_transactions(start_time=None, end_time=None):
    if check_master_enable():
        if not start_time:
            start_time = today()
        if not end_time:
            end_time = str(get_datetime())
        if str(get_datetime(start_time)) == end_time:
            start_time = add_to_date(start_time, days=-1)

        space = "\n" * 2
        tf_log_name = creat_transaction_fetch_log(start_time, end_time)
        start = "start_time=" + start_time
        end = "end_time=" + end_time
        url = get_url() + "/iclock/api/transactions/?" + start + "&" + end

        try:
            response = requests.get(url=url, headers=get_headers(), timeout=5)
        except Timeout:
            tf_log_doc = frappe.get_doc("Transaction Fetch Log", tf_log_name)
            tf_log_doc.status = "Error"
            if not tf_log_doc.log:
                tf_log_doc.log = ""
            tf_log_doc.log = tf_log_doc.log + space + str("Timeout Error")
            tf_log_doc.save()
            return {"status": "Error", "message": "Timeout Error"}
        else:
            if response.status_code == 200:
                res = json.loads(response.text)
                count = res["count"]
                transactions_data = res["data"]
                get_transaction_pages(count, start_time, end_time, tf_log_name)
                tf_log_doc = frappe.get_doc("Transaction Fetch Log", tf_log_name)
                tf_log_doc.status = "Success"
                tf_log_doc.save()
                return {
                    "status": "Success",
                    "message": "Transactions fetched successfully",
                    "transactions": transactions_data
                }
            else:
                tf_log_doc = frappe.get_doc("Transaction Fetch Log", tf_log_name)
                tf_log_doc.status = "Error"
                res = json.loads(response.text)
                if not tf_log_doc.log:
                    tf_log_doc.log = ""
                tf_log_doc.log = tf_log_doc.log + space + str(res)
                tf_log_doc.save()
                return {"status": "Error", "message": "Error fetching transactions", "details": res}


def get_transaction_pages(start_time, end_time, tf_log_name):
    unique_list = []
    repeated_list = []
    space = "\n" * 2
    tf_log_doc = frappe.get_doc("Transaction Fetch Log", tf_log_name)

    page_size = 50  # Adjust page size as per API capability
    next_url = f"{get_url()}/iclock/api/transactions/?start_time={start_time}&end_time={end_time}&page_size={page_size}"
    while next_url:
        response = requests.get(url=next_url, headers=get_headers())
        if response.status_code == 200:
            res = json.loads(response.text)
            data = res.get("data", [])
            creat_transaction_log(data, tf_log_name, unique_list, repeated_list)
            next_url = res.get("next")  # Handle `next` for pagination
        else:
            res = json.loads(response.text)
            tf_log_doc.status = "Error"
            if not tf_log_doc.log:
                tf_log_doc.log = ""
            tf_log_doc.log = tf_log_doc.log + space + str(res)
            tf_log_doc.save()
            next_url = None  # Exit loop on error

    tf_log_doc.log = (tf_log_doc.log or "") + space + "Unique Record IDs: " + str(unique_list)
    tf_log_doc.log += space + "Repeated Record IDs: " + str(repeated_list)
    tf_log_doc.save()


def creat_transaction_fetch_log(start_time,end_time,times=None,count=None):
	transaction_fetch_log_doc = frappe.get_doc(dict(
			doctype = "Transaction Fetch Log",
			start_time = start_time,
			end_time = end_time,
			count = count,
			page = times,
		)).insert(ignore_permissions = True)
	if transaction_fetch_log_doc:
		frappe.flags.ignore_account_permission = True
		update_default_shift_type_last_sync(get_default_shift_type(),end_time)
		return transaction_fetch_log_doc.name


def creat_shift_assignment_for_active_today():
	active_emp_list = frappe.db.sql_list("""select name from `tabEmployee`
				where status=%s """, "Active")
	if active_emp_list:
		for emp in active_emp_list:
			if check_employee_enable(emp):
				if frappe.db.get_value("Employee", emp, "biometric_id"):
					date = today()
					shift_type = get_shift_type(emp)
					creat_shift_assignment(emp,date,shift_type)


def creat_shift_assignment(emp_id,date,shift_type):
	name = "New Shift Assignment"
	d = frappe.db.sql("""
				select name
				from `tabShift Assignment`
				where employee = %(employee)s and docstatus < 2
				and date = %(date)s
				and name != %(name)s""", {
					"employee": emp_id,
					"shift_type": shift_type,
					"date": date,
					"name": name
				}, as_dict = 1)
	for date_overlap in d:
		if date_overlap['name']:
			return

	shift_assignment_doc = frappe.get_doc(dict(
			doctype = "Shift Assignment",
			employee = emp_id,
			shift_type = shift_type,
			date = date,
		)).insert(ignore_permissions = True)
	if shift_assignment_doc:
		frappe.flags.ignore_account_permission = True
		shift_assignment_doc.submit()
		return shift_assignment_doc.name

def creat_transaction_log(data,tf_log_name,unique_list,repeated_list):
	tf_log_doc = frappe.get_doc("Transaction Fetch Log",tf_log_name)
	if tf_log_doc.unique:
		unique = int(tf_log_doc.unique)
	else:
		unique = 0
	if tf_log_doc.repeated:
		repeated = int(tf_log_doc.repeated)
	else:
		repeated = 0
	
	for transaction_row in data:
		if check_transactions_id_is_unique(transaction_row["id"]):
			unique += 1
			unique_list.append(transaction_row["id"])
			if not transaction_row["id"] or not transaction_row["punch_time"] or not transaction_row["punch_state"] or not transaction_row["emp"]:
				status = "Error"
			else:
				status = "Waiting"
			transaction_log_doc = frappe.get_doc(dict(
				doctype="Transactions Log",
				id=transaction_row.get("id"),
				emp_code=transaction_row.get("emp_code"),
				punch_time=transaction_row.get("punch_time"),
				punch_state=transaction_row.get("punch_state"),
				verify_type=transaction_row.get("verify_type"),
				work_code=transaction_row.get("work_code"),
				terminal_sn=transaction_row.get("terminal_sn"),
				terminal_alias=transaction_row.get("terminal_alias"),
				area_alias=transaction_row.get("area_alias"),
				ilongituded=transaction_row.get("longitude"),  
				latitude=transaction_row.get("latitude"),    
				gps_location=transaction_row.get("gps_location"),
				mobile=transaction_row.get("mobile"),
				source=transaction_row.get("source"),
				purpose=transaction_row.get("purpose"),
				crc=transaction_row.get("crc"),
				is_attendance=transaction_row.get("is_attendance"),
				reserved=transaction_row.get("reserved"),
				upload_time=transaction_row.get("upload_time"),
				sync_status=transaction_row.get("sync_status"),
				sync_statusid=transaction_row.get("sync_status"),
				sync_time=transaction_row.get("sync_time"),
				emp=transaction_row.get("emp"),
				terminal=transaction_row.get("terminal"),
				transaction_fetch_log=tf_log_name,
				status=status,
			)).insert(ignore_permissions=True)

			if transaction_log_doc:
				frappe.flags.ignore_account_permission = True

		else:
			repeated_list.append(transaction_row["id"])
			repeated += 1
	
	tf_log_doc.unique = unique
	tf_log_doc.repeated = repeated
	tf_log_doc.save()


@frappe.whitelist()
def make_employee_checkin():
	if check_master_enable():
		transactions_log_list = frappe.db.sql_list("""select name from `tabTransactions Log`
					where status=%s """, "Waiting")
		for transaction_item in transactions_log_list:
			transaction_doc = frappe.get_doc("Transactions Log",transaction_item)
			if get_employee_name_id(transaction_doc.emp):
				employee_name_id = get_employee_name_id(transaction_doc.emp)
				if check_employee_enable(employee_name_id):
					shift = get_shift_type(employee_name_id)
					punch_date =getdate(transaction_doc.punch_time)
					creat_shift_assignment(employee_name_id,punch_date,get_default_shift_type())
					if int(transaction_doc.punch_state) == 0 :
						log_type = "IN"
					else:
						log_type = "OUT"
					employee_checkin_doc = frappe.get_doc(dict(
						doctype = "Employee Checkin",
						employee = employee_name_id,
						log_type = log_type,
						time = transaction_doc.punch_time,
						device_id = transaction_doc.terminal_alias,
						shift = shift,
					)).insert(ignore_permissions = True)
					if employee_checkin_doc:
						frappe.flags.ignore_account_permission = True
						transaction_doc.employee_checkin = employee_checkin_doc.name
						transaction_doc.status = "Linked"
						transaction_doc.save()
		return "Success"
		

@frappe.whitelist()
def create_attendance_automated():
    """Enqueue attendance creation as a background job."""
    frappe.enqueue("biometric_client.biometric_client.doctype.biometric_client_settings.biometric_client_settings.process_attendance_in_background",
                   queue='long', timeout=3600)
    return "Attendance synchronization has started in the background."

def fetch_transactions_with_retries(url, retries=5, backoff_factor=2):
    """Fetch transactions with retries and exponential backoff."""
    attempt = 1
    while attempt <= retries:
        try:
            response = requests.get(url, headers=get_headers(), timeout=60)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, dict) or 'data' not in data:
                raise ValueError("Invalid response format")
                
            return data
        except requests.exceptions.RequestException as e:
            if attempt == retries:
                raise e
            sleep_time = backoff_factor ** attempt
            frappe.log_error("API Timeout", f"Retry {attempt}/{retries} - Error: {str(e)}")
            sleep(sleep_time)
            attempt += 1
    return {}

def get_shift_type(employee, attendance_date):
    """
    Get shift type for employee on given date.
    First checks shift assignment, then falls back to default shift.
    Returns tuple of (shift_type, source) where source is either 'assignment' or 'default'
    """
    # First check shift assignment
    assigned_shift = frappe.db.get_value(
        "Shift Assignment",
        {
            "employee": employee,
            "start_date": ["<=", attendance_date],
            "end_date": [">=", attendance_date]
        },
        "shift_type"
    )
    
    if assigned_shift:
        return assigned_shift, 'assignment'
        
    # If no assignment found, check default shift
    default_shift = frappe.db.get_value("Employee", employee, "default_shift")
    if default_shift:
        return default_shift, 'default'
        
    return None, None

def create_attendance_record(employee_id, attendance_date, status):
    """Create or update attendance record using assigned shift or default shift."""
    try:
        # Check for shift assignment or default shift
        shift, shift_source = get_shift_type(employee_id, attendance_date)
        if not shift:
            frappe.log_error(
                "No Shift Found",
                f"No shift assignment or default shift found for employee {employee_id} on {attendance_date}. Attendance not marked."
            )
            return False

        # Proceed with attendance creation
        existing_attendance = frappe.db.exists("Attendance", {
            "employee": employee_id,
            "attendance_date": attendance_date
        })

        if existing_attendance:
            # Update existing record if not submitted
            attendance_doc = frappe.get_doc("Attendance", existing_attendance)
            if attendance_doc.docstatus == 1:  # Skip if already submitted
                return True
                
            attendance_doc.status = status
            attendance_doc.shift = shift
            attendance_doc.save(ignore_permissions=True)
            
        else:
            # Create new attendance record
            company = frappe.db.get_value("Employee", employee_id, "company")
            attendance_doc = frappe.get_doc({
                "doctype": "Attendance",
                "employee": employee_id,
                "attendance_date": attendance_date,
                "status": status,
                "company": company,
                "shift": shift
            })
            attendance_doc.insert(ignore_permissions=True)
            attendance_doc.submit()
            
        # Log the shift source used
        frappe.log_error(
            "Attendance Created",
            f"Attendance marked for employee {employee_id} on {attendance_date} using {shift_source} shift: {shift}"
        )
        return True
            
    except Exception as e:
        frappe.log_error(
            "Attendance Creation Error",
            f"Error creating attendance for {employee_id} on {attendance_date}: {str(e)}"
        )
        return False

def process_attendance_in_background():
    """Fetch and process attendance data, creating records based on shifts."""
    if not check_master_enable():
        frappe.log_error("Automated Attendance", "Biometric integration is disabled in settings")
        return

    # Get department ID
    department_name = "WASCO ISOAF Tanzania Limited"
    department_id = get_department_id(department_name)
    if not department_id:
        frappe.log_error("Department not found", f"Department '{department_name}' not found")
        return

    # Get start time
    start_time = frappe.db.get_value("Biometric Client Settings", None, "last_sync_time") or \
                frappe.db.get_value("Biometric Client Settings", None, "start_time")
    if not start_time:
        frappe.log_error("Automated Attendance", "Start time is not defined in Biometric Client Settings")
        return

    end_time = str(get_datetime())
    latest_punch_time = start_time
    
    # Initialize counters
    page_size = 100
    page = 1
    processed_count = 0
    skipped_count = 0
    error_count = 0

    while True:
        try:
            url = (f"{get_url()}/iclock/api/transactions/"
                  f"?start_time={start_time}&end_time={end_time}"
                  f"&department_id={department_id}&page={page}&page_size={page_size}")

            response = fetch_transactions_with_retries(url)
            transactions = response.get("data", [])
            
            if not transactions:
                break

            # Process each transaction
            for transaction in transactions:
                try:
                    biometric_id = transaction.get("emp_code")
                    punch_time = transaction.get("punch_time")
                    
                    if not biometric_id or not punch_time:
                        continue

                    employee_id = frappe.db.get_value("Employee", 
                                                    {"biometric_id": biometric_id}, 
                                                    "name")
                    if not employee_id:
                        continue

                    attendance_date = getdate(punch_time)
                    
                    # Try to create attendance record
                    if create_attendance_record(
                        employee_id=employee_id,
                        attendance_date=attendance_date,
                        status="Present"
                    ):
                        processed_count += 1
                    else:
                        skipped_count += 1

                    # Update latest punch time
                    if punch_time > latest_punch_time:
                        latest_punch_time = punch_time

                except Exception as e:
                    error_count += 1
                    frappe.log_error("Transaction Processing Error", 
                                   f"Error processing transaction: {transaction}, Error: {str(e)}")
                    continue

            if not response.get("next"):
                break
                
            page += 1

        except Exception as e:
            frappe.log_error("Pagination Error", 
                           f"Error during pagination: {str(e)}. Last processed page: {page-1}")
            break

    # Update last sync time
    try:
        frappe.db.set_value("Biometric Client Settings", None, "last_sync_time", latest_punch_time)
        frappe.db.commit()
    except Exception as e:
        frappe.log_error("Sync Time Update Error", f"Error updating last_sync_time: {str(e)}")

    # Log summary
    frappe.log_error("Processing Summary", 
                    f"Processed {processed_count} attendance records, "
                    f"Skipped {skipped_count} records due to missing shifts, "
                    f"Encountered {error_count} errors. "
                    f"New last_sync_time: {latest_punch_time}")


def get_department_id(department_name):
    """Fetch department ID by department name from ZKBioTime with pagination."""
    url = f"{get_url()}/personnel/api/departments/"
    try:
        while url:  # Handle pagination
            response = requests.get(url=url, headers=get_headers(), timeout=10)
            response.raise_for_status()
            res = response.json()
            departments = res.get("data", [])

            # Search for the department ID in the current page
            for department in departments:
                if department.get("dept_name") == department_name:
                    return department.get("id")

            # Move to the next page, if available
            url = res.get("next")

        # If the loop completes and no department is found
        frappe.log_error("Department Fetch Error", f"Department '{department_name}' not found")
        return None
    except requests.RequestException as e:
        frappe.log_error("Department Fetch Error", f"Error fetching departments: {str(e)}")
        return None


@frappe.whitelist()
def fetch_departments():
    """Fetch list of all departments from ZKBioTime API with pagination."""
    url = f"{get_url()}/personnel/api/departments/"
    all_departments = []

    try:
        while url:
            response = requests.get(url=url, headers=get_headers(), timeout=10)
            response.raise_for_status()
            res = response.json()

            # Append data from the current page
            all_departments.extend(res.get("data", []))

            # Update URL for the next page if available
            url = res.get("next")

        return all_departments
    except requests.RequestException as e:
        frappe.log_error("Fetch Departments Error", f"Error fetching departments: {str(e)}")
        return []

@frappe.whitelist()
def fetch_employees_by_department(department_name):
    """Fetch all employees from a specific department by name with pagination."""
    department_id = get_department_id(department_name)
    if not department_id:
        frappe.throw(f"Department '{department_name}' not found")

    url = f"{get_url()}/personnel/api/employees/?department_id={department_id}"
    all_employees = []

    try:
        while url:  # Handle pagination
            response = requests.get(url=url, headers=get_headers(), timeout=10)
            response.raise_for_status()
            res = response.json()
            employees = res.get("data", [])

            # Append employees from the current page
            all_employees.extend(employees)

            # Update the URL for the next page, if available
            url = res.get("next")

        return all_employees
    except requests.RequestException as e:
        frappe.log_error("Fetch Employees Error", f"Error fetching employees: {str(e)}")
        return []

def setup_scheduled_job_type():
    """Create or update the scheduled job for attendance synchronization"""
    job = frappe.get_doc({
        "doctype": "Scheduled Job Type",
        "method": "biometric_client.biometric_client.doctype.biometric_client_settings.biometric_client_settings.create_attendance_automated",
        "frequency": "Daily",
        "start_time": "01:00:00",  # Run at 1 AM
        "docstatus": 0,
        "name": "Daily Attendance Record Sync",
        "document_type": "Attendance",
        "status": "Active",
        "enabled": 1,
        "create_log": 1
    })
    
    try:
        existing_job = frappe.get_doc("Scheduled Job Type", "Daily Attendance Record Sync")
        existing_job.update(job)
        existing_job.save()
        frappe.db.commit()
        print("Updated existing scheduled job for attendance synchronization")
    except frappe.DoesNotExistError:
        job.insert()
        frappe.db.commit()
        print("Created new scheduled job for attendance synchronization")

def execute_scheduled_job():
    """Wrapper function to handle scheduled job execution"""
    try:
        create_attendance_automated()
    except Exception as e:
        frappe.log_error(
			"Scheduled Job Error",
            f"Error in scheduled attendance synchronization: {str(e)}"
        )
        raise

@frappe.whitelist()
def fetch_transaction_report(start_date, end_date, page=1, page_size=100, department="WASCO ISOAF Tanzania Limited", area=None):
    """Fetch transaction report from ZKBioTime API."""
    base_url = f"{get_url()}/att/api/transactionReport/"
    headers = get_headers()
    
    # Get department ID for the provided department name (case-sensitive)
    department_id = get_department_id_case_sensitive(department)
    if not department_id:
        frappe.throw(f"Department '{department}' not found in Biotime (case-sensitive).")

    params = {
        "start_date": start_date,
        "end_date": end_date,
        "departments": department_id,
        "areas": area or "",
        "page": page,
        "page_size": page_size
    }
    
    employee_punches = {}  # Group punches by employee and date

    try:
        while True:
            response = requests.get(url=base_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract records
            records = data.get("data", [])
            if not records:
                frappe.msgprint("No transactions found for the given parameters.")
                break

            for record in records:
                emp_code = record.get("emp_code")
                punch_time = record.get("punch_time")
                att_date = record.get("att_date")

                if emp_code and punch_time and att_date:
                    key = (emp_code, att_date)
                    if key not in employee_punches:
                        employee_punches[key] = {
                            "emp_code": emp_code,
                            "att_date": att_date,
                            "dept_name": record.get("dept_name"),
                            "first_name": record.get("first_name"),
                            "last_name": record.get("last_name"),
                            "punch_times": []
                        }
                    employee_punches[key]["punch_times"].append(punch_time)

            if not data.get("next"):
                break
            params["page"] += 1

        # Calculate worked hours and format the results
        all_records = []
        for key, value in employee_punches.items():
            punch_times = sorted(value["punch_times"])  # Sort times for the day
            if len(punch_times) >= 2:
                in_time = get_datetime(f"{value['att_date']} {punch_times[0]}")
                out_time = get_datetime(f"{value['att_date']} {punch_times[-1]}")
                worked_hours = (out_time - in_time).total_seconds() / 3600
            else:
                worked_hours = 0

            all_records.append({
                "emp_code": value["emp_code"],
                "att_date": value["att_date"],
                "dept_name": value["dept_name"],
                "first_name": value["first_name"],
                "last_name": value["last_name"],
                "in_time": punch_times[0] if punch_times else None,
                "out_time": punch_times[-1] if punch_times else None,
                "worked_hours": round(worked_hours, 2)
            })

        return all_records

    except requests.exceptions.RequestException as e:
        frappe.log_error("Transaction Report Fetch Error", f"Error fetching transaction report: {str(e)}")
        return {"error": str(e)}

def get_department_id_case_sensitive(department_name):
    """Fetch department ID by department name with case sensitivity from ZKBioTime API."""
    url = f"{get_url()}/personnel/api/departments/"
    try:
        while url:
            response = requests.get(url=url, headers=get_headers(), timeout=10)
            response.raise_for_status()
            res = response.json()

            for department in res.get("data", []):
                # Ensure case-sensitive match
                if department.get("dept_name") == department_name:
                    return department.get("id")
            
            url = res.get("next")

        frappe.log_error("Department Fetch Error", f"Department '{department_name}' not found (case-sensitive)")
        return None

    except requests.RequestException as e:
        frappe.log_error("Fetch Departments Error", f"Error fetching departments: {str(e)}")
        return None
