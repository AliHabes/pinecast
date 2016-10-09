(function() {

function hide(elem) {
    elem.style.display = 'none';
}
function show(elem) {
    elem.style.display = 'block';
}

function buildTabs(tabBar) {
    const allTabs = Array.prototype.slice.call(tabBar.querySelectorAll('li a[data-tab]'));

    function select(a, initial) {
        allTabs.forEach(function(tab) {
            if (tab === a) return;
            tab.parentNode.className = '';
            hide(document.querySelector(tab.getAttribute('data-tab')));
        });
        a.parentNode.className = 'selected';
        const tabName = a.getAttribute('data-tab');
        const tab = document.querySelector(tabName);
        show(tab);
        if (tabBar.getAttribute('data-no-history') !== null || initial) {
            return;
        }
        window.history.replaceState(null, null, '#' + tabName.substr(5));
    }

    tabBar.addEventListener('click', function(e) {
        if (!e.target.getAttribute('data-tab')) return;
        e.preventDefault();
        if (e.target.nodeName !== 'A') return;

        select(e.target);
    });

    let selected = null;
    if (window.location.hash) {
        selected = (
            tabBar.querySelector('a[data-tab=".tab-' + window.location.hash.substr(1) + '"]') ||
            tabBar.querySelector('a[data-tab=".' + window.location.hash.substr(1) + '"]')
        );
    }
    if (!selected) {
        selected = tabBar.querySelector('li a[data-tab]');
    }
    select(selected, true);
}

const tabs = document.querySelectorAll('.tabs.dynamic');
Array.prototype.slice.call(tabs).forEach(buildTabs);

}());
