document.addEventListener('DOMContentLoaded', function() {
    const toggleSwitch = document.querySelector('#theme-toggle');

    // Функция для переключения темы
    function switchTheme(e) {
        if (e.target.checked) {
            document.body.classList.add('dark-theme');
            localStorage.setItem('theme', 'dark');
        } else {
            document.body.classList.remove('dark-theme');
            localStorage.setItem('theme', 'light');
        }
    }

    // Установка сохраненной темы
    const currentTheme = localStorage.getItem('theme');
    if (currentTheme) {
        document.body.classList.add(currentTheme === 'dark' ? 'dark-theme' : 'light-theme');
        if (currentTheme === 'dark') {
            toggleSwitch.checked = true;
        }
    }

    // Слушатель события изменения переключателя
    toggleSwitch.addEventListener('change', switchTheme);
});
