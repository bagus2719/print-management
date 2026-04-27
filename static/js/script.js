/* PrintManager – Minimal JS
   Most interactivity is handled inline in templates.
   This file is kept for any future shared utilities. */

document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss flash messages after 6 seconds
    document.querySelectorAll('[data-auto-dismiss]').forEach(el => {
        setTimeout(() => {
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 300);
        }, 6000);
    });
});