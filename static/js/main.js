console.log('Main app loaded');
document.addEventListener('DOMContentLoaded', function() {
    const firstInput = document.querySelector('input:not([type="hidden"])');
    if (firstInput) setTimeout(() => firstInput.focus(), 100);
});