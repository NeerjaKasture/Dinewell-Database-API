document.addEventListener('DOMContentLoaded', function() {
    // Check if user is logged in and has admin role
    checkAdminAccess();
    
    // Load user list
    loadUsers();
    
    // Setup event listeners
    document.getElementById('logout-btn').addEventListener('click', logout);
    document.getElementById('add-user-form').addEventListener('submit', addUser);
    document.getElementById('delete-user-form').addEventListener('submit', deleteUser);
    document.getElementById('remove-expired-btn').addEventListener('click', removeExpiredInventory);
    const utilityForm = document.getElementById('add-utility-form');
    if (utilityForm) {
        utilityForm.addEventListener('submit', addUtility);
    }
    const tableBody = document.querySelector('#utilities-table tbody');
    document.getElementById('punch-in-form').addEventListener('submit', handlePunchIn);
    document.getElementById('refresh-revenue').addEventListener('click', fetchRevenueData);
    document.getElementById('refresh-orders').addEventListener('click', fetchOrders);
    document.getElementById('place-order-form').addEventListener('submit', placeOrder);
    fetchOrders();
    fetchRevenueData();
    loadSalaries();
    fetchUtilities();
    loadInventory();
});

// Function to check if the current user has admin access
function checkAdminAccess() {
    fetch('/isValidSession')
        .then(response => response.json())
        .then(data => {
            if (!data.valid) {
                // Redirect to login page if session is invalid
                window.location.href = '/';
            }
        })
        .catch(error => {
            console.error('Error checking session:', error);
            window.location.href = '/';
        });
}

// Function to load and display users
function loadUsers() {
    fetch('/users', {
        method: 'GET',
        credentials: 'include' // Include cookies in the request
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to fetch users');
        }
        return response.json();
    })
    .then(users => {
        displayUsers(users);
    })
    .catch(error => {
        console.error('Error loading users:', error);
        document.getElementById('user-list').innerHTML = `
            <h3>Current Users</h3>
            <p>Error loading users. Please try again later.</p>
        `;
    });
}

// Function to display users in the UI
function displayUsers(users) {
    const userListElement = document.getElementById('user-list');
    
    if (!users || users.length === 0) {
        userListElement.innerHTML = `
            <h3>Current Users</h3>
            <p>No users found.</p>
        `;
        return;
    }
    
    let userListHTML = `<h3>Current Users</h3>`;
    
    users.forEach(user => {
        const roleBadgeClass = `role-badge role-${user.Role.toLowerCase().replace(' ', '-')}`;
        
        userListHTML += `
            <div class="user-list-item">
                <div class="user-info">
                    <strong>${user.UserName}</strong>
                    <div>${user.emailID}</div>
                    <span class="${roleBadgeClass}">${user.Role}</span>
                </div>
                <div class="user-actions">
                    <button class="btn btn-danger btn-sm delete-btn" data-email="${user.emailID}">Delete</button>
                </div>
            </div>
        `;
    });
    
    userListElement.innerHTML = userListHTML;
    
    // Add event listeners to delete buttons
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', function() {
            const email = this.getAttribute('data-email');
            document.getElementById('delete-email').value = email;
        });
    });
}

// Function to handle user logout
function logout(event) {
    event.preventDefault();
    
    fetch('/logout', {
        method: 'POST',
        credentials: 'include' // Include cookies in the request
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Logout failed');
        }
        return response.json();
    })
    .then(data => {
        // Redirect to login page after successful logout
        window.location.href = '/';
    })
    .catch(error => {
        console.error('Error during logout:', error);
        alert('Failed to logout. Please try again.');
    });
}

// Function to handle adding a new user
function addUser(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const dob = document.getElementById('dob').value;
    const role = document.getElementById('role').value;
    
    const alertElement = document.getElementById('add-user-alert');
    
    // Validate form data
    if (!username || !email || !password || !dob || !role) {
        showAlert(alertElement, 'Please fill in all fields.', 'danger');
        return;
    }
    
    // Prepare request data
    const userData = {
        username: username,
        email: email,
        password: password,
        DoB: dob,
        role: role
    };
    
    // Send request to add user
    fetch('/admin/addUser', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include', // Include cookies in the request
        body: JSON.stringify(userData)
    })
    
    .then(response => {
        return response.json().then(data => {
            if (!response.ok) {
                throw new Error(data.error || 'Failed to add user');
            }
            return data;
        });
    })
    .then(data => {
        // Show success message
        showAlert(alertElement, 'User added successfully!', 'success');
        
        // Reset form
        document.getElementById('add-user-form').reset();
        
        // Reload user list
        loadUsers();
    })
    .catch(error => {
        console.error('Error adding user:', error);
        showAlert(alertElement, error.message, 'danger');
    });
}

// Function to handle deleting a user
function deleteUser(event) {
    event.preventDefault();
    
    const email = document.getElementById('delete-email').value;
    const alertElement = document.getElementById('delete-user-alert');
    
    // Validate email
    if (!email) {
        showAlert(alertElement, 'Please enter an email address.', 'danger');
        return;
    }
    
    // Confirm deletion
    if (!confirm(`Are you sure you want to delete the user with email ${email}?`)) {
        return;
    }
    
    // Send request to delete user
    fetch('/deleteUser', {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include', // Include cookies in the request
        body: JSON.stringify({ email: email })
    })
    .then(response => {
        return response.json().then(data => {
            if (!response.ok) {
                throw new Error(data.error || 'Failed to delete user');
            }
            return data;
        });
    })
    .then(data => {
        // Show success message
        showAlert(alertElement, data.message || 'User deleted successfully!', 'success');
        
        // Reset form
        document.getElementById('delete-user-form').reset();
        
        // Reload user list
        loadUsers();
    })
    .catch(error => {
        console.error('Error deleting user:', error);
        showAlert(alertElement, error.message, 'danger');
    });
}

async function addUtility(e) {
    e.preventDefault();
    const name = document.getElementById('utility-name').value.trim();
    const amount = document.getElementById('utility-amount').value.trim();
    const txnid = document.getElementById('utility-txnid').value.trim();
    const sender = document.getElementById('utility-sender').value.trim();
    const receiver = document.getElementById('utility-receiver').value.trim();
    const date = document.getElementById('utility-date').value.trim();

    // Prepare payload
    const payload = {
        Name: name,
        Amount: parseFloat(amount),
        TransactionID: txnid
    };

    // Add optional fields if provided
    if (sender) payload.Sender = sender;
    if (receiver) payload.Receiver = receiver;
    if (date) payload.Date = date;

    try {
        const response = await fetch('/admin/add_utility', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload),
            credentials: 'include'
        });

        const result = await response.json();

        if (response.ok) {
            alert(result.message || 'Utility added!');
            e.target.reset();
            fetchUtilities();
        } else {
            alert(result.error || 'Error adding utility.');
        }
    } catch (err) {
        alert('Network error.');
    }
}

// Fetch and display utilities
async function fetchUtilities() {
    const tableBody = document.querySelector('#utilities-table tbody');
    if (!tableBody) return;
    
    try {
        const response = await fetch('/admin/list_utilities', {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();

        tableBody.innerHTML = '';

        if (Array.isArray(data) && data.length > 0) {
            data.forEach(util => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${util.Name}</td>
                    <td>₹${parseFloat(util.Amount).toFixed(2)}</td>
                    <td>${util.TransactionID}</td>
                `;
                tableBody.appendChild(row);
            });
        } else {
            tableBody.innerHTML = '<tr><td colspan="3">No utilities found.</td></tr>';
        }
    } catch (err) {
        console.error('Fetch error:', err);
        tableBody.innerHTML = '<tr><td colspan="3">Error loading utilities. Check console.</td></tr>';
    }
}
// Function to load inventory data
function loadInventory() {
    const inventoryTable = document.getElementById('inventory-items');
    const loadingIndicator = document.getElementById('inventory-loading');
    const alertElement = document.getElementById('inventory-alert');

    loadingIndicator.style.display = 'block';
    inventoryTable.innerHTML = '';

    fetch('/admin/inventory', {
        method: 'GET',
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to fetch inventory');
            });
        }
        return response.json();
    })
    .then(inventory => {
        displayInventory(inventory);
        loadingIndicator.style.display = 'none';
    })
    .catch(error => {
        console.error('Error loading inventory:', error);
        loadingIndicator.style.display = 'none';
        showAlert(alertElement, error.message, 'danger');
    });
}

// Function to display inventory in a table
function displayInventory(inventory) {
    const tbody = document.getElementById('inventory-items');
    const today = new Date();
    
    tbody.innerHTML = inventory.map(item => {
        const expiryDate = new Date(item.Expiry_date);
        const today = new Date();
        const isExpired = expiryDate < today || Number(item.Current_quantity) <= 0;
        const status = isExpired ? 'Expired' : 'Available';
    
        return `
            <tr class="${isExpired ? 'expired-row' : ''}">
                <td>${item.ItemId}</td>
                <td>${item.Product_name}</td>
                <td>${item.Current_quantity}</td>
                <td>${item.Min_quantity_req}</td>
                <td>${item.Unit}</td>
                <td>${expiryDate.toLocaleDateString()}</td>
                <td>₹${Number(item.TotalCost).toLocaleString()}</td>
                <td>${new Date(item.Date_of_order).toLocaleDateString()}</td>
                <td>${item.UpdatedBy}</td>
                <td>${status}</td>
                <td>
                    <button class="btn btn-sm btn-warning edit-btn" 
                            data-itemid="${item.ItemId}"
                            data-currentquantity="${item.Current_quantity}">
                        Edit
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    // Add event listeners to edit buttons
    document.querySelectorAll('.edit-btn').forEach(button => {
        button.addEventListener('click', function() {
            const itemId = this.dataset.itemid;
            const currentQty = this.dataset.currentquantity;
            document.getElementById('update-item-id').value = itemId;
            document.getElementById('update-quantity').value = currentQty;
        });
    });
}

// Function to handle removing expired inventory
function removeExpiredInventory() {
    if (!confirm('This will set current quantity to 0 for all expired items. Continue?')) {
        return;
    }

    const alertElement = document.getElementById('inventory-alert');
    
    fetch('/admin/inventory/remove_expired', {
        method: 'PUT',
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to update expired items');
            });
        }
        return response.json();
    })
    .then(data => {
        showAlert(alertElement, data.message, 'success');
        loadInventory(); // Refresh inventory list
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert(alertElement, error.message, 'danger');
    });
}


function loadSalaries() {
    fetch('/admin/salaries', {
        method: 'GET',
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to fetch salaries');
            });
        }
        return response.json();
    })
    .then(salaries => {
        displaySalaries(salaries);
    })
    .catch(error => {
        console.error('Error loading salaries:', error);
        const salariesList = document.getElementById('salaries-list');
        if (salariesList) {
            salariesList.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center; padding: 20px;">
                        Error loading salaries: ${error.message}
                    </td>
                </tr>
            `;
        }
        const alertElement = document.getElementById('salaries-alert');
        if (alertElement) {
            showAlert(alertElement, 'Failed to load employee salaries: ' + error.message, 'danger');
        }
    });
}

function displaySalaries(salaries) {
    const salariesList = document.getElementById('salaries-list');
    if (!salaries || salaries.length === 0) {
        salariesList.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 20px;">
                    No employee salaries found.
                </td>
            </tr>
        `;
        return;
    }
    let salariesHTML = '';
    salaries.forEach(salary => {
        salariesHTML += `
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">${salary.Month || 'N/A'}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">${salary.MemberID || 'N/A'}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">${salary.NoOfDays || 'N/A'}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">₹${salary.SalaryPerDay || 'N/A'}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">₹${salary.TotalSalary || 'N/A'}</td>
            </tr>
        `;
    });
    salariesList.innerHTML = salariesHTML;
}

const currentMonth = new Date().toISOString().slice(0, 7); 
// Add new function for punch-in handling
function handlePunchIn(event) {
    event.preventDefault();
    const employeeId = document.getElementById('employee-id').value;
    const alertElement = document.getElementById('punch-in-alert');

    if (!employeeId) {
        showAlert(alertElement, 'Please enter an Employee ID', 'danger');
        return;
    }

    fetch(`/admin/punch_in/${employeeId}`, {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ month: currentMonth })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Punch-in failed');
            });
        }
        return response.json();
    })
    .then(data => {
        showAlert(alertElement, data.message, 'success');
        document.getElementById('punch-in-form').reset();
        loadSalaries();
    })
    .catch(error => {
        console.error('Punch-in error:', error);
        showAlert(alertElement, error.message, 'danger');
    });
}

async function fetchRevenueData() {
    try {
        const response = await fetch('/admin/revenue', {
            credentials: 'include'
        });
        const data = await response.json();
        populateRevenueTable(data);
    } catch (err) {
        console.error('Error fetching revenue:', err);
        alert('Failed to load revenue data');
    }
}

// Populate the revenue table
function populateRevenueTable(data) {
    const tableBody = document.querySelector('#revenue-table tbody');
    tableBody.innerHTML = '';

    if (Array.isArray(data) && data.length > 0) {
        data.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${new Date(row.Month).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}</td>
                <td>₹${parseFloat(row.Payment || 0).toFixed(2)}</td>
                <td>₹${parseFloat(row.Inventory || 0).toFixed(2)}</td>
                <td>₹${parseFloat(row.Salary || 0).toFixed(2)}</td>
                <td>₹${parseFloat(row.Utilities || 0).toFixed(2)}</td>
                <td>₹${parseFloat(row.TotalExpense || 0).toFixed(2)}</td>
                <td class="${parseFloat(row.TotalRevenue || 0) < 0 ? 'negative' : ''}">
                    ₹${parseFloat(row.TotalRevenue || 0).toFixed(2)}
                </td>
            `;
            tableBody.appendChild(tr);
        });
    } else {
        tableBody.innerHTML = '<tr><td colspan="7">No revenue data found.</td></tr>';
    }
}

// Helper function to display alerts
function showAlert(element, message, type) {
    element.textContent = message;
    element.className = `alert alert-${type}`;
    element.style.display = 'block';
    
    // Hide alert after 5 seconds
    setTimeout(() => {
        element.style.display = 'none';
    }, 5000);
}

document.getElementById('update-quantity-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const itemId = document.getElementById('update-item-id').value;
    const quantity = document.getElementById('update-quantity').value;
    const alertElement = document.getElementById('update-quantity-alert');

    if (!itemId || !quantity) {
        showAlert(alertElement, 'Please fill in all fields', 'danger');
        return;
    }

    try {
        const response = await fetch(`/admin/inventory/update_quantity/${itemId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({ quantity: parseInt(quantity) })
        });

        const data = await response.json();

        if (response.ok) {
            showAlert(alertElement, data.message, 'success');
            loadInventory(); // Refresh inventory list
            this.reset();
        } else {
            showAlert(alertElement, data.error || 'Update failed', 'danger');
        }
    } catch (err) {
        console.error('Update error:', err);
        showAlert(alertElement, 'Network error', 'danger');
    }
});

async function fetchOrders() {
    const tableBody = document.querySelector('#orders-table tbody');
    tableBody.innerHTML = '';
    try {
        const response = await fetch('/admin/orders', { credentials: 'include' });
        const data = await response.json();
        if (Array.isArray(data) && data.length > 0) {
            data.forEach(order => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${order.ItemId}</td>
                    <td>${order.Vendorname}</td>
                    <td>${order.Vendor_contact_no}</td>
                    <td>₹${parseFloat(order.Amount).toFixed(2)}</td>
                    <td>${parseFloat(order.Quantity_ordered).toFixed(2)}</td>
                    <td>${order.Unit}</td>
                    <td>${order.TransactionID}</td>
                `;
                tableBody.appendChild(row);
            });
        } else {
            tableBody.innerHTML = '<tr><td colspan="7">No orders found.</td></tr>';
        }
    } catch (err) {
        tableBody.innerHTML = '<tr><td colspan="7">Error loading orders.</td></tr>';
    }
}

// Place a new vendor order
async function placeOrder(e) {
    e.preventDefault();
    const alertElement = document.getElementById('order-alert');

    // Gather form data
    const payload = {
        ItemId: document.getElementById('order-itemid').value,
        Product_name: document.getElementById('order-productname').value,
        Vendorname: document.getElementById('order-vendorname').value,
        Vendor_contact_no: document.getElementById('order-vendorcontact').value,
        Quantity_ordered: parseFloat(document.getElementById('order-quantity').value),
        Unit: document.getElementById('order-unit').value,
        TransactionID: document.getElementById('order-txnid').value,
        Sender: document.getElementById('order-sender').value,
        Date: document.getElementById('order-date').value,
        Min_quantity_req: parseFloat(document.getElementById('order-minqty').value),
        Expiry_date: document.getElementById('order-expiry').value,
        TotalCost: parseFloat(document.getElementById('order-totalcost').value)
    };

    try {
        const response = await fetch('/admin/place_order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (response.ok) {
            showAlert(alertElement, result.message, 'success');
            e.target.reset();
            fetchOrders();
        } else {
            showAlert(alertElement, result.error || 'Order failed', 'danger');
        }
    } catch (err) {
        showAlert(alertElement, 'Network error', 'danger');
    }
}