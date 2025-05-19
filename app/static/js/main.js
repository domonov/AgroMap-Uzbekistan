/**
 * Main JavaScript file for AgroMap application
 */

// Check for online/offline status
window.addEventListener('online', updateOnlineStatus);
window.addEventListener('offline', updateOnlineStatus);

function updateOnlineStatus() {
    const statusIndicator = document.createElement('div');
    statusIndicator.className = 'alert alert-dismissible fade show';
    statusIndicator.setAttribute('role', 'alert');
    
    if (navigator.onLine) {
        statusIndicator.className += ' alert-success';
        statusIndicator.textContent = 'You are back online! All features are now available.';
    } else {
        statusIndicator.className += ' alert-warning';
        statusIndicator.textContent = 'You are currently offline. Some features may be limited.';
    }
    
    // Add dismiss button
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    closeButton.setAttribute('aria-label', 'Close');
    
    statusIndicator.appendChild(closeButton);
    
    // Add to page if not already present
    const existingAlert = document.querySelector('.alert[role="alert"]');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    document.querySelector('.container').prepend(statusIndicator);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        const alert = document.querySelector('.alert[role="alert"]');
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, 5000);
}

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Format dates
function formatDate(dateString) {
    if (!dateString) return '-';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Utility function to safely parse JSON
function safeJSONParse(str) {
    try {
        return JSON.parse(str);
    } catch (e) {
        console.error('Error parsing JSON:', e);
        return null;
    }
}

// Function to show loading spinner
function showLoading(element) {
    const spinner = document.createElement('div');
    spinner.className = 'spinner-border text-primary';
    spinner.setAttribute('role', 'status');
    
    const span = document.createElement('span');
    span.className = 'visually-hidden';
    span.textContent = 'Loading...';
    
    spinner.appendChild(span);
    
    element.innerHTML = '';
    element.appendChild(spinner);
}

// Function to handle errors
function handleError(element, message = 'An error occurred. Please try again.') {
    element.innerHTML = `
        <div class="alert alert-danger" role="alert">
            ${message}
        </div>
    `;
}

// Export functionality for tables
function exportTableToCSV(tableId, filename = 'data.csv') {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = table.querySelectorAll('tr');
    const csv = [];
    
    for (let i = 0; i < rows.length; i++) {
        const row = [], cols = rows[i].querySelectorAll('td, th');
        
        for (let j = 0; j < cols.length; j++) {
            // Replace any commas in the cell content to avoid CSV issues
            let text = cols[j].innerText.replace(/,/g, ';');
            // Wrap in quotes to handle newlines
            row.push('"' + text + '"');
        }
        
        csv.push(row.join(','));
    }
    
    // Download CSV file
    downloadCSV(csv.join('\n'), filename);
}

function downloadCSV(csv, filename) {
    const csvFile = new Blob([csv], {type: 'text/csv'});
    const downloadLink = document.createElement('a');
    
    downloadLink.download = filename;
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}
