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
def add_user(username="TestUsr4", password="TestUsr@123", role="Student", email="testusr@dinewell.com", dob="2003-04-05"):
    print("[*] Adding new user...")
    res = session.post(f"{BASE_URL}/admin/addUser", json={
        "username": username,
        "password": password,
        "role": role,
        "email": email,
        "DoB": dob
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
    res = session.delete(f"{BASE_URL}/admin/inventory/remove_expired")
    print_response(res)

# 5. View salaries (admin)
def view_salaries():
    print("[*] Viewing employee salaries...")
    res = session.get(f"{BASE_URL}/admin/salaries")
    print_response(res)

# 6. Update revenue
def update_revenue():
    print("[*] Updating revenue...")
    data = {
        "Inventory": 1000,
        "Payment": 2000,
        "Salary": 3000,
        "TotalExpense": 6000,
        "TotalRevenue": 8000,
        "Utilities": 500,
        "Month": "2025-04-10"
    }
    res = session.put(f"{BASE_URL}/admin/revenue_update", json=data)
    print_response(res)

# 7. View inventory
def view_inventory():
    print("[*] Viewing inventory...")
    res = session.get(f"{BASE_URL}/admin/inventory")
    print_response(res)

# 8. View vendors
def view_vendors():
    print("[*] Viewing vendors...")
    res = session.get(f"{BASE_URL}/admin/vendors")
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

# 10 Delete item from inventory
def delete_item_from_inventory():
    print("[*] Deleting item from inventory...")
    res = session.delete(f"{BASE_URL}/admin/inventory/delete_item", json={"ItemId": 1002})
    print_response(res)
    
# 6. View menu
def view_menu(meal_type="lunch"):
    print(f"[*] Viewing {meal_type} menu...")
    res = session.get(f"{BASE_URL}/menu/{meal_type}")
    print_response(res)








# 14. Employee salary (as employee)
def employee_salary():
    print("[*] Viewing employee salary...")
    res = session.get(f"{BASE_URL}/employee/salary")
    print_response(res)



# 16. DB connection check
def dbcon():
    print("[*] Checking DB connection...")
    res = session.get(f"{BASE_URL}/dbcon")
    print_response(res)






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

def punch_in():
    print("[*] Punching in...")
    res = session.post(f"{BASE_URL}/employee/punch_in")
    print_response(res)


def test_admin_apis() :
    login("admin@dinewell.com", "Admin@123")
    view_users()
    add_user()
    view_salaries()
    view_inventory()    
    view_menu("lunch")
    view_vendors()
    place_vendor_order()
    update_revenue()
    remove_expired_inventory()
    delete_user("testusr@dinewell.com")
    is_valid_session()
    ping()
    logout()

def test_employee_apis() :
    login("employee1@dinewell.com", "Employee1@123")
    view_menu("lunch")
    punch_in()
    employee_salary()
    is_valid_session()
    ping()
    logout()

def test_council_apis() :
    login("council@dinewell.com", "Council@123")
    view_menu("lunch")
    update_menu()
    is_valid_session()
    ping()
    logout()

def student_apis() :
    login("student1@dinewell.com", "Student1@123")
    view_menu("lunch")
    is_valid_session()
    ping()
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
# add_user(username="Student1", password="Student1@123", email="student1@dinewell.com", role="Student", dob="2003-04-05")
# logout()