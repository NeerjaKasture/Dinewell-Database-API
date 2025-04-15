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


# 1. Login as Admin
def login(email, password):
    print("[*] Logging in...")
    res = session.post(f"{BASE_URL}/login", json={
        "email": email,
        "password": password
    })
    print_response(res)

# 2. View all users
def view_users():
    print("[*] Fetching users...")
    res = session.get(f"{BASE_URL}/users")
    print_response(res)

# 3. Add new user
def add_user():
    print("[*] Adding new user...")
    res = session.post(f"{BASE_URL}/addUser", json={
        "username": "TestUsr4",
        "password": "Test@123",
        "role": "Student",
        "email": "testusr@dinewell.com",
        "DoB": "2003-04-05"
    })
    print_response(res)

# 4. View salaries (admin)
def view_salaries():
    print("[*] Viewing employee salaries...")
    res = session.get(f"{BASE_URL}/admin/salaries")
    print_response(res)

# 5. View inventory
def view_inventory():
    print("[*] Viewing inventory...")
    res = session.get(f"{BASE_URL}/admin/inventory")
    print_response(res)

# 6. View menu
def view_menu(meal_type="lunch"):
    print(f"[*] Viewing {meal_type} menu...")
    res = session.get(f"{BASE_URL}/menu/{meal_type}")
    print_response(res)

# 7. Logout

# 8. Delete a user (admin)
def delete_user(email="testusr@dinewell.com"):
    print("[*] Deleting user...")
    res = session.delete(f"{BASE_URL}/deleteUser", json={"email": email})
    print_response(res)

# 9. Remove expired inventory (admin)
def remove_expired_inventory():
    print("[*] Removing expired inventory...")
    res = session.delete(f"{BASE_URL}/admin/inventory/remove_expired")
    print_response(res)

# 10. Update revenue (admin)
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
    res = session.put(f"{BASE_URL}/admin/revenue/update", json=data)
    print_response(res)

# 11. View vendors (admin)
def view_vendors():
    print("[*] Viewing vendors...")
    res = session.get(f"{BASE_URL}/admin/vendors")
    print_response(res)

# 13. Place vendor order (admin)
def place_vendor_order():
    print("[*] Adding new vendor...")
    data = {
        "ItemId" : 0, 
        "Vendorname" : "abc",
        "Vendor_contact_no": 2222222222, 
        "Quantity_ordered": 10, 
        "Unit": "kg", 
        "TransactionID": 1234
    }
    res = session.post(f"{BASE_URL}/admin/vendors/place_order", json=data)
    print_response(res)

# 14. Employee salary (as employee)
def employee_salary():
    print("[*] Viewing employee salary...")
    res = session.get(f"{BASE_URL}/employee/salary")
    print_response(res)

# 15. Ping (health check)
def ping():
    print("[*] Pinging server...")
    res = session.get(f"{BASE_URL}/ping")
    print_response(res)

# 16. DB connection check
def dbcon():
    print("[*] Checking DB connection...")
    res = session.get(f"{BASE_URL}/dbcon")
    print_response(res)

# 17. Check session validity
def is_valid_session():
    print("[*] Checking session validity...")
    # Get the session token from cookies
    token = session.cookies.get("session_token")
    res = session.get(f"{BASE_URL}/isValidSession", params={"session": token})
    print_response(res)


def logout():
    print("[*] Logging out...")
    res = session.post(f"{BASE_URL}/logout")
    print_response(res)

if __name__ == "__main__":
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
    dbcon()
    logout()