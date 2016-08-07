/**
 *
 * Created by shelbysturgis on 1/23/14.
 */

$(document).ready(function () {

    "use strict";
    var client = new elasticsearch.Client(
        {
            host: "http://" + window.location.hostname + ":9200"
        }
    );

    client.search({
        index: 'logstash-*',
        size: 10000,
        search_type: "count",
        body: {
            // Aggregate on the results
            aggs: {
                levels: {
                    terms: {
                        field: "level",
                        order: { "_term": "asc" }
                    }
                }
            }
            // End query.
        }
    }).then(function (resp) {
        console.log(resp);

        // D3 code goes here.
        var levels = resp.aggregations.levels.buckets;

        // d3 donut chart
        var width = 140,
            height = 140,
            radius = Math.min(width, height) / 2;

        var color = ['#ff7f0e', '#d62728', '#2ca02c', '#1f77b4'];

        var arc = d3.svg.arc()
                .outerRadius(radius)
        /*.innerRadius(120)*/;

        var pie = d3.layout.pie()
            .sort(null)
            .value(function (d) {
                return d.doc_count;
            });

        var svg = d3.select("#donut-chart").append("svg")
            .attr("width", width)
            .attr("height", height)
            .append("g")
            .attr("transform", "translate(" + width / 2 + "," + height / 2 + ")");

        var g = svg.selectAll(".arc")
            .data(pie(levels))
            .enter()
            .append("g")
            .attr("class", "arc");

        g.append("path")
            .attr("d", arc)
            .style("fill", function (d, i) {
                return  "#" + Math.round(Math.random() * 16 * 1024 * 1024).toString(16);
            });

        var levels_container = $("#levels_container");
        $.each(levels, function () {
            var kibana_link = "/kibana/#/dashboard/file/logstash.json?from=7d&query=level:" + this.key;
            levels_container.append($("<div>" + this.key + ": " + this.doc_count + "<span class='link'><a href='" + kibana_link +
                    "' target='_blank'>&#x2197;</a></div>"));
        });
    });

    client.search({
        index: 'logstash-*',
        body: {
            query: {
                // Boolean query for matching and excluding items.
                bool: {
                    must: { match: { "level": "error" }}
                }
            },
            // Aggregate on the results
            aggs: {
                sources: {
                    terms: {
                        field: "source_type",
                        order: { "_term": "asc" }
//                    },
//                    aggs: {
//                        contents: {
//                            terms: {
//                                field: "content"
//                            }
//                        }
                    }
                }
            }
        }
    }).then(function (resp) {
        console.log(resp);
    });

    $.get("/queries.yaml", function (data) {
        var queries = jsyaml.safeLoad(data);
        $.each(queries, function () {
            var title = this.title;
            var link = this.link;
            var query = this.query;
            var kibana_link = "/kibana/#/dashboard/file/logstash.json?from=7d&query=" + query;
            var ext_link = link ? "<a href=" + link + " target='_blank'>Info&#x2197;</a>" : "";

            var queries_container = $("#queries_container");

            var counter_block = $('<div class="counter"></div>');
            var query_block = $('<div class="query_block"></div>');

            query_block
                .append($('<div><span class="query_title">' + title +
                    '</span><span class="link"><a href="' + kibana_link +
                    '" target="_blank">Kibana&#x2197;</a></span><span class="link">' + ext_link + '</span></div>'))
                .append($('<div class="query"><b>Query:</b>' + query + '</div>'));

            var block = $("<div style='margin-top: 16pt;'/>")
                .append(counter_block)
                .append(query_block);

            queries_container.append(block);

            client.search({
                index: 'logstash-*',
                body: {
                    query: {
                        query_string: {
                            query: query
                        }
                    }
                }
            }).then(function (resp) {
                console.log(resp);
                var hits = resp.hits.total;
                counter_block.append($("<div class='counter_text'>" + hits + "</div>"));
                counter_block.addClass(hits ? "red" : "green");

                var unique = [];

                $.each(resp.hits.hits, function () {
                    var item = this._source;
                    var time = "<span style='color: #804040;'>" + item["@timestamp"] + "</span>&nbsp;";
                    var text = "";
                    if (item.message) {
                        text += item.message;
                    } else if (item.source == "haproxy") {
                        text += "backend: " + item.node + "/" + item.backend_name + ", req: " + item.http_verb + " " + item.http_request;
                    } else {
                        text += JSON.stringify(this._source);
                    }
                    if (!unique[text]) {
                        query_block.append($('<div class="message">&#x273C; ' + time + ' ' + text + '</div>'));
                        unique[text] = true;
                    }
                });
            });

        });

    }).fail(function () {
    });

});
