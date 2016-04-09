(function() {

var allCats = window.PODCAST_CATEGORIES;

var CategoryComponent = React.createClass({

    getInitialState: function() {
        var hasDef = !!this.props.defCats;
        return {
            selectedCats: hasDef ? this.props.defCats.split(',') : [],
        };
    },

    render: function() {
        return React.createElement(
            'div',
            {
                className: 'category-picker',
            },
            this.getUnselected(),
            this.getSelected(),
            React.createElement(
                'input',
                {
                    name: this.props.name,
                    type: 'hidden',
                    value: this.state.selectedCats.join(',')
                }
            )
        );
    },

    getUnselected: function() {
        var unselected = allCats.filter(function(c) {
            return this.state.selectedCats.indexOf(c) === -1;
        }, this).sort();
        return React.createElement(
            'div',
            {className: 'category-picker-unselected'},
            React.createElement('b', {}, this.props.transUnsel),
            unselected.map(function(u) {
                return React.createElement(
                    'a',
                    {
                        className: 'category',
                        onClick: this.doSelect.bind(this, u),
                        href: '#',
                    },
                    u
                );
            }, this)
        );
    },
    getSelected: function() {
        return React.createElement(
            'div',
            {className: 'category-picker-selected'},
            React.createElement('b', {}, this.props.transSel),
            this.state.selectedCats.map(function(s) {
                return React.createElement(
                    'a',
                    {
                        className: 'category',
                        onClick: this.doUnselect.bind(this, s),
                        href: '#',
                    },
                    s
                );
            }, this)
        );
    },

    doSelect: function(cat, e) {
        e.preventDefault();
        this.setState({
            selectedCats: [cat].concat(this.state.selectedCats).sort(),
        });
    },
    doUnselect: function(cat, e) {
        e.preventDefault();
        this.setState({
            selectedCats: this.state.selectedCats.filter(function(c) {return c !== cat;}),
        });
    },

});


var fields = document.querySelectorAll('.category-placeholder');
Array.prototype.slice.call(fields).forEach(function(field) {
    ReactDOM.render(
        React.createElement(CategoryComponent, {
            name: field.getAttribute('data-name'),
            defCats: field.getAttribute('data-default-cats'),

            transUnsel: field.getAttribute('data-trans-unselcats'),
            transSel: field.getAttribute('data-trans-selcats'),
        }),
        field
    );
});

}());
