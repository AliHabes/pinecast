(function() {

var allCats = window.PODCAST_CATEGORIES.sort(function(a, b) {
    return a.localeCompare(b);
});

var CategoryComponent = React.createClass({

    getInitialState: function() {
        var hasDef = !!this.props.defCats;
        var selectedCats = hasDef ? this.props.defCats.split(',') : [];
        return {
            selectedCats: selectedCats,
            cats: allCats.sort(function(a, b) {
                var leftSelected = selectedCats.indexOf(a) > -1;
                var rightSelected = selectedCats.indexOf(a) > -1;
                if (leftSelected && !rightSelected) {
                    return -1;
                }
                if (!leftSelected && rightSelected) {
                    return 1;
                }
                return a.localeCompare(b);
            })
        };
    },

    render: function() {
        return React.createElement(
            'div',
            {
                className: 'category-picker',
            },
            this.getItems(),
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

    getItems: function() {
       return allCats.map(function(s) {
            var isSelected = this.state.selectedCats.indexOf(s) > -1;
            return React.createElement(
                'button',
                {
                    className: 'category' + (isSelected ? ' is-selected' : ''),
                    key: s,
                    onClick: isSelected ? this.doUnselect.bind(this, s) : this.doSelect.bind(this, s),
                    type: 'button',
                },
                s
            );
        }, this);
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
        }),
        field
    );
});

}());
