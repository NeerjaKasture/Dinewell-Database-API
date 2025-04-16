document.addEventListener('DOMContentLoaded', function() {
    // Check if user is logged in and has council role
    checkCouncilAuth();
    
    // Setup event listeners
    document.getElementById('logout-btn').addEventListener('click', logout);
    document.getElementById('menu-form').addEventListener('submit', updateMenuItem);
    
    // Setup menu tabs
    const menuTabs = document.querySelectorAll('.menu-tab');
    menuTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs
            menuTabs.forEach(t => t.classList.remove('active'));
            
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Update form fields based on meal type
            const mealType = this.getAttribute('data-meal');
            updateFormFields(mealType);
            
            // Load menu items for the selected meal type
            const month = document.getElementById('Month').value;
            const day = document.getElementById('Day').value;
            loadMenuItems(mealType, month, day);
        });
    });
    
    // Setup month and day change listeners
    document.getElementById('Month').addEventListener('change', function() {
        const mealType = document.querySelector('.menu-tab.active').getAttribute('data-meal');
        const day = document.getElementById('Day').value;
        loadMenuItems(mealType, this.value, day);
    });
    
    document.getElementById('Day').addEventListener('change', function() {
        const mealType = document.querySelector('.menu-tab.active').getAttribute('data-meal');
        const month = document.getElementById('Month').value;
        loadMenuItems(mealType, month, this.value);
    });
    
    // Initialize form fields for default meal type (breakfast)
    updateFormFields('breakfast');
    
    // Load menu items for default selection
    const defaultMealType = document.querySelector('.menu-tab.active').getAttribute('data-meal');
    const defaultMonth = document.getElementById('Month').value;
    const defaultDay = document.getElementById('Day').value;
    loadMenuItems(defaultMealType, defaultMonth, defaultDay);
});

// Function to check if the current user has council role
function checkCouncilAuth() {
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
                document.getElementById('student-name').textContent = data.username;
            }
        }
    })
    .catch(error => {
        console.error('Auth check error:', error);
        window.location.href = '/';
    });
}

// Function to update form fields based on meal type
function updateFormFields(mealType) {
    const dynamicFieldsContainer = document.getElementById('dynamic-fields');
    let fieldsHTML = '';
    
    // Define fields for each meal type based on your database schema
    const mealFields = {
        breakfast: [
            { name: 'Breakfast_meal', label: 'Breakfast Meal', required: true },
            { name: 'Side_item', label: 'Side Item', required: false },
            { name: 'Pickle_Lemon', label: 'Pickle/Lemon', required: false },
            { name: 'Eggs', label: 'Eggs', required: true },
            { name: 'Bread_butter_jam', label: 'Bread/Butter/Jam', required: true },
            { name: 'Hot_Beverage', label: 'Hot Beverage', required: true },
            { name: 'Chocos_Cornflake', label: 'Chocos/Cornflake', required: true },
            { name: 'Flavoured_powder', label: 'Flavoured Powder', required: true },
            { name: 'Fruit', label: 'Fruit', required: true }
        ],
        lunch: [
            { name: 'Salad', label: 'Salad', required: true },
            { name: 'Dal', label: 'Dal', required: true },
            { name: 'Vegetable', label: 'Vegetable', required: true },
            { name: 'Legume_Curry', label: 'Legume Curry', required: false },
            { name: 'Rice_Side', label: 'Rice Side', required: true },
            { name: 'Dairy_Product', label: 'Dairy Product', required: true },
            { name: 'Chapati', label: 'Chapati', required: true },
            { name: 'Pickle_Lemon', label: 'Pickle/Lemon', required: false },
            { name: 'Papad_Fryums', label: 'Papad/Fryums', required: false }
        ],
        snacks: [
            { name: 'Snacks', label: 'Snacks', required: true },
            { name: 'Dips_Chutney', label: 'Dips/Chutney', required: false },
            { name: 'Cold_Beverage', label: 'Cold Beverage', required: true },
            { name: 'Hot_Beverage', label: 'Hot Beverage', required: true }
        ],
        dinner: [
            { name: 'Salad', label: 'Salad', required: false },
            { name: 'Dal', label: 'Dal', required: true },
            { name: 'Vegetable', label: 'Vegetable', required: true },
            { name: 'Rice', label: 'Rice', required: true },
            { name: 'Chapati', label: 'Chapati', required: true },
            { name: 'Pickle_Lemon', label: 'Pickle/Lemon', required: false },
            { name: 'Special_item', label: 'Special Item', required: false },
            { name: 'Non_veg', label: 'Non-Veg', required: false }
        ]
    };
    
    // Generate HTML for the fields
    const fields = mealFields[mealType] || [];
    
    // Create fields in pairs for two-column layout
    for (let i = 0; i < fields.length; i += 2) {
        fieldsHTML += '<div class="form-row">';
        
        // First field in the row
        fieldsHTML += `
            <div class="form-group">
                <label for="${fields[i].name}">${fields[i].label}</label>
                <input type="text" id="${fields[i].name}" name="${fields[i].name}" class="form-control" ${fields[i].required ? 'required' : ''}>
            </div>
        `;
        
        // Second field in the row (if exists)
        if (i + 1 < fields.length) {
            fieldsHTML += `
                <div class="form-group">
                    <label for="${fields[i+1].name}">${fields[i+1].label}</label>
                    <input type="text" id="${fields[i+1].name}" name="${fields[i+1].name}" class="form-control" ${fields[i+1].required ? 'required' : ''}>
                </div>
            `;
        }
        
        fieldsHTML += '</div>';
    }
    
    // Update the container with the new fields
    dynamicFieldsContainer.innerHTML = fieldsHTML;
    
    // Store the current meal type in a data attribute for the form
    document.getElementById('menu-form').setAttribute('data-meal-type', mealType);
}

// Function to load menu items for a specific meal type, month, and day
function loadMenuItems(mealType, month, day) {
    const container = document.getElementById('menu-items-container');
    container.innerHTML = '<p>Loading menu items...</p>';
    
    fetch(`/menu/${mealType}?month=${encodeURIComponent(month)}&day=${encodeURIComponent(day)}`, {
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
    .then(menuItems => {
        displayMenuItems(menuItems, mealType, month, day);
    })
    .catch(error => {
        console.error(`Error loading ${mealType} menu:`, error);
        container.innerHTML = `<p>Error loading menu items: ${error.message}</p>`;
    });
}

// Function to display menu items
function displayMenuItems(menuItems, mealType, month, day) {
    const container = document.getElementById('menu-items-container');
    
    if (!menuItems || menuItems.length === 0) {
        container.innerHTML = `<p>No menu items found for ${month} ${day}.</p>`;
        return;
    }
    
    let html = '';
    
    // Display each menu item
    menuItems.forEach(item => {
        html += `<div class="menu-item">`;
        html += `<div class="menu-item-header">`;
        html += `<div class="menu-item-title">${month} ${day} Menu</div>`;
        html += `<div class="menu-item-actions">`;
        html += `<button type="button" class="edit-btn" data-month="${month}" data-day="${day}">Edit</button>`;
        html += `</div></div>`;
        
        html += `<div class="menu-item-details">`;
        
        // Display all fields except Month and Day
        Object.entries(item).forEach(([key, value]) => {
            if (key !== 'Month' && key !== 'Day' && value) {
                html += `<span><strong>${key.replace(/_/g, ' ')}:</strong> ${value}</span>`;
            }
        });
        
        html += `</div></div>`;
    });
    
    container.innerHTML = html;
    
    // Add event listeners to edit buttons
    document.querySelectorAll('.edit-btn').forEach(button => {
        button.addEventListener('click', function() {
            const month = this.getAttribute('data-month');
            const day = this.getAttribute('data-day');
            
            // Set the form's month and day values
            document.getElementById('Month').value = month;
            document.getElementById('Day').value = day;
            
            // Find the menu item data
            const menuItem = menuItems.find(item => 
                item.Month === month && item.Day === day
            );
            
            if (menuItem) {
                // Fill in the form fields with the menu item data
                Object.entries(menuItem).forEach(([key, value]) => {
                    const field = document.getElementById(key);
                    if (field) {
                        field.value = value || '';
                    }
                });
                
                // Scroll to the form
                document.querySelector('.menu-form').scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
}

// Function to update a menu item
function updateMenuItem(e) {
    e.preventDefault();
    
    const mealType = this.getAttribute('data-meal-type');
    const month = document.getElementById('Month').value;
    const day = document.getElementById('Day').value;
    
    // Collect all form data
    const formData = {
        Month: month,
        Day: day
    };
    
    // Add all dynamic fields to the form data
    const dynamicFields = document.querySelectorAll('#dynamic-fields input');
    dynamicFields.forEach(field => {
        if (field.value) {
            formData[field.name] = field.value;
        }
    });
    
    // Disable submit button to prevent multiple submissions
    const submitBtn = this.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Updating...';
    
    // Send the update request
    fetch(`/council/menu/update/${mealType}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify(formData)
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => {
                try {
                    // Try to parse as JSON
                    const data = JSON.parse(text);
                    throw new Error(data.error || 'Failed to update menu item');
                } catch (e) {
                    if (text.includes('<!DOCTYPE html>')) {
                        throw new Error('Session expired. Please log in again.');
                    } else {
                        throw new Error('Failed to update menu item');
                    }
                }
            });
        }
        return response.json();
    })
    .then(data => {
        showAlert(document.getElementById('menu-alert'), data.message || 'Menu updated successfully', 'success');
        
        // Reload menu items to show the updated data
        loadMenuItems(mealType, month, day);
    })
    .catch(error => {
        console.error('Error updating menu item:', error);
        showAlert(document.getElementById('menu-alert'), error.message, 'danger');
    })
    .finally(() => {
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.textContent = 'Update Menu';
    });
}

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