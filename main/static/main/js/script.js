// Custom JavaScript for PharmaStore
//
// This file intentionally contains very few scripts because most
// functionality (such as authentication, cart management and form
// processing) is handled server‑side by Django.  If you wish to add
// client‑side enhancements—like live search suggestions or interactive
// form validation—define your functions here and ensure the elements
// exist in the corresponding templates.

document.addEventListener('DOMContentLoaded', () => {
    // Example: automatically hide messages after 5 seconds
    const messages = document.querySelectorAll('.alert, .message');
    if (messages) {
        setTimeout(() => {
            messages.forEach(msg => {
                msg.style.display = 'none';
            });
        }, 5000);
    }
});