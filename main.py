from flask import Flask, request, jsonify, make_response
import mysql.connector
import jwt
import datetime
import logging
import hashlib
from functools import wraps
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'CS'  # Change this to a strong secret in production

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='app.log',
    filemode='a'
)

# Database Configuration
db_config_proj = {
    "host": "10.0.116.125",  # Only the IP or hostname, no http or phpmyadmin
    "user": "cs432g14",
    "password": "YqJ5XnTz",  # Use your real password here
    "database": "cs432g14"
}

db_config = {
    "host": "10.0.116.125",
    "user": "cs432g14",
    "password": "YqJ5XnTz",  # Use your real password here
    "database": "cs432cims"
}



# Helper Functions

def get_db_connection():
    return mysql.connector.connect(**db_config)

def get_db_local_connection():
    return mysql.connector.connect(**db_config_proj)

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


def create_token(user_id, role):
    expiry = int((datetime.datetime.utcnow() +
                 datetime.timedelta(hours=24)).timestamp())
    return jwt.encode({
        'user_id': user_id,
        'role': role,
        'exp': expiry
    }, app.config['SECRET_KEY'], algorithm='HS256'), expiry

def token_required(required_role=None):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            token = request.cookies.get('session_token')
            if not token:
                return jsonify({"error": "Token is missing"}), 401

            try:
                data = jwt.decode(
                    token, app.config['SECRET_KEY'], algorithms=["HS256"])
                if required_role and data['role'] != required_role:
                    return jsonify({"error": "Insufficient permissions"}), 403
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token has expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 401

            return f(*args, **kwargs)
        return wrapped
    return decorator

def is_member_of_group(member_id, group_id=14):
    try:
        # Connect to the central database (cs432cims) for group mapping info.
        conn = mysql.connector.connect(
            host="10.0.116.125",
            user="cs432g14",
            password="YqJ5XnTz",
            database="cs432cims"
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM MemberGroupMapping WHERE MemberID = %s AND GroupID = %s
        """, (member_id, group_id))
        result = cursor.fetchone()
        return bool(result)
    except Exception as e:
        logging.error(f"Error checking group membership: {str(e)}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def addLogs(userID, Action, Timestamp):
    try:
        audit_conn = get_db_local_connection()
        audit_cursor = audit_conn.cursor()
        audit_cursor.execute("""
        INSERT INTO G14_AuditLogs (MemberID, Action, Timestamp)
        VALUES (%s, %s, %s)
        """, (userID, Action, Timestamp))
        audit_conn.commit()
    except Exception as audit_error:
        logging.error(f"Error logging audit action: {str(audit_error)}")
    finally:
        if 'audit_cursor' in locals():
            audit_cursor.close()
        if 'audit_conn' in locals():
            audit_conn.close()

def get_session_from_db(session_token):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT Expiry FROM Login WHERE Session = %s"
        cursor.execute(query, (session_token,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return {
                "Expiry": int(result["Expiry"])
            }
        return None

    except mysql.connector.Error as err:
        logging.error(f"MySQL error: {err}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return None




# =================== General APIs ==================

# 1. Login
@app.route('/login', methods=['POST'])
def login():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check member exists
        cursor.execute("""
            SELECT m.ID, m.UserName, l.Password, l.Role 
            FROM members m
            JOIN Login l ON m.ID = l.MemberID
            WHERE m.emailID = %s
        """, (email,))
        user = cursor.fetchone()

        if not user or user['Password'] != hash_password(password):
            return jsonify({"error": "Invalid credentials"}), 401

        # Check if the user is in group 14
        if not is_member_of_group(user['ID']):
            return jsonify({"error": "User not part of Group 14"}), 403
                 
        token, expiry = create_token(user['ID'], user['Role'])

        cursor.execute("""
            UPDATE Login
            SET Session = %s, Expiry = %s
            WHERE MemberID = %s
        """, (token, expiry, user['ID']))

        conn.commit()

        addLogs(user['ID'], 'Login', datetime.datetime.utcnow())

        response = make_response(jsonify({
            "message": "Login successful",
            "user": {
                "id": user['ID'],
                "name": user['UserName'],
                "role": user['Role']
            }
        }))
        response.set_cookie('session_token', token,
                            httponly=True, expires=expiry)
        return response

    except Exception as e:
        logging.error(f"Login error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# 2. Logout
@app.route('/logout', methods=['POST'])
def logout():
    response = jsonify({"message": "Successfully logged out"})
    response.set_cookie('session_token', '', expires=0)
    return response

# 3. Check server availability
@app.route('/ping', methods=['GET'])
def ping():
    return "pong", 200

# 4. Check if the session is valid
@app.route('/isValidSession', methods=['GET'])
def is_valid_session():
    session_token = request.args.get('session') or request.cookies.get('session_token')

    if not session_token:
        return jsonify({"valid": False, "error": "No session token provided"}), 400

    # Retrieve session from the database
    session = get_session_from_db(session_token)
    if not session:
        return jsonify({"valid": False, "error": "Session not found"}), 404

    # Compare expiry timestamp
    current_timestamp = int(datetime.datetime.utcnow().timestamp())
    if session['Expiry'] < current_timestamp:
        return jsonify({"valid": False, "error": "Session expired"}), 401

    return jsonify({"valid": True})


# ================= Admin APIs =================

# 1. View all users
@app.route('/admin/users', methods=['GET'])
@token_required(required_role='Admin')
def get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT m.ID, m.UserName, m.emailID, m.DoB, l.Role
            FROM members m
            JOIN Login l ON m.ID = l.MemberID
            JOIN MemberGroupMapping mg ON m.ID = mg.MemberID
            WHERE mg.GroupID = 14
        """)
        users = cursor.fetchall()
        return jsonify(users), 200
    except Exception as e:
        logging.error(f"Error fetching users: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# 2. Add new user
@app.route('/admin/addUser', methods=['POST'])
@token_required(required_role='Admin')
def add_user():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        session_token = request.cookies.get("session_token")
        payload = jwt.decode(
            session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
        member_id = payload['user_id']

        if not is_valid_session() or not is_member_of_group(member_id):
            logging.warning(f"Unauthorized add user attempt by member {member_id}")
            return jsonify({"error": "Unauthorized"}), 401

        data = request.get_json()
        required_fields = ['username', 'password', 'role', 'email', 'DoB']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db_connection()

        with conn.cursor(buffered=True) as cursor:
            cursor.execute("SELECT ID FROM members WHERE emailID = %s", (data['email'],))
            existing_user = cursor.fetchone()
            if existing_user:
                return jsonify({"error": "Email already exists"}), 400

            cursor.execute("""
                INSERT INTO members (UserName, emailID, DoB)
                VALUES (%s, %s, %s)
            """, (data['username'], data['email'], data['DoB']))
            user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO Login (MemberID, Password, Role)
                VALUES (%s, %s, %s)
            """, (user_id, hash_password(data['password']), data['role']))

            cursor.execute("""
                INSERT INTO MemberGroupMapping (MemberID, GroupID)
                VALUES (%s, %s)
            """, (user_id, 14))

        conn.commit()

        addLogs(user_id, 'Add User', datetime.datetime.utcnow())

        return jsonify({"message": "User created successfully"}), 201

    except mysql.connector.Error as e:
        if 'conn' in locals():
            conn.rollback()
        logging.error(f"Database error: {str(e)}")
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        logging.error(f"Error creating user: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 3. Delete user
@app.route('/admin/deleteUser', methods=['DELETE'])
@token_required(required_role='Admin')
def delete_user():
    try:
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400

        data = request.get_json()
        if 'email' not in data:
            return jsonify({"error": "Missing 'email' field"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)  # <-- Use buffered cursor

        # Get member ID
        cursor.execute("SELECT ID FROM members WHERE emailID = %s", (data['email'],))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "User not found"}), 404

        member_id = result[0]

        # Get all groups the user belongs to
        cursor.execute("SELECT GroupID FROM MemberGroupMapping WHERE MemberID = %s", (member_id,))
        groups = [row[0] for row in cursor.fetchall()]

        if 14 not in groups:
            return jsonify({"error": "User is not in group 14"}), 400

        if len(groups) == 1 and groups[0] == 14:
            # Only in group 14 — delete from all 3 tables
            cursor.execute("DELETE FROM Login WHERE MemberID = %s", (member_id,))
            cursor.execute("DELETE FROM MemberGroupMapping WHERE MemberID = %s", (member_id,))
            cursor.execute("DELETE FROM members WHERE ID = %s", (member_id,))
            conn.commit()
            addLogs(member_id, 'Delete User', datetime.datetime.utcnow())
            return jsonify({"message": "User was only in group 14 and has been fully deleted."}), 200
        else:
            # In multiple groups — remove only group 14
            cursor.execute("""
                DELETE FROM MemberGroupMapping
                WHERE MemberID = %s AND GroupID = 14
            """, (member_id,))
            conn.commit()
            addLogs(member_id, 'Delete User Mapping from group 14', datetime.datetime.utcnow())
            return jsonify({"message": "User removed from group 14, but retained in other groups."}), 200

    except mysql.connector.Error as e:
        conn.rollback()
        logging.error(f"Database error: {str(e)}")
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# 4. Removing expired inventory items
@app.route('/admin/inventory/remove_expired', methods=['DELETE'])
@token_required(required_role='Admin')
def remove_expired_inventory():
    session_token = request.cookies.get("session_token")
    # Extract member_id from the session token; assume it is in the JWT payload.
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    # Check centralized session validation and group membership
    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized inventory update attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM Inventory
            WHERE Expiry_date < CURDATE()
        """)
        conn.commit()
        return jsonify({"message": "Expired items removed successfully"}), 200
    except Exception as e:
        logging.error(f"Error removing expired items: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

#  5. View Employee Salaries
@app.route('/admin/salaries', methods=['GET'])
@token_required(required_role='Admin')
def view_salaries():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized salary view attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM EmployeeSalary")
        salaries = cursor.fetchall()
        return jsonify(salaries), 200
    except Exception as e:
        logging.error(f"Error fetching salaries: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# 6. Update daily revenue
@app.route('/admin/revenue_update', methods=['PUT'])
@token_required(required_role='Admin')
def update_revenue():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized revenue update attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    required_fields = ["Inventory", "Payment", "Salary",
                       "Utilities", "Month"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO G14_revenue (Month, Inventory, Payment, Salary, Utilities)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            Inventory = VALUES(Inventory),
            Payment = VALUES(Payment),
            Salary = VALUES(Salary),
            Utilities = VALUES(Utilities)
        """, (
            data["Month"], data["Inventory"], data["Payment"],
            data["Salary"], data["Utilities"]
        ))

        conn.commit()
        addLogs(member_id, 'Update Revenue', datetime.datetime.utcnow())
        return jsonify({"message": "Revenue updated successfully"}), 200
    except Exception as e:
        logging.error(f"Error updating revenue: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# 7. View Inventory
@app.route('/admin/inventory', methods=['GET'])
@token_required(required_role='Admin')
def view_inventory():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized inventory view attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Inventory")
        inventory_items = cursor.fetchall()
        return jsonify(inventory_items), 200
    except Exception as e:
        logging.error(f"Error fetching inventory: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# 8. Check list of vendors
@app.route('/admin/vendors', methods=['GET'])
@token_required(required_role='Admin')
def view_vendors():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized vendor view attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Vendors")
        vendors = cursor.fetchall()
        return jsonify(vendors), 200
    except Exception as e:
        logging.error(f"Error fetching vendors: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# 9. Place vendor order
@app.route('/admin/place_order', methods=['POST'])
@token_required(required_role='Admin')
def add_new_vendor():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized attempt to add a vendor by member {member_id}")
        return jsonify({"error": "Unauthorized session"}), 401

    data = request.get_json()
    required_fields = ["ItemId", "Vendorname", "Vendor_contact_no", "Quantity_ordered", "Unit", "TransactionID", "Sender", "Date", "Product_name", "Min_quantity_req", "Expiry_date", "TotalCost"]

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # 1. Add to payments table in cs432cims
        cims_conn = get_db_connection()
        cims_cursor = cims_conn.cursor()
        cims_cursor.execute("""
            INSERT INTO payments (TransactionID, Sender, Receiver, Date)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            Sender = VALUES(Sender),
            Receiver = VALUES(Receiver),
            Date = VALUES(Date)
        """, (
            data["TransactionID"],
            data["Sender"],
            data["Vendorname"],
            data["Date"]
        ))
        cims_conn.commit()

        local_conn = get_db_local_connection()
        local_cursor = local_conn.cursor()

        # 2. Add to inventory table in cs432g14
        local_cursor.execute("""
            INSERT INTO Inventory (ItemId, Product_name, Quantity, Unit, Min_quantity_req, Expiry_date, TotalCost, Date_of_order, Current_quantity, UpdatedBy)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            Product_name = VALUES(Product_name),
            Quantity = VALUES(Quantity),
            Unit = VALUES(Unit),
            Min_quantity_req = VALUES(Min_quantity_req),
            Expiry_date = VALUES(Expiry_date),
            TotalCost = VALUES(TotalCost),
            Date_of_order = VALUES(Date_of_order),
            Current_quantity = VALUES(Current_quantity),
            UpdatedBy = VALUES(UpdatedBy)
        """, (
            data["ItemId"],
            data["Product_name"],
            data["Quantity_ordered"],
            data["Unit"],
            data["Min_quantity_req"],
            data["Expiry_date"],
            data["TotalCost"],
            data["Date"],
            data["Quantity_ordered"],
            member_id
        ))


        # 3. Add to vendors table in cs432g14
        local_cursor.execute("""
            INSERT INTO Vendors (ItemId, Vendorname, Vendor_contact_no, Quantity_ordered, Unit, TransactionID, Amount)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            Vendorname = VALUES(Vendorname),
            Vendor_contact_no = VALUES(Vendor_contact_no),
            Quantity_ordered = VALUES(Quantity_ordered),
            Unit = VALUES(Unit),
            TransactionID = VALUES(TransactionID)
            Amount = VALUES(Amount)
        """, (
            data["ItemId"],
            data["Vendorname"],
            data["Vendor_contact_no"],
            data["Quantity_ordered"],
            data["Unit"],
            data["TransactionID"],
            data["TotalCost"]
        ))

        local_conn.commit()
        return jsonify({"message": "Vendor order, payment, and inventory record added successfully"}), 201

    except mysql.connector.Error as e:
        if 'cims_conn' in locals():
            cims_conn.rollback()
        if 'local_conn' in locals():
            local_conn.rollback()
        logging.error(f"MySQL error: {str(e)}")
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        logging.error(f"Error adding new vendor: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if 'cims_cursor' in locals():
            cims_cursor.close()
        if 'cims_conn' in locals():
            cims_conn.close()
        if 'local_cursor' in locals():
            local_cursor.close()
        if 'local_conn' in locals():
            local_conn.close()

# 10. Delete an item from inventory
@app.route('/admin/inventory/delete/<int:item_id>', methods=['DELETE'])
@token_required(required_role='Admin')
def delete_inventory_item(item_id):
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized inventory delete attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor()

        # Check if the item exists
        cursor.execute("SELECT * FROM Inventory WHERE ItemId = %s", (item_id,))
        item = cursor.fetchone()
        if not item:
            return jsonify({"error": "Item not found"}), 404

        # Delete the item
        cursor.execute("DELETE FROM Inventory WHERE ItemId = %s", (item_id,))
        conn.commit()

        addLogs(member_id, f"Deleted inventory item with ID {item_id}", datetime.datetime.utcnow())
        return jsonify({"message": "Item deleted successfully"}), 200

    except Exception as e:
        logging.error(f"Error deleting inventory item: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# 11. Update inventory quantity
@app.route('/admin/inventory/update_quantity/<int:item_id>', methods=['PUT'])
@token_required(required_role='Admin')
def update_inventory_quantity(item_id):
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized inventory update attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if 'quantity' not in data:
        return jsonify({"error": "Missing 'quantity' field"}), 400

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor()

        # Check if the item exists
        cursor.execute("SELECT * FROM Inventory WHERE ItemId = %s", (item_id,))
        item = cursor.fetchone()
        if not item:
            return jsonify({"error": "Item not found"}), 404

        # Update the quantity
        cursor.execute("""
            UPDATE Inventory
            SET Current_quantity = %s
            WHERE ItemId = %s
        """, (data['quantity'], item_id))
        conn.commit()

        addLogs(member_id, f"Updated inventory item {item_id} quantity to {data['quantity']}", datetime.datetime.utcnow())
        return jsonify({"message": "Item quantity updated successfully"}), 200

    except Exception as e:
        logging.error(f"Error updating inventory quantity: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# 12. Punch in
@app.route('/admin/punch_in/<int:employee_id>', methods=['POST'])
@token_required(required_role='Admin')
def admin_punch_in(employee_id):
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    admin_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(admin_id):
        logging.warning(f"Unauthorized punch-in attempt by admin {admin_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        today = datetime.date.today()
        month_start = today.replace(day=1)  # Normalize to first day of current month

        conn = get_db_local_connection()
        cursor = conn.cursor()

        # Check if record exists
        cursor.execute("""
            SELECT NoOfDays FROM EmployeeSalary
            WHERE MemberID = %s AND Month = %s
        """, (employee_id, month_start))

        result = cursor.fetchone()

        if result:
            # Update NoOfDays
            cursor.execute("""
                UPDATE EmployeeSalary
                SET NoOfDays = NoOfDays + 1
                WHERE MemberID = %s AND Month = %s
            """, (employee_id, month_start))
        else:
            # Insert new entry with NoOfDays = 1 (you can customize SalaryPerDay)
            default_salary = 500.00
            cursor.execute("""
                INSERT INTO EmployeeSalary (MemberID, Month, NoOfDays, SalaryPerDay)
                VALUES (%s, %s, %s, %s)
            """, (employee_id, month_start, 1, default_salary))

        conn.commit()
        return jsonify({"message": f"Punch-in successful for employee {employee_id}"}), 200

    except Exception as e:
        logging.error(f"Error during punch-in for employee {employee_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()



# ================ Employee APIs =================

# 1. View employee salary details
@app.route('/employee/salary', methods=['GET'])
@token_required(required_role='Employee')
def employee_salary():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized salary view attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM EmployeeSalary WHERE MemberID = %s", (member_id,))
        salary_info = cursor.fetchone()
        if salary_info:
            return jsonify(salary_info), 200
        else:
            return jsonify({"error": "Salary information not found"}), 404
    except Exception as e:
        logging.error(f"Error fetching salary: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()




# =========== Council Members APIs ===========

# Update the Menu
@app.route('/council/menu/update/<meal_type>', methods=['PUT'])  
@token_required(required_role='Council')
def add_menu(meal_type):
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session():
        logging.warning(f"Invalid session token for member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401
    if not is_member_of_group(member_id):
        logging.warning(f"Member {member_id} is not in the group")
        return jsonify({"error": "Unauthorized"}), 401

    table_mapping = {
        "breakfast": "Breakfast_menu",
        "lunch": "Lunch_menu",
        "dinner": "Dinner_menu",
        "snacks": "Snacks_menu"
    }

    table_name = table_mapping.get(meal_type.lower())
    if not table_name:
        return jsonify({"error": "Invalid meal type"}), 400

    updated_data = request.get_json()
    if not updated_data:
        return jsonify({"error": "No data provided"}), 400

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor()

        columns = ", ".join(updated_data.keys())
        placeholders = ", ".join(["%s"] * len(updated_data))
        update_clause = ", ".join([f"{col} = VALUES({col})" for col in updated_data.keys()])
        values = tuple(updated_data.values())

        query = f"""
        INSERT INTO {table_name} ({columns}) 
        VALUES ({placeholders}) 
        ON DUPLICATE KEY UPDATE {update_clause}
        """

        cursor.execute(query, values)
        conn.commit()

        return jsonify({"message": f"{meal_type.capitalize()} menu updated successfully"}), 201

    except Exception as e:
        logging.error(f"Error inserting menu: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()







# =========== Common API for Viewing Menu ===========

@app.route('/menu/<meal_type>', methods=['GET'])
# No required_role parameter, so any valid user can access it.
@token_required()
def view_menu(meal_type):
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized menu access attempt by member {member_id}")
        return jsonify({"error": "Unauthorized session"}), 401

    # Map meal types to their corresponding table names.
    table_mapping = {
        "breakfast": "Breakfast_menu",
        "lunch": "Lunch_menu",
        "dinner": "Dinner_menu",
        "snacks": "Snacks_menu"
    }

    table_name = table_mapping.get(meal_type.lower())
    if not table_name:
        return jsonify({"error": "Invalid meal type"}), 400

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM {table_name}")
        menu_items = cursor.fetchall()
        return jsonify(menu_items), 200
    except Exception as e:
        logging.error(f"Error fetching menu items: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()






if __name__ == '__main__':
    # Create tables if they don't exist
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS members (
        #         ID INT AUTO_INCREMENT PRIMARY KEY,
        #         UserName VARCHAR(100) NOT NULL,
        #         emailID VARCHAR(100) UNIQUE NOT NULL,
        #         DoB DATE
        #     )
        # """)

        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS Login (
        #         MemberID INT PRIMARY KEY,
        #         Password VARCHAR(255) NOT NULL,
        #         Role VARCHAR(20) NOT NULL,
        #         FOREIGN KEY (MemberID) REFERENCES members(ID)
        #     )
        # """)

        # Check if admin exists
        cursor.execute(
            "SELECT ID FROM members WHERE emailID = 'admin@dinewell.com'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO members (UserName, emailID, DoB)
                VALUES ('admin', 'admin@dinewell.com', '2000-01-01')
            """)
            admin_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO Login (MemberID, Password, Role)
                VALUES (%s, %s, 'Admin')
            """, (admin_id, hash_password('Admin@123')))

        conn.commit()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"Database initialization failed: {str(e)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

    app.run(debug=True, host='127.0.0.1', port=5000)
