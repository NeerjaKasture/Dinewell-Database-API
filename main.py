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


        if data['role'] == 'Employee':
            local_conn = get_db_local_connection()
            local_cursor = local_conn.cursor()
            salary = data.get('salary', 500)
            # Add to EmployeeSalary table
            local_cursor.execute("""
                INSERT INTO EmployeeSalary (MemberID, NoOfDays, SalaryPerDay, Month)
                VALUES (%s, 0, %s, %s)
            """, (user_id, salary, datetime.datetime.utcnow().strftime('%Y-%m-01')))
            local_conn.commit()
            local_cursor.close()

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

        cursor.execute("SELECT Role FROM Login WHERE MemberID = %s", (member_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"error": "User not found"}), 404
        role = result[0]

        if role == 'Employee':
            # Check if the user is in group 14
            if not is_member_of_group(member_id):
                return jsonify({"error": "User not part of Group 14"}), 403
            
            local_conn = get_db_local_connection()
            local_cursor = local_conn.cursor()
            local_cursor.execute("DELETE FROM EmployeeSalary WHERE MemberID = %s", (member_id,))
            local_conn.commit()
            local_cursor.close()
            
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
@app.route('/admin/inventory/remove_expired', methods=['PUT'])
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
            UPDATE Inventory
            SET Current_quantity = 0
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

# 6. Add employee salary
@app.route('/admin/add_salary', methods=['POST'])
@token_required(required_role='Admin')
def add_employee_salary():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized salary addition attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    required_fields = ["MemberID", "SalaryPerDay", "Month"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        conn = get_db_local_connection()
        numDays = data.get("NoOfDays", 0)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO EmployeeSalary (MemberID, SalaryPerDay, Month, NoOfDays)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            SalaryPerDay = VALUES(SalaryPerDay)
        """, (data["MemberID"], data["SalaryPerDay"], data["Month"], numDays))
        conn.commit()
        addLogs(member_id, 'Add Employee Salary', datetime.datetime.utcnow())
        return jsonify({"message": "Employee salary added successfully"}), 201
    except Exception as e:
        logging.error(f"Error adding employee salary: {str(e)}")
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

# 8. Check list of orders
@app.route('/admin/orders', methods=['GET'])
@token_required(required_role='Admin')
def view_orders():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized order view attempt by member {member_id}")
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
def place_order():
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
        addLogs(member_id, 'Add Payment', datetime.datetime.utcnow())

        local_conn = get_db_local_connection()
        local_cursor = local_conn.cursor()

        # 2. Add to inventory table in cs432g14
        local_cursor.execute("""
            INSERT INTO Inventory (ItemId, Product_name, Quantity, Unit, Min_quantity_req, Expiry_date, TotalCost, Date_of_order, Current_quantity, UpdatedBy)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            Product_name = VALUES(Product_name),
            Quantity = Quantity + VALUES(Quantity),
            Unit = VALUES(Unit),
            Min_quantity_req = VALUES(Min_quantity_req),
            TotalCost = TotalCost + VALUES(TotalCost),
            Date_of_order = VALUES(Date_of_order),
            Current_quantity = Current_quantity + VALUES(Current_quantity),
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
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            Vendorname = VALUES(Vendorname),
            Vendor_contact_no = VALUES(Vendor_contact_no),
            Quantity_ordered = Quantity_ordered + VALUES(Quantity_ordered),
            Unit = VALUES(Unit),
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

        cims_conn = get_db_connection()
        cims_cursor = cims_conn.cursor()

        month_start = datetime.datetime.strptime(data["Date"], '%Y-%m-%d').replace(day=1).strftime('%Y-%m-01')
        cims_cursor.execute("""
            INSERT INTO G14_revenue (Month, Payment, Inventory, Salary, Utilities)
            VALUES (%s, 0, %s, 0, 0)
            ON DUPLICATE KEY UPDATE
            Inventory = Inventory + VALUES(Inventory)
        """, (month_start, data["TotalCost"]))
        cims_conn.commit()
        addLogs(member_id, 'Update Inventory in G14_revenue', datetime.datetime.utcnow())
        
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
    
# 10. Update inventory quantity
@app.route('/admin/inventory/update_quantity/<int:item_id>', methods=['PUT'])
@token_required(required_role='Admin')
def update_inventory_quantity(item_id):
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(f"Unauthorized inventory update attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if 'quantity' not in data:
        return jsonify({"error": "Missing 'quantity' field"}), 400

    try:
        quantity_to_reduce = data['quantity']
        if quantity_to_reduce <= 0:
            return jsonify({"error": "Quantity must be a positive integer"}), 400

        conn = get_db_local_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch inventory entries for this item, ordered by expiry date
        cursor.execute("""
            SELECT ItemId, Expiry_date, Current_quantity
            FROM Inventory
            WHERE ItemId = %s AND Current_quantity > 0
            ORDER BY Expiry_date ASC
        """, (item_id,))
        entries = cursor.fetchall()

        if not entries:
            return jsonify({"error": "No inventory entries found for this item"}), 404

        remaining_to_reduce = quantity_to_reduce
        for entry in entries:
            current_quantity = entry['Current_quantity']
            if remaining_to_reduce <= 0:
                break

            deduct = min(current_quantity, remaining_to_reduce)
            new_quantity = current_quantity - deduct

            cursor.execute("""
                UPDATE Inventory
                SET Current_quantity = %s
                WHERE ItemId = %s AND Expiry_date = %s
            """, (new_quantity, item_id, entry['Expiry_date']))

            remaining_to_reduce -= deduct

        if remaining_to_reduce > 0:
            return jsonify({
                "warning": f"Only {quantity_to_reduce - remaining_to_reduce} units deducted. Not enough stock to fulfill full reduction."
            }), 206  # Partial Content

        conn.commit()
        addLogs(member_id, f"Reduced item {item_id} quantity by {quantity_to_reduce}", datetime.datetime.utcnow())
        return jsonify({"message": f"Item quantity reduced by {quantity_to_reduce} successfully"}), 200

    except Exception as e:
        logging.error(f"Error updating inventory quantity: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# 11. Punch in
@app.route('/admin/punch_in/<int:employee_id>', methods=['POST'])
@token_required(required_role='Admin')
def admin_punch_in(employee_id):
    session_token = request.cookies.get("session_token")
    try:
        payload = jwt.decode(session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
        admin_id = payload['user_id']
    except Exception as e:
        logging.warning("JWT decode failed")
        return jsonify({"error": "Unauthorized"}), 401

    if not is_valid_session() or not is_member_of_group(admin_id):
        logging.warning(f"Invalid punch-in attempt by admin {admin_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        month_str = data.get("month")  # Expecting format: "YYYY-MM"

        if not month_str:
            return jsonify({"error": "Missing 'month' in request body. Expected format: 'YYYY-MM'."}), 400

        try:
            month_start = datetime.datetime.strptime(month_str, "%Y-%m").date()
        except ValueError:
            return jsonify({"error": "Invalid month format. Use 'YYYY-MM'."}), 400

        # Connect to primary database (cs432g14)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verify employee exists and has correct role
        cursor.execute("""
            SELECT m.ID, l.Role
            FROM members m
            JOIN Login l ON m.ID = l.MemberID
            WHERE m.ID = %s AND l.Role = 'Employee'
        """, (employee_id,))
        employee = cursor.fetchone()
        conn.commit()
        conn.close()

        if not employee:
            return jsonify({"error": "Invalid employee ID or the member is not an Employee"}), 404

        conn = get_db_local_connection()
        cursor = conn.cursor(dictionary=True)
        # Check if EmployeeSalary record exists
        cursor.execute("""
            SELECT NoOfDays, SalaryPerDay FROM EmployeeSalary
            WHERE MemberID = %s AND Month = %s
        """, (employee_id, month_start))
        salary_record = cursor.fetchone()

        if not salary_record:
            return jsonify({"error": f"No salary record found for employee {employee_id} for {month_str}."}), 404

        # Update NoOfDays
        cursor.execute("""
            UPDATE EmployeeSalary
            SET NoOfDays = NoOfDays + 1
            WHERE MemberID = %s AND Month = %s
        """, (employee_id, month_start))
        conn.commit()

        # Update G14_revenue in cs432cims using new connection
        salary_per_day = salary_record['SalaryPerDay']
        current_month = datetime.datetime.utcnow().strftime('%Y-%m-01')

        conn_cims = mysql.connector.connect(
            host="10.0.116.125",
            user="cs432g14",
            password="YqJ5XnTz",
            database="cs432cims"
        )
        cursor_cims = conn_cims.cursor()

        cursor_cims.execute("""
            INSERT INTO G14_revenue (Month, Payment, Inventory, Salary, Utilities)
            VALUES (%s, 0, 0, %s, 0)
            ON DUPLICATE KEY UPDATE
            Salary = Salary + VALUES(Salary)
        """, (current_month, salary_per_day))
        conn_cims.commit()

        return jsonify({"message": f"Punch-in successful for employee {employee_id}"}), 200

    except Exception as e:
        logging.error(f"Error during punch-in for employee {employee_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass
        try:
            cursor_cims.close()
            conn_cims.close()
        except:
            pass


# 12. Update income table
@app.route('/admin/add_income', methods=['POST'])
@token_required(required_role='Admin')
def add_income():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(f"Unauthorized income addition attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    required_fields = ['Meal', 'Amount', 'TransactionID']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields: Meal, Amount, TransactionID"}), 400

    meal = data['Meal']
    amount = data['Amount']
    transaction_id = data['TransactionID']

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if transaction exists in payments
        cursor.execute("USE cs432cims")
        cursor.execute("""
            SELECT Sender, Receiver, Date
            FROM payments
            WHERE TransactionID = %s
        """, (transaction_id,))
        payment_info = cursor.fetchone()

        # Extract or fallback to request
        sender = (payment_info['Sender'] if payment_info and payment_info['Sender'] else data.get('Sender'))
        receiver = (payment_info['Receiver'] if payment_info and payment_info['Receiver'] else data.get('Receiver'))
        payment_date = (payment_info['Date'] if payment_info and payment_info['Date'] else data.get('Date'))

        # Check for missing fields
        if not (sender and receiver and payment_date):
            return jsonify({
                "error": "TransactionID not in payments – either update payments table or provide full transaction details in request (Sender, Receiver, Date)"
            }), 400

        # If transaction doesn't exist in payments, insert it
        if not payment_info:
            cursor.execute("""
                INSERT INTO payments (TransactionID, Sender, Receiver, Date)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                Sender = VALUES(Sender),
                Receiver = VALUES(Receiver),
                Date = VALUES(Date)
            """, (transaction_id, sender, receiver, payment_date))
            addLogs(member_id, f"Added transaction for TxnID {transaction_id}", datetime.datetime.utcnow())
            conn.commit()

        # Now add to Income table
        cursor.execute("USE cs432g14")
        cursor.execute("""
            INSERT INTO Income (Meal, Date, Amount, TransactionID)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            Amount = VALUES(Amount),
            Date = VALUES(Date)  
        """, (meal, payment_date, amount, transaction_id))

        # Update G14_revenue table in cs432cims
        cursor.execute("USE cs432cims")
        month_start = payment_date.replace(day=1).strftime('%Y-%m-01')
        cursor.execute("""
            INSERT INTO G14_revenue (Month, Payment, Inventory, Salary, Utilities)
            VALUES (%s, %s, 0, 0, 0)
            ON DUPLICATE KEY UPDATE
            Payment = Payment + VALUES(Payment)
        """, (month_start, amount))
        conn.commit()
        addLogs(member_id, f"Added income and transaction for TxnID {transaction_id}", datetime.datetime.utcnow())

        return jsonify({"message": "Income entry added successfully"}), 201

    except Exception as e:
        logging.error(f"Error adding income entry: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# 13. Update utilities table
@app.route('/admin/add_utility', methods=['POST'])
@token_required(required_role='Admin')
def add_utility():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    required_fields = ['Name', 'Amount', 'TransactionID']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    name = data['Name']
    amount = data['Amount']
    txn_id = data['TransactionID']
    sender = data.get('Sender')
    receiver = data.get('Receiver')
    txn_date = data.get('Date')  # YYYY-MM-DD

    try:
        # Connect to cs432cims to check payments
        conn_cims = get_db_connection()
        cursor_cims = conn_cims.cursor(dictionary=True)

        cursor_cims.execute("SELECT * FROM payments WHERE TransactionID = %s", (txn_id,))
        txn = cursor_cims.fetchone()

        if not txn:
            if not (sender and receiver and txn_date):
                return jsonify({
                    "error": "TransactionID not found in payments. Please provide Sender, Receiver, and Date, or add the transaction first."
                }), 400

            cursor_cims.execute("""
                INSERT INTO payments (TransactionID, Sender, Receiver, Date)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                Sender = VALUES(Sender),
                Receiver = VALUES(Receiver),
                Date = VALUES(Date)
            """, (txn_id, sender, receiver, txn_date))
            conn_cims.commit()

            txn = {'Date': txn_date}  # Use provided date for revenue update

        # Get the month from transaction date
        txn_month = datetime.datetime.strptime(str(txn['Date']), "%Y-%m-%d").strftime("%Y-%m-01")

        # Insert or update in G14_revenue for utilities
        cursor_cims.execute("""
            INSERT INTO G14_revenue (Month, Payment, Inventory, Salary, Utilities)
            VALUES (%s, 0, 0, 0, %s)
            ON DUPLICATE KEY UPDATE
            Utilities = Utilities + VALUES(Utilities)
        """, (txn_month, amount))
        conn_cims.commit()

        cursor_cims.close()
        conn_cims.close()

        # Insert into cs432g14.Utilities
        conn_util = get_db_local_connection()
        cursor_util = conn_util.cursor()

        cursor_util.execute("""
            INSERT INTO Utilities (Name, Amount, TransactionID, Date)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            Amount = Amount + VALUES(Amount),
            Date = VALUES(Date)
        """, (name, amount, txn_id, txn['Date']))
        conn_util.commit()

        cursor_util.close()
        conn_util.close()

        return jsonify({"message": f"Utility '{name}' of amount ₹{amount} added successfully."}), 201

    except Exception as e:
        logging.error(f"Error adding utility: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        try:
            cursor_cims.close()
            conn_cims.close()
        except:
            pass
        try:
            cursor_util.close()
            conn_util.close()
        except:
            pass

# 14. View revenue
@app.route('/admin/revenue', methods=['GET'])
@token_required(required_role='Admin')
def view_revenue():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(f"Unauthorized revenue view attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM G14_revenue")
        revenue_data = cursor.fetchall()
        return jsonify(revenue_data), 200
    except Exception as e:
        logging.error(f"Error fetching revenue data: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# 15. List uitilities
@app.route('/admin/list_utilities', methods=['GET'])
@token_required(required_role='Admin')
def list_utilities():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(f"Unauthorized utility view attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Utilities")
        utilities_data = cursor.fetchall()
        return jsonify(utilities_data), 200
    except Exception as e:
        logging.error(f"Error fetching utilities data: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# 16. Alerts
@app.route('/admin/alerts', methods=['GET'])
@token_required(required_role='Admin')
def view_alerts():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(f"Unauthorized alert view attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ItemId, Product_name, SUM(Current_quantity) AS Total_quantity, Min_quantity_req
            FROM Inventory
            GROUP BY ItemId, Product_name, Min_quantity_req
            HAVING Total_quantity < Min_quantity_req
        """)
        alerts_data = cursor.fetchall()
        return jsonify(alerts_data), 200
    except Exception as e:
        logging.error(f"Error fetching alerts data: {str(e)}")
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
    try:
        payload = jwt.decode(
            session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
        member_id = payload['user_id']
    except Exception as e:
        logging.warning("JWT decode failed")
        return jsonify({"error": "Unauthorized"}), 401

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized salary view attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Use a new local DB connection (cs432g14)
        conn = get_db_local_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM EmployeeSalary WHERE MemberID = %s", (member_id,))
        rows = cursor.fetchall()  # Always fetch all to avoid unread result errors

        if rows:
            return jsonify(rows), 200
        else:
            return jsonify({"error": "Salary information not found"}), 404

    except Exception as e:
        logging.error(f"Error fetching salary: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass







# =========== Council Members APIs ===========

# 1. Update the Menu
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

# 2. View complaints
@app.route('/complaint', methods=['GET'])
@token_required(required_role='Council')
def view_complaints():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized complaint view attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Complaints")
        complaints = cursor.fetchall()
        return jsonify(complaints), 200
    except Exception as e:
        logging.error(f"Error fetching complaints: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# 3. View feedback
@app.route('/feedback', methods=['GET'])
@token_required(required_role='Council')
def view_feedback():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized feedback view attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Feedbacks")
        feedbacks = cursor.fetchall()
        return jsonify(feedbacks), 200
    except Exception as e:
        logging.error(f"Error fetching feedback: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

        



# =========== Common APIs ===========

# 1. View menu
@app.route('/menu/<meal_type>', methods=['GET'])
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

# 2. write feedback
@app.route('/feedback', methods=['POST'])
@token_required()
def feedback():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized feedback attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or 'feedback' not in data:
        return jsonify({"error": "Feedback is required"}), 400

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT IGNORE INTO Feedbacks (MemberID, Feedback)
            VALUES (%s, %s)
        """, (member_id, data['feedback']))
        conn.commit()
        return jsonify({"message": "Feedback submitted successfully"}), 201
    except Exception as e:
        logging.error(f"Error submitting feedback: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        cursor.close()
        conn.close()

# 3. Raise complaint
@app.route('/complaint', methods=['POST'])
@token_required()
def raise_complaint():
    session_token = request.cookies.get("session_token")
    payload = jwt.decode(
        session_token, app.config['SECRET_KEY'], algorithms=["HS256"])
    member_id = payload['user_id']

    if not is_valid_session() or not is_member_of_group(member_id):
        logging.warning(
            f"Unauthorized complaint attempt by member {member_id}")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or 'complaint' not in data:
        return jsonify({"error": "Complaint is required"}), 400

    try:
        conn = get_db_local_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT IGNORE INTO Complaints (MemberID, Complaint)
            VALUES (%s, %s)
        """, (member_id, data['complaint']))
        conn.commit()
        return jsonify({"message": "Complaint raised successfully"}), 201
    except Exception as e:
        logging.error(f"Error raising complaint: {str(e)}")
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
