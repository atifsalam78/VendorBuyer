// Toast notification system
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-message">${message}</div>
        <button class="toast-close">&times;</button>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
    
    // Close button
    toast.querySelector('.toast-close').addEventListener('click', function() {
        toast.remove();
    });
}

// Form validation helpers
function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function validateMobile(mobile) {
    const mobileRegex = /^[0-9]{10,12}$/;
    return mobileRegex.test(mobile);
}

// Helper function to get cookie value
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

// Initialize any global event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Add any global initialization here
    console.log('BazaarHub application initialized');
    
    // Only initialize profile dropdown if the dropdown container exists
    const dropdownContainer = document.querySelector('.profile-dropdown');
    if (dropdownContainer) {
        // Multiple initialization attempts to work around profile page conflicts
        let attempts = 0;
        const maxAttempts = 5;
        
        function tryInitialize() {
            attempts++;
            console.log(`Profile dropdown initialization attempt ${attempts}/${maxAttempts}`);
            
            try {
                // Check if dropdown container still exists before initializing
                const dropdownContainer = document.querySelector('.profile-dropdown');
                if (dropdownContainer) {
                    initializeProfileDropdown();
                    console.log('Profile dropdown initialized successfully');
                } else {
                    console.log('Profile dropdown container no longer exists - stopping initialization attempts');
                }
            } catch (error) {
                console.error('Profile dropdown initialization failed:', error);
                
                if (attempts < maxAttempts) {
                    // Try again with increasing delays
                    setTimeout(tryInitialize, attempts * 200);
                }
            }
        }
        
        // Start initialization attempts
        setTimeout(tryInitialize, 100);
    } else {
        console.log('Profile dropdown container not found - skipping initialization');
    }
});

// Profile dropdown functionality
function initializeProfileDropdown() {
    console.log('Initializing profile dropdown...');
    
    const dropdownContainer = document.querySelector('.profile-dropdown');
    const dropdownToggle = dropdownContainer?.querySelector('.profile-picture-btn');
    const dropdownMenu = dropdownContainer?.querySelector('.custom-dropdown-menu');
    
    console.log('Profile dropdown container found:', dropdownContainer);
    console.log('Profile dropdown toggle found:', dropdownToggle);
    console.log('Profile dropdown menu found:', dropdownMenu);
    
    if (!dropdownContainer || !dropdownToggle || !dropdownMenu) {
        console.error('Profile dropdown elements not found');
        return;
    }
    
    // Store original event listeners to prevent conflicts
    const originalToggleClick = dropdownToggle.onclick;
    
    // Override any existing click handlers to ensure our dropdown works
    
    // Toggle dropdown on click - use capture phase to ensure we handle it first
    function handleToggleClick(e) {
        console.log('Dropdown toggle clicked');
        e.preventDefault();
        e.stopImmediatePropagation();
        
        const isOpen = dropdownMenu.classList.contains('show');
        
        if (isOpen) {
            hideDropdown();
        } else {
            showDropdown();
        }
    }
    
    dropdownToggle.addEventListener('click', handleToggleClick, true); // Use capture phase
    dropdownToggle._clickHandler = handleToggleClick;
    
    // Close dropdown when clicking outside
    function handleDocumentClick(e) {
        if (!dropdownMenu.contains(e.target) && !dropdownToggle.contains(e.target)) {
            hideDropdown();
        }
    }
    
    // Use a named function for easier removal - use capture phase
    document.addEventListener('click', handleDocumentClick, true);
    
    // Store the event listener for later removal
    dropdownContainer._dropdownClickListener = handleDocumentClick;
    
    // Find dropdown menu items - match the actual HTML structure
    const logoutBtn = document.getElementById('logout-btn');
    const profileBtn = dropdownMenu.querySelector('a[href="/profile"]');
    
    // Handle logout action
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation(); // Prevent event from bubbling to document
            performLogout();
        });
    }
    
    // Handle profile action
    if (profileBtn) {
        profileBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation(); // Prevent event from bubbling to document
            console.log('Profile clicked - navigating to profile page');
            hideDropdown(); // Close dropdown first
            // Navigate to profile page after a small delay for smooth UX
            setTimeout(() => {
                window.location.href = '/profile';
            }, 100);
        });
    }
    
    // Handle escape key to close dropdown - use capture phase
    function handleEscapeKey(e) {
        if (e.key === 'Escape' && dropdownContainer.classList.contains('dropdown-open')) {
            hideDropdown();
        }
    }
    document.addEventListener('keydown', handleEscapeKey, true);
    
    // Store for later removal
    dropdownContainer._escapeKeyListener = handleEscapeKey;
    
    // Add cleanup method
    dropdownContainer.cleanupDropdown = function() {
        if (this._dropdownClickListener) {
            document.removeEventListener('click', this._dropdownClickListener, true);
        }
        if (this._escapeKeyListener) {
            document.removeEventListener('keydown', this._escapeKeyListener, true);
        }
        dropdownToggle.removeEventListener('click', dropdownToggle._clickHandler, true);
    };
}

function showDropdown() {
    const dropdownContainer = document.querySelector('.profile-dropdown');
    if (dropdownContainer) {
        dropdownContainer.classList.add('dropdown-open');
    }
}

function hideDropdown() {
    const dropdownContainer = document.querySelector('.profile-dropdown');
    if (dropdownContainer) {
        dropdownContainer.classList.remove('dropdown-open');
    }
}

function performLogout() {
    // Call server-side logout endpoint to properly delete session
    fetch('/logout', {
        method: 'GET',
        credentials: 'same-origin' // Include cookies in the request
    })
    .then(response => {
        if (response.ok) {
            // Clear the session cookie client-side as well
            document.cookie = 'session_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
            
            // Show logout success message
            showToast('You have been logged out successfully', 'success');
            
            // Redirect to home page after a short delay
            setTimeout(() => {
                window.location.href = '/';
            }, 1500);
        } else {
            showToast('Logout failed. Please try again.', 'error');
        }
    })
    .catch(error => {
        console.error('Logout error:', error);
        showToast('Logout failed. Please try again.', 'error');
    });
}