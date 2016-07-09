(function() {

function request(method, url, body, onload, onerror) {
    var xhr = new XMLHttpRequest();
    xhr.onload = function() {
        if (xhr.status !== 200) {
            if (onerror) {
                onerror(xhr.responseText);
            }
        } else {
            onload(xhr.responseText);
        }
    };
    xhr.onerror = onerror;

    xhr.open(method, url, true);
    if (method.toUpperCase() === 'POST' && url[0] === '/') {
        xhr.setRequestHeader('X-CSRFToken', this.props.csrf);
    }
    xhr.send(body);
    return xhr;
}

var SlugField = React.createClass({
    propTypes: {
        validityCB: React.PropTypes.func.isRequired,
        valueCB: React.PropTypes.func.isRequired,
    },
    getInitialState: function() {
        return {
            checkTimeout: null,
            checkXHR: null,

            isValid: null,
        };
    },

    render: function() {
        return React.createElement(
            'label',
            {},
            React.createElement('span', {}, 'Slug'),
            React.createElement(
                'input',
                {
                    className: 'slug-field width-full',
                    maxLength: 64,
                    pattern: '[\\w-]+',
                    placeholder: 'my-great-podcast',
                    ref: 'inp',
                    required: true,
                    type: 'text',
                    readOnly: this.props.readonly,

                    onInput: this.checkValidity,
                }
            ),
            !this.props.readonly && this.state.isValid === null ? null : React.createElement(
                'div',
                {className: 'url-availability ' + (this.state.isValid ? 'is-available' : 'is-unavailable')},
                this.state.isValid ? gettext('The slug is available!') : gettext('The slug is unavailable.')
            )
        );
    },

    checkValidity: function() {
        this.setState({isValid: null});

        if (this.state.checkXHR) {
            this.state.checkXHR.abort();
            this.setState({checkXHR: null});
        }
        if (this.state.checkTimeout) {
            clearTimeout(this.state.checkTimeout);
            this.setState({checkTimeout: null});
        }

        var node = this.refs.inp;
        if (!node.validity.valid || !node.value) {
            this.props.validityCB(false);
            return;
        } else {
            this.props.validityCB(true);
        }

        this.props.valueCB(node.value);
        this.setState({checkTimeout: setTimeout(this.doCheck, 500)});
    },
    doCheck: function() {
        var node = this.refs.inp;
        var req = this.req(
            'get',
            '/dashboard/services/slug_available?slug=' + encodeURIComponent(node.value),
            null,
            function(responseText) {
                var parsed = JSON.parse(responseText);
                this.setState({isValid: parsed.valid});
            }.bind(this)
        );
    },

    req: request,
});

var PodcastImporter = React.createClass({

    getInitialState: function() {
        return {
            step: 1,
            step1error: null,
            step2loaded: false,
            step2error: null,
            slugValue: null,
            slugValid: false,
            step3process: null,
            step3xhr: null,
            step3ids: null,
            step3interval: null,

            importPercent: null,

            podcastData: null,
        };
    },

    render: function() {
        return React.createElement(
            'div',
            {},
            !this.state.step1error ? null : React.createElement(
                'div',
                {className: 'error'},
                this.state.step1error
            ),
            this.getStep1(),
            this.getStep2(),
            this.getStep2_5(),
            this.getStep3(),
            this.getStep4()
        );
    },

    getStep1: function() {
        if (this.state.step !== 1) {
            return null;
        }
        return React.createElement(
            'div',
            {className: 'card card-block'},
            React.createElement('strong', {}, gettext('Step One')),
            React.createElement('p', {}, gettext('Enter the feed URL of your existing podcast')),
            React.createElement(
                'label',
                {},
                React.createElement('span', {}, gettext('Feed URL')),
                React.createElement(
                    'input',
                    {
                        type: 'url',
                        ref: 's1url',
                        placeholder: 'http://wtfpod.libsyn.com/rss',
                        readOnly: this.state.step !== 1,
                        pattern: 'https?://',
                        title: gettext('Enter a HTTP or HTTPS feed URL'),
                    }
                )
            ),
            React.createElement(
                'button',
                {
                    onClick: this.downloadFeed,
                },
                gettext('Continue')
            )
        );
    },
    getStep2: function() {
        if (this.state.step !== 2) {
            return null;
        }

        if (!this.state.step2loaded) {
            return React.createElement(
                'div',
                {className: 'card card-block'},
                React.createElement('strong', {}, gettext('Step Two')),
                React.createElement('p', {}, gettext('Loading feed information...'))
            );
        }

        return React.createElement(
            'div',
            {className: 'card card-block'},
            React.createElement('strong', {}, gettext('Step Two')),
            React.createElement('p', {}, gettext('Review the feed information below')),
            !this.state.step2error ? null : React.createElement('div', {className: 'error'}, this.state.step2error),
            this.renderPodcastData(),
            React.createElement(
                'menu',
                {className: 'toolbar'},
                React.createElement(
                    'li',
                    {},
                    React.createElement(
                        'button',
                        {
                            onClick: this.goToStep2_5,
                        },
                        gettext('Continue')
                    )
                ),
                React.createElement(
                    'li',
                    {},
                    React.createElement(
                        'button',
                        {
                            className: 'btn-neutral',
                            onClick: function() {
                                this.setState({
                                    step: 1,
                                    step1error: null,
                                    step2loaded: false,
                                });
                            }.bind(this),
                        },
                        gettext('Change Feed')
                    )
                )
            )
        );
    },
    getStep2_5: function() {
        if (this.state.step !== 2.5) {
            return null;
        }
        return React.createElement(
            'div',
            {className: 'card card-block'},
            React.createElement('strong', {}, gettext('Step Two')),
            React.createElement('p', {}, gettext('Please choose a slug to use for this podcast.')),
            !this.state.step2error ? null : React.createElement('div', {className: 'error'}, this.state.step2error),
            React.createElement(
                SlugField,
                {
                    validityCB: function(valid) {
                        this.setState({slugValid: valid});
                    }.bind(this),
                    valueCB: function(value) {
                        this.setState({slugValue: value});
                    }.bind(this),
                }
            ),
            React.createElement(
                'menu',
                {className: 'toolbar'},
                React.createElement(
                    'li',
                    {},
                    React.createElement(
                        'button',
                        {
                            onClick: this.beginImport,
                        },
                        gettext('Continue')
                    )
                )
            )
        );
    },
    getStep3: function() {
        if (this.state.step !== 3) {
            return null;
        }

        var progress = this.getStep3Progress();
        return React.createElement(
            'div',
            {className: 'card card-block'},
            React.createElement('strong', {}, gettext('Step Three')),
            this.getStep3ProgressText(),
            React.createElement(
                'div',
                {className: 'progress'},
                React.createElement('i', {style: {width: progress + '%'}, 'data-tooltip': progress + '%'})
            )
        );
    },
    getStep4: function() {
        if (this.state.step !== 4) {
            return null;
        }

        return React.createElement(
            'div',
            {className: 'card card-block'},
            React.createElement('strong', {}, gettext('Import Complete')),
            React.createElement('p', {}, gettext('We\'ve finished importing your podcast. Thanks for choosing Pinecast!')),
            React.createElement(
                'a',
                {
                    className: 'btn',
                    href: '/dashboard/podcast/' + encodeURIComponent(this.state.slugValue),
                },
                gettext('Go to Podcast')
            )
        );
    },

    downloadFeed: function() {
        var val = this.refs.s1url.value;
        if (!val) {
            this.setState({step1error: gettext('You must enter a feed URL')});
            return;
        }
        this.setState({step: 2, step1error: null});

        this.req('get', '/dashboard/services/get_request_token', null, function(text) {
            getFeed.call(this, JSON.parse(text).token);
        }.bind(this), function() {
            this.setState({
                step: 1,
                step1error: gettext('Unable to get an access token from Pinecast'),
            });
        }.bind(this));

        function getFeed(token) {
            this.req(
                'get',
                this.props.rssFetch +
                    '?token=' + encodeURIComponent(token) +
                    '&url=' + encodeURIComponent(val),
                null,
                function(text) {
                    var parsed = JSON.parse(text);
                    if (parsed.errorMessage) {
                        this.setState({step: 1, step1error: parsed.errorMessage});
                        return;
                    }
                    processFeed.call(this, parsed.content);
                }.bind(this),
                function() {
                    this.setState({
                        step: 1,
                        step1error: gettext('Could not connect to the Pinecast import server'),
                    });
                }.bind(this)
            );
        }

        function processFeed(feedContent) {
            var fd = new FormData();
            fd.append('feed', feedContent);
            this.req(
                'post',
                '/dashboard/import/feed',
                fd,
                function(responseText) {
                    var parsed = JSON.parse(responseText);
                    if (parsed.error) {
                        switch(parsed.error) {
                            case 'invalid encoding':
                                this.setState({step: 1, step1error: gettext('We were able to download the feed, but it had a bad encoding.')});
                                return;
                            case 'invalid xml':
                                this.setState({step: 1, step1error: gettext('We were able to download the feed, but could not parse it. Try validating your feed first.')});
                                return;
                            case 'invalid format':
                                this.setState({step: 1, step1error: parsed.details});
                                return;
                        }
                        return;
                    }
                    this.setState({
                        step2loaded: true,
                        podcastData: parsed,
                    });
                }.bind(this),
                function() {
                    this.setState({
                        step: 1,
                        step1error: gettext('Could not connect to Pinecast'),
                    })
                }.bind(this)
            );
        }
    },

    renderPodcastData: function() {
        var data = this.state.podcastData;

        function nullStyle(obj, val) {
            if (val) return obj;
            obj.style = {'font-style': 'italic'};
            return obj
        }
        function trunc(str) {
            if (str.length < 60) {
                return str;
            }
            return str.substr(0, 60) + '...';
        }

        return React.createElement(
            'div',
            {
                className: 'podcast-import-data',
                style: {
                    'min-height': '200px',
                    'padding-left': '220px',
                    position: 'relative',
                },
            },
            React.createElement(
                'img',
                {
                    className: 'podcast-import-coverimage',
                    src: data.cover_image,
                    style: {
                        height: '200px',
                        left: 0,
                        position: 'absolute',
                        top: 0,
                        width: '200px',
                    },
                }
            ),
            React.createElement('hgroup', {},
                React.createElement('h1', {className: 'podcast-import-title'}, data.name),
                React.createElement('h2', nullStyle(data.subtitle, {className: 'podcast-import-subtitle'}), data.subtitle || gettext('No Subtitle'))
            ),
            React.createElement(
                'div',
                {
                    className: 'podcast-import-description',
                    dangerouslySetInnerHTML: {__html: data.description},
                    style: {margin: '20px 10px'},
                }
            ),
            React.createElement('h3', {}, gettext('Categories')),
            React.createElement(
                'ul',
                {
                    style: {
                        'line-height': '20px',
                        margin: '10px 0',
                    },
                },
                data.categories.map(function(c, i) {
                    return React.createElement('li', {key: i}, c);
                })
            ),
            React.createElement('h3', {}, gettext('Details')),
            React.createElement(
                'dl',
                {
                    style: {padding: '15px'},
                },
                React.createElement('dt', {}, gettext('Homepage')),
                React.createElement('dd', {}, data.homepage),

                React.createElement('dt', {}, gettext('Language')),
                React.createElement('dd', {}, data.language),

                React.createElement('dt', {}, gettext('Copyright')),
                React.createElement('dd', {}, data.copyright),

                React.createElement('dt', {}, gettext('Author Name')),
                React.createElement('dd', {}, data.author_name),

                React.createElement('dt', {}, gettext('Explicit?')),
                React.createElement('dd', {}, data.is_explicit ? gettext('Yes') : gettext('No'))
            ),

            React.createElement('h3', {}, 'Items'),
            React.createElement(
                'p',
                {style: {padding: '0 10px'}},
                ngettextf(
                    'There is %d episode in this podcast.',
                    'There are %d episodes in this podcast.',
                    data.items.length
                )
            ),

            React.createElement(
                'table',
                {
                    style: {
                        border: '1px solid #eee',
                        'box-shadow': 'none',
                    },
                },
                React.createElement('thead', {},
                    React.createElement('tr', {},
                        React.createElement('th', {}, gettext('Episode Name')),
                        React.createElement('th', {}, gettext('Subtitle'))
                    )
                ),
                React.createElement('tbody', {},
                    data.items.slice(0, 10).map(function(i, j) {
                        return React.createElement('tr', {key: j},
                            React.createElement('td', {}, i.title),
                            React.createElement('td', nullStyle({}, i.subtitle), trunc(i.subtitle) || gettext('No Subtitle'))
                        )
                    })
                )
            ),
            data.items.length > 10 ? React.createElement(
                'p',
                {style: {'font-style': 'italic', 'padding-left': '10px'}},
                ngettextf('%d item not shown', '%d items not shown', data.items.length - 10)
            ) : null,
            !this.state.podcastData.__ignored_items ? null : React.createElement(
                'div',
                {className: 'warning'},
                ngettextf(
                    'Warning! We found %d item in your feed that did not have an <enclosure /> tag. There was no audio attached to this item, so we cannot import it.',
                    'Warning! We found %d items in your feed that did not have an <enclosure /> tag. There was no audio attached to these items, so we cannot import them.',
                    this.state.podcastData.__ignored_items
                )
            )

            // TODO: Show a warning if any of the files are too big for the user's account

        );
    },

    goToStep2_5: function() {
        this.setState({step: 2.5, step2error: null});
    },

    beginImport: function() {
        if (!this.state.slugValue || !this.state.slugValid) {
            this.setState({step2error: gettext('You must find an available slug before proceeding')});
            return;
        }
        this.setState({step: 3, step3process: 'submitting', step2error: null});

        var body = new FormData();
        for (var key in this.state.podcastData) {
            if (!this.state.podcastData.hasOwnProperty(key)) continue;
            if (key === 'items') continue;
            if (key.substr(0, 2) === '__') continue;
            body.append(key, this.state.podcastData[key]);
        }
        body.append('slug', this.state.slugValue);
        body.append('items', JSON.stringify(this.state.podcastData.items));
        this.req('post', '/dashboard/services/start_import', body, this.importStarted, this.importError);
    },

    importStarted: function(responseText) {
        var parsed = JSON.parse(responseText);
        if (parsed.error) {
            this.setState({step: 2, step2error: parsed.error});
            return;
        }
        this.setState({step3process: 'importing', step3ids: parsed.ids});

        var interval = setInterval(function() {
            if (this.state.step3xhr) return;
            var req = this.req(
                'get',
                '/dashboard/services/import_progress/' +
                    encodeURIComponent(this.state.slugValue) +
                    '?ids=' + encodeURIComponent(this.state.step3ids.join(',')),
                null,
                function(responseText) {
                    var parsed = JSON.parse(responseText);
                    this.setState({step3xhr: null, importPercent: parsed.status});
                    if (parsed.status === 100) {
                        clearTimeout(this.state.step3interval);
                        this.setState({
                            step3process: 'done',
                            step3interval: null,
                            step: 4,
                        });
                    }
                }.bind(this),
                function() {
                    this.setState({step3xhr: null});
                }.bind(this)
            );
        }.bind(this), 3000);
        this.setState({step3interval: interval});
    },
    importError: function() {
        this.setState({step: 2, step2error: gettext('There was an error while connecting to Pinecast')});
    },

    getStep3Progress: function() {
        switch (this.state.step3process) {
            case 'submitting':
                return 2;
            case 'importing':
                return Math.round(5 + 0.95 * this.state.importPercent);
            case 'done':
                return 100;
        }
        return 0;
    },
    getStep3ProgressText: function() {
        var text = 'Working...';
        switch (this.state.step3process) {
            case 'submitting':
                text = gettext('Submitting podcast import request to Pinecast...');
                break;
            case 'importing':
                text = gettext('Waiting for assets to import. Please be patient, this may take a few minutes to complete.');
                break;
            case 'done':
                text = gettext('Import completed');
                break;
            default:
                text = '¯\\_(ツ)_/¯';
        }
        return React.createElement('p', {}, text);
    },

    req: request,

});

var placeholders = document.querySelectorAll('.importer-placeholder');
Array.prototype.slice.call(placeholders).forEach(function(placeholder) {
    ReactDOM.render(
        React.createElement(PodcastImporter, {
            origElement: placeholder,
            csrf: placeholder.getAttribute('data-csrf'),
            rssFetch: placeholder.getAttribute('data-rss-fetch'),
        }),
        placeholder
    );
});

function ngettextf(singular, plural, count) {
    var value = ngettext(singular, plural, count);
    return value.replace(/%d/g, count);
}

}());
