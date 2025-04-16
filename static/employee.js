document.addEventListener('DOMContentLoaded', function() {
    // Check if user is logged in and has employee role
    checkEmployeeAuth();
    
    // Set default month and day to today
    const currentDate = new Date();
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    
    document.getElementById('month-select').value = months[currentDate.getMonth()];
    document.getElementById('day-select').value = days[currentDate.getDay()];
    
    // Setup event listeners
    document.getElementById('logout-btn').addEventListener('click', logout);
    
    // Setup menu tabs
    const menuTabs = document.querySelectorAll('.menu-tab');
    menuTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs
            menuTabs.forEach(t => t.classList.remove('active'));
            
            // Add active class to clicked tab
            this.classList.add('active');
        });
    });
    
    // Setup view menu button
    document.getElementById('view-menu-btn').addEventListener('click', function() {
        const mealType = document.querySelector('.menu-tab.active').getAttribute('data-meal');
        const month = document.getElementById('month-select').value;
        const day = document.getElementById('day-select').value;
        
        loadMenu(mealType, month, day);
    });
    
    // Load default menu (breakfast for current month/day)
    const defaultMealType = document.querySelector('.menu-tab.active').getAttribute('data-meal');
    loadMenu(defaultMealType, months[currentDate.getMonth()], days[currentDate.getDay()]);
});

// Function to check if the current user has employee access
function checkEmployeeAuth() {
    fetch('/isValidSession', {
        method: 'GET',
        credentials: 'include'
    })
    .then(response => response.json())
    .then(data => {
        if (!data.valid) {
            // Redirect to login page if session is invalid
            window.location.href = '/';
        } else {
            // Set username in header if available
            if (data.username) {
                document.getElementById('employee-name').textContent = data.username;
            }
        }
    })
    .catch(error => {
        console.error('Auth check error:', error);
        window.location.href = '/';
    });
}


// Function to load menu for a specific meal type
function loadMenu(mealType, selectedMonth, selectedDay) {
    // Show loading indicator
    document.getElementById('menu-loading').style.display = 'block';
    document.getElementById('menu-table').style.display = 'none';
    
    fetch(`/menu/${mealType}`, {
        method: 'GET',
        credentials: 'include'
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => {
                try {
                    // Try to parse as JSON
                    const data = JSON.parse(text);
                    throw new Error(data.error || `Failed to load ${mealType} menu`);
                } catch (e) {
                    if (text.includes('<!DOCTYPE html>')) {
                        throw new Error('Session expired. Please log in again.');
                    } else {
                        throw new Error(`Failed to load ${mealType} menu`);
                    }
                }
            });
        }
        return response.json();
    })
    .then(allMenuItems => {
        // Filter menu items by selected month and day
        const filteredMenuItems = allMenuItems.filter(item => 
            item.Month === selectedMonth && item.Day === selectedDay
        );
        
        displayMenu(filteredMenuItems, selectedMonth, selectedDay);
    })
    .catch(error => {
        console.error(`Error loading ${mealType} menu:`, error);
        showAlert(document.getElementById('menu-alert'), error.message, 'danger');
        document.getElementById('menu-loading').style.display = 'none';
    });
}

// Function to display menu items in the table
function displayMenu(menuItems, month, day) {
    const tableBody = document.getElementById('menu-items');
    tableBody.innerHTML = '';
    
    if (!menuItems || menuItems.length === 0) {
        // Show a message if no menu items are available
        const row = document.createElement('tr');
        row.innerHTML = `<td colspan="2" style="text-align: center;">No menu items available for ${month} ${day}.</td>`;
        tableBody.appendChild(row);
    } else {
        // For each menu item (typically just one object per meal)
        menuItems.forEach(item => {
            // For each field in the menu item
            Object.entries(item).forEach(([key, value]) => {
                // Skip Month and Day fields as they're already selected by the user
                if (key !== 'Month' && key !== 'Day' && value) {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${key.replace(/_/g, ' ')}</td>
                        <td>${value}</td>
                    `;
                    tableBody.appendChild(row);
                }
            });
        });
    }
    
    // Hide loading indicator and show table
    document.getElementById('menu-loading').style.display = 'none';
    document.getElementById('menu-table').style.display = 'table';
}

document.getElementById('view-salary-btn').addEventListener('click', async () => {
    const salaryLoading = document.getElementById('salary-loading');
    const salaryInfo = document.getElementById('salary-info');
    
    try {
        salaryLoading.style.display = 'block';
        salaryInfo.style.display = 'none';
        
        fetch('/employee/salary', {
            method: 'GET',
            credentials: 'include'
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('salary-loading').style.display = 'none';
            document.getElementById('salary-info').style.display = 'block';
            document.getElementById('salary-per-day').textContent = data.SalaryPerDay ? `₹${Number(data.SalaryPerDay).toFixed(2)}` : 'N/A';
            document.getElementById('total-salary').textContent = data.TotalSalary ? `₹${Number(data.TotalSalary).toFixed(2)}` : 'N/A';
            document.getElementById('salary-month').textContent = data.Month || 'N/A';
            document.getElementById('no-of-days').textContent = data.NoOfDays || 'N/A';
            document.getElementById('member-id').textContent = data.MemberID || 'N/A';
        })
        .catch(error => {
            document.getElementById('salary-loading').style.display = 'none';
            document.getElementById('salary-info').style.display = 'none';
            // Optionally show an error message
        });
        
        // Update the salary information in the UI
        document.getElementById('salary-per-day').textContent = `₹${data.SalaryPerDay.toFixed(2)}`;
        document.getElementById('total-salary').textContent = `₹${data.TotalSalary.toFixed(2)}`;
        document.getElementById('salary-month').textContent = data.Month;
        document.getElementById('no-of-days').textContent = data.NoOfDays;
        document.getElementById('member-id').textContent = data.MemberID;
        
        salaryInfo.style.display = 'grid';
    } catch (error) {
        console.error('Error fetching salary data:', error);
        // You might want to show an error message to the user
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger';
        alertDiv.style.display = 'block';
        alertDiv.textContent = 'Failed to fetch salary information. Please try again later.';
        document.getElementById('salary-view').insertBefore(alertDiv, salaryInfo);
        
        // Remove the alert after 5 seconds
        setTimeout(() => alertDiv.remove(), 5000);
    } finally {
        salaryLoading.style.display = 'none';
    }
});

// Tab switching functionality (already present in your HTML, but better to move it here)
document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // Remove active class from all tabs and content
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        // Add active class to clicked tab and corresponding content
        tab.classList.add('active');
        document.getElementById(tab.dataset.tab).classList.add('active');
    });
});
// Function to handle user logout
function logout() {
    // Disable the button to prevent multiple clicks
    this.disabled = true;
    this.textContent = 'Logging out...';
    
    fetch('/logout', {
        method: 'POST',
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        // Small delay for user feedback
        setTimeout(() => {
            window.location.href = '/';
        }, 500);
    })
    .catch(error => {
        console.error('Logout error:', error);
        setTimeout(() => {
            window.location.href = '/';
        }, 500);
    });
}

// Helper function to display alerts
function showAlert(alertElement, message, type) {
    alertElement.textContent = message;
    alertElement.className = `alert alert-${type}`;
    alertElement.style.display = 'block';
    
    // Hide alert after 5 seconds
    setTimeout(() => {
        alertElement.style.display = 'none';
    }, 5000);
}