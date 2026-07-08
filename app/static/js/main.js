// main.js
document.addEventListener('click', function (e) {
    var trigger = e.target.closest('[data-dropdown-toggle]');
    var openMenus = document.querySelectorAll('.dropdown-menu.show');

    if (trigger) {
        var menu = trigger.parentElement.querySelector('.dropdown-menu');
        var wasOpen = menu.classList.contains('show');
        openMenus.forEach(function (m) { m.classList.remove('show'); });
        if (!wasOpen) menu.classList.add('show');
        return;
    }

    openMenus.forEach(function (menu) {
        if (!menu.parentElement.contains(e.target)) menu.classList.remove('show');
    });
});