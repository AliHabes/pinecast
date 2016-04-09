(function() {

var chartTypes = {
    line: 'Line',
    pie: 'Doughnut',
};

var GeoChartComponent = React.createClass({

    getInitialState: function() {
        return {
            loadingData: true,
            data: null,

            chart: null,
        };
    },

    render: function() {
        return React.createElement(
            'div',
            {},
            (this.props.title ? React.createElement('span', {className: 'chart-title'}, this.props.title) : null),
            React.createElement(
                'div',
                {
                    ref: 'surface',
                    width: this.props.origElement.clientWidth - 30,
                    height: 600,
                }
            )
        );
    },

    componentDidMount: function() {
        setTimeout(function() {
            this.startLoadingData();
        }.bind(this), Math.random() * 3000);
    },

    componentDidUpdate: function() {
        if (this.state.loadingData) {
            this.startLoadingData();
            return;
        }
        var node = this.refs.surface;
        var data = google.visualization.arrayToDataTable(this.state.data);
        var c = new google.visualization.GeoChart(node);
        c.draw(data, {});
        this.setState({chart: c});
    },

    startLoadingData: function() {
        var req = new XMLHttpRequest();
        req.onload = function() {
            var parsed = JSON.parse(req.responseText);
            this.setState({
                loadingData: false,
                data: parsed,
            });
        }.bind(this);
        req.open(
            'get',
            '/analytics/' + this.props.type +
                '?podcast=' + encodeURIComponent(this.props.podcast) +
                (this.props.episode ? '&episode=' + encodeURIComponent(this.props.episode) : ''),
            true
        );
        req.send();
    },

    shouldComponentUpdate: function(_, nextState) {
        return nextState.loadingData !== this.state.loadingData;
    },

});

google.load("visualization", "1", {packages:["geochart"]});
google.setOnLoadCallback(doLoad);

function doLoad() {
    var placeholders = document.querySelectorAll('.geo-chart-placeholder');
    Array.prototype.slice.call(placeholders).forEach(function(placeholder) {
        ReactDOM.render(
            React.createElement(GeoChartComponent, {
                podcast: placeholder.getAttribute('data-podcast'),
                episode: placeholder.getAttribute('data-episode'),
                type: placeholder.getAttribute('data-type'),
                title: placeholder.getAttribute('data-title'),

                origElement: placeholder,
            }),
            placeholder
        );
    });
}

}());
