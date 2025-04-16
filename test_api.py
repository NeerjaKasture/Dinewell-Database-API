import requests

BASE_URL = "http://localhost:5000"
session = requests.Session()

# Utility: Print response nicely
def print_response(response):
    print(f"URL: {response.url}")
    print(f"Status: {response.status_code}")
    try:
        print("Response:", response.json())
    except Exception:
        print("Raw Response:", response.text)
    print("-" * 50)


# =================== General APIs ==================

# 1. Login
def login(email, password):
    print("[*] Logging in...")
    res = session.post(f"{BASE_URL}/login", json={
        "email": email,
        "password": password
    })
    print_response(res)

# 2. Logout
def logout():
    print("[*] Logging out...")
    res = session.post(f"{BASE_URL}/logout")
    print_response(res)

# 3. Ping
def ping():
    print("[*] Pinging server...")
    res = session.get(f"{BASE_URL}/ping")
    print_response(res)

# 4. Check session validity
def is_valid_session():
    print("[*] Checking session validity...")
    # Get the session token from cookies
    token = session.cookies.get("session_token")
    res = session.get(f"{BASE_URL}/isValidSession", params={"session": token})
    print_response(res)


# ================= Admin APIs =================

# 1. View all users
def view_users():
    print("[*] Fetching users...")
    res = session.get(f"{BASE_URL}/admin/users")
    print_response(res)

# 2. Add new user
def add_user(username="TestUsr4", password="TestUsr@123", role="Student", email="testusr@dinewell.com", dob="2003-04-05", salary=500):
    print("[*] Adding new user...")
    res = session.post(f"{BASE_URL}/admin/addUser", json={
        "username": username,
        "password": password,
        "role": role,
        "email": email,
        "DoB": dob,
        salary: salary
    })
    print_response(res)

# 3. Delete user
def delete_user(email="testusr@dinewell.com"):
    print("[*] Deleting user...")
    res = session.delete(f"{BASE_URL}/admin/deleteUser", json={"email": email})
    print_response(res)

# 4. Remove expired inventory
def remove_expired_inventory():
    print("[*] Removing expired inventory...")
    res = session.put(f"{BASE_URL}/admin/inventory/remove_expired")
    print_response(res)

# 5. View salaries (admin)
def view_salaries():
    print("[*] Viewing employee salaries...")
    res = session.get(f"{BASE_URL}/admin/salaries")
    print_response(res)

# 6. Add employee salary
def add_employee_salary():
    print("[*] Adding employee salary...")
    data = {
        "MemberID": 2260,
        "SalaryPerDay": 500,
        "Month": "2025-04-01",
        "NoOfDays": 0,
    }
    res = session.post(f"{BASE_URL}/admin/add_salary", json=data)
    print_response(res)

# 7. View inventory
def view_inventory():
    print("[*] Viewing inventory...")
    res = session.get(f"{BASE_URL}/admin/inventory")
    print_response(res)

# 8. View vendors
def view_orders():
    print("[*] Viewing vendors...")
    res = session.get(f"{BASE_URL}/admin/orders")
    print_response(res)

# 9. Place vendor order
def place_vendor_order():
    print("[*] Adding new vendor...")
    data = {
        "ItemId": 1002,  # Existing ID
        "Vendorname": "Acme Supplies",
        "Vendor_contact_no": 9876543210,
        "Quantity_ordered": 50,
        "Unit": "kg",
        "TransactionID": 1111,
        "Product_name": "Wheat",
        "Min_quantity_req": 10,
        "Expiry_date": "2025-06-01",
        "Sender" : "Admin",
        "Date": "2025-04-10",
        "TotalCost": 5000,
    }
    res = session.post(f"{BASE_URL}/admin/place_order", json=data)
    print_response(res)

# 10. Update inventory quantity
def update_inventory_quantity(item_id=1002, quantity=50):
    print("[*] Updating inventory quantity...")
    res = session.put(f"{BASE_URL}/admin/inventory/update_quantity/{item_id}", json={"quantity": quantity})
    print_response(res)

# 11. Punch in
def punch_in(employee_id=1):
    print("[*] Punching in...")
    res = session.post(f"{BASE_URL}/admin/punch_in/{employee_id}", json={"month": "2025-04"})
    print_response(res)

# 12. Add income
def add_income():
    print("[*] Testing /admin/add_income")

    # Sample transaction data
    payload = {
        "Meal": "Lunch",
        "Amount": 10000,
        "TransactionID": 123456,  # Ensure this is unique or appropriate
        "Sender": "Student1",
        "Receiver": "Admin",
        "Date": "2025-04-15"
    }

    res = session.post(f"{BASE_URL}/admin/add_income", json=payload)
    print_response(res)

# 13. update utilities
def test_add_utility():
    print("[*] Testing utility addition...")

    url = f"{BASE_URL}/admin/add_utility"
    payload = {
        "Name": "Electricity Bill",
        "Amount": 200,
        "TransactionID": 12345678,  # Use a unique or test-safe TransactionID
        "Sender": "Admin001",
        "Receiver": "ElectricityDept",
        "Date": "2025-04-15"  # Use YYYY-MM-DD format
    }

    response = session.post(url, json=payload)
    print_response(response)

# 14. View revenue
def view_revenue():
    print("[*] Viewing revenue...")
    res = session.get(f"{BASE_URL}/admin/revenue")
    print_response(res)

# 15. View utilities
def view_utilities():
    print("[*] Viewing utilities...")
    res = session.get(f"{BASE_URL}/admin/list_utilities")
    print_response(res)

# 16. Get alerts
def get_alerts():
    print("[*] Fetching alerts...")
    res = session.get(f"{BASE_URL}/admin/alerts")
    print_response(res)




# ================ Employee APIs =================

# 1. Employee salary
def employee_salary():
    print("[*] Viewing employee salary...")
    res = session.get(f"{BASE_URL}/employee/salary")
    print_response(res)





# =========== Council Members APIs ===========

# 1. Update menu
def update_menu():
    print("[*] Updating menu...")
    res = session.put(f"{BASE_URL}/council/menu/update/lunch", json={
        "Month": "May",
        "Day": "Monday",
        "Salad": "Cucumber Tomato Salad",
        "Dal": "Toor Dal",
        "Vegetable": "Mixed Veg Curry",
        "Legume_Curry": "Chana Masala",
        "Rice_Side": "Jeera Rice",
        "Dairy_Product": "Curd",
        "Chapati": "Whole Wheat Chapati",
        "Pickle_Lemon": "Lemon Pickle",
        "Papad_Fryums": "Masala Papad"
    })
    print_response(res)

# 2. View Feedback
def view_feedback():
    print("[*] Viewing feedback...")
    res = session.get(f"{BASE_URL}/feedback")
    print_response(res)

# 3. View Complaints
def view_complaints():
    print("[*] Viewing complaints...")
    res = session.get(f"{BASE_URL}/complaint")
    print_response(res)






# ================= Common APIs ====================

# 1. View menu
def view_menu(meal_type="lunch"):
    print(f"[*] Viewing {meal_type} menu...")
    res = session.get(f"{BASE_URL}/menu/{meal_type}")
    print_response(res)

# 2. give feedback
def give_feedback():
    print("[*] Giving feedback...")
    res = session.post(f"{BASE_URL}/feedback", json={
        "feedback": "The food was delicious!"
    })
    print_response(res)

# 3. Raise complaint
def raise_complaint():
    print("[*] Raising complaint...")
    res = session.post(f"{BASE_URL}/complaint", json={
        "complaint": "The food was too spicy!"
    })
    print_response(res)







# =========== Role based tests ===========

def test_admin_apis() :
    login("admin@dinewell.com", "Admin@123")
    ping()
    is_valid_session()
    view_users()
    add_user()
    delete_user("testusr@dinewell.com")
    remove_expired_inventory()
    view_salaries()
    add_employee_salary()
    view_inventory()    
    view_orders()
    place_vendor_order()
    update_inventory_quantity(1002, 50)
    punch_in(2260)
    add_income()
    view_menu("lunch")
    test_add_utility()
    view_revenue()
    view_utilities()
    give_feedback()
    raise_complaint()
    get_alerts()
    logout()

def test_employee_apis() :
    login("employee1@dinewell.com", "Employee1@123")
    ping()
    is_valid_session()
    employee_salary()
    view_menu("lunch")
    logout()

def test_council_apis() :
    login("council@dinewell.com", "Council@123")
    ping()
    is_valid_session()
    update_menu()
    view_menu("lunch")
    logout()

def student_apis() :
    login("student1@dinewell.com", "Student1@123")
    ping()
    is_valid_session()
    view_menu("lunch")
    logout()




if __name__ == "__main__":
    print("================ Testing Admin APIs ========")
    test_admin_apis()
    print("\n\n================ Testing Employee APIs ========")
    test_employee_apis()
    print("\n\n================ Testing Council APIs ========")
    test_council_apis()
    print("\n\n================ Testing Student APIs ========")
    student_apis()


# login("admin@dinewell.com", "Admin@123")
# add_user(username="Employee3", password="Employee3@123", email="employee3@dinewell.com", role="Employee", dob="2003-04-05", salary=500)
# delete_user("employee3@dinewell.com")
# # test_add_utility()
# # view_revenue()
# # view_utilities()
# give_feedback()
# raise_complaint()
# logout()

# login("council@dinewell.com", "Council@123")
# view_feedback()
# view_complaints()
# logout()