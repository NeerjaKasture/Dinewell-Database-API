document.addEventListener('DOMContentLoaded', function() {
    // Check if user is logged in and has student role
    checkStudentAuth();
    
    // Set default month and day to today
    const currentDate = new Date();
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December'];
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    
    document.getElementById('month-select').value = months[currentDate.getMonth()];
    document.getElementById('day-select').value = days[currentDate.getDay()];
    
    // Setup event listeners
    document.getElementById('logout-btn').addEventListener('click', logout);
    
    // Setup main navigation tabs
    setupMainTabs();
    
    // Setup menu tabs
    setupMenuTabs();
    
    // Setup view menu button
    document.getElementById('view-menu-btn').addEventListener('click', loadSelectedMenu);
    
    // Setup form submissions
    document.getElementById('feedback-form').addEventListener('submit', handleFeedbackSubmit);
    document.getElementById('complaint-form').addEventListener('submit', handleComplaintSubmit);
    
    // Load default menu
    loadInitialMenu();
});

// ======================
// AUTHENTICATION FUNCTIONS
// ======================

function checkStudentAuth() {
    fetch('/isValidSession', {
        method: 'GET',
        credentials: 'include'
    })
    .then(handleResponse)
    .then(data => {
        if (data.username) {
            document.getElementById('student-name').textContent = data.username;
        }
    })
    .catch(error => redirectToLogin(error));
}

// ======================
// TAB MANAGEMENT
// ======================

function setupMainTabs() {
    const mainTabs = document.querySelectorAll('#main-tabs .menu-tab');
    mainTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Switch active tab
            mainTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding content
            const targetId = `tab-${this.dataset.tab}`;
            document.querySelectorAll('.tab-content').forEach(tc => {
                tc.style.display = tc.id === targetId ? 'block' : 'none';
            });
        });
    });
}

function setupMenuTabs() {
    const menuTabs = document.querySelectorAll('.menu-tab[data-meal]');
    menuTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            menuTabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            loadSelectedMenu();
        });
    });
}

// ======================
// MENU FUNCTIONS
// ======================

function loadInitialMenu() {
    const defaultMealType = document.querySelector('.menu-tab[data-meal].active').dataset.meal;
    const month = document.getElementById('month-select').value;
    const day = document.getElementById('day-select').value;
    loadMenu(defaultMealType, month, day);
}

function loadSelectedMenu() {
    const mealType = document.querySelector('.menu-tab[data-meal].active').dataset.meal;
    const month = document.getElementById('month-select').value;
    const day = document.getElementById('day-select').value;
    loadMenu(mealType, month, day);
}

async function loadMenu(mealType, selectedMonth, selectedDay) {
    showLoadingIndicator();
    
    try {
        const response = await fetch(`/menu/${mealType}`, {credentials: 'include'});
        const allMenuItems = await handleResponse(response);
        const filteredItems = allMenuItems.filter(item => 
            item.Month === selectedMonth && item.Day === selectedDay
        );
        displayMenu(filteredItems, selectedMonth, selectedDay);
    } catch (error) {
        handleMenuError(error, mealType);
    } finally {
        hideLoadingIndicator();
    }
}

function displayMenu(menuItems, month, day) {
    const tableBody = document.getElementById('menu-items');
    tableBody.innerHTML = '';
    
    if (!menuItems?.length) {
        tableBody.innerHTML = `<tr><td colspan="2">No menu available for ${month} ${day}</td></tr>`;
        return;
    }

    menuItems.forEach(item => {
        Object.entries(item).forEach(([key, value]) => {
            if (['Month', 'Day'].includes(key)) return;
            if (value) {
                tableBody.innerHTML += `
                    <tr>
                        <td>${key.replace(/_/g, ' ')}</td>
                        <td>${value}</td>
                    </tr>`;
            }
        });
    });
    document.getElementById('menu-table').style.display = 'table';
}

// ======================
// FEEDBACK & COMPLAINTS
// ======================

async function handleFeedbackSubmit(e) {
    e.preventDefault();
    const formData = getFormData('feedback');
    await submitForm('/feedback', formData, 'feedback-alert');
    e.target.reset();
}

async function handleComplaintSubmit(e) {
    e.preventDefault();
    const formData = getFormData('complaint');
    await submitForm('/complaint', formData, 'complaint-alert');
    e.target.reset();
}

function getFormData(formType) {
    const textarea = document.getElementById(`${formType}-text`);
    return { [formType]: textarea.value.trim() };
}

async function submitForm(url, data, alertId) {
    const alertElement = document.getElementById(alertId);
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify(data)
        });
        const result = await handleResponse(response);
        showAlert(alertElement, result.message, 'success');
    } catch (error) {
        showAlert(alertElement, error.message, 'danger');
    }
}

// ======================
// UTILITY FUNCTIONS
// ======================

function showLoadingIndicator() {
    document.getElementById('menu-loading').style.display = 'block';
    document.getElementById('menu-table').style.display = 'none';
}

function hideLoadingIndicator() {
    document.getElementById('menu-loading').style.display = 'none';
}

async function handleResponse(response) {
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText.includes('<!DOCTYPE html>') 
            ? 'Session expired. Please log in again.'
            : errorText);
    }
    return response.json();
}

function redirectToLogin(error) {
    console.error('Auth error:', error);
    window.location.href = '/';
}

function handleMenuError(error, mealType) {
    console.error(`Menu load error (${mealType}):`, error);
    showAlert(document.getElementById('menu-alert'), 
             error.message || `Failed to load ${mealType} menu`, 
             'danger');
}

function logout() {
    this.disabled = true;
    this.textContent = 'Logging out...';
    
    fetch('/logout', {
        method: 'POST',
        credentials: 'include',
        headers: {'Content-Type': 'application/json'}
    }).finally(() => setTimeout(() => window.location.href = '/', 500));
}

function showAlert(element, message, type) {
    element.textContent = message;
    element.className = `alert alert-${type}`;
    element.style.display = 'block';
    setTimeout(() => element.style.display = 'none', 5000);
}