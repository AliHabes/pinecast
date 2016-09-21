(function() {

function hide(elem) {
    elem.style.overflow = 'hidden';
    elem.style.height = '0';
}
function show(elem) {
    elem.style.overflow = 'auto';
    elem.style.height = 'auto';
}

function buildTabs(tab) {
    var allTabs = Array.prototype.slice.call(tab.querySelectorAll('li a[data-tab]'));

    function select(a) {
        allTabs.forEach(function(tab) {
            if (tab === a) return;
            tab.parentNode.className = '';
            hide(document.querySelector(tab.getAttribute('data-tab')));
        });
        a.parentNode.className = 'selected';
        var tab = a.getAttribute('data-tab');
        show(document.querySelector(tab));
        window.history.replaceState(null, null, '#' + tab.substr(5));
    }

    tab.addEventListener('click', function(e) {
        if (!e.target.getAttribute('data-tab')) return;
        e.preventDefault();
        if (e.target.nodeName !== 'A') return;

        select(e.target);
    });

    var selected = null;
    if (window.location.hash) {
        selected = (
            tab.querySelector('a[data-tab=".tab-' + window.location.hash.substr(1) + '"]') ||
            tab.querySelector('a[data-tab=".' + window.location.hash.substr(1) + '"]')
        );
    }
    if (!selected) {
        selected = tab.querySelector('li a[data-tab]');
    }
    select(selected);
}

var tabs = document.querySelectorAll('.tabs.dynamic');
Array.prototype.slice.call(tabs).forEach(function(tab) {
    buildTabs(tab);
});

}());
