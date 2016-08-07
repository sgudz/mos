<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Ceilometer benchmark report</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.13-beta/nv.d3.min.css"
          rel="stylesheet"
          type="text/css" />
    <link href="https://cdn.datatables.net/1.10.0/css/jquery.dataTables.css"
          rel="stylesheet"
          type="text/css" />

    <!-- Remove jQuery and use d3.select in futuer -->
    <script type="text/javascript"
            src="https://cdnjs.cloudflare.com/ajax/libs/jquery/2.1.0/jquery.min.js"
            charset="utf-8">
    </script>
    <script type="text/javascript"
            src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.4.1/d3.min.js"
            charset="utf-8">
    </script>
    <script type="text/javascript"
            src="https://cdnjs.cloudflare.com/ajax/libs/nvd3/1.1.13-beta/nv.d3.min.js"
            charset="utf-8">
    </script>
    <script type="text/javascript"
            src="https://cdn.datatables.net/1.10.0/js/jquery.dataTables.js"
            charset="utf-8">
    </script>

    <style>
        #results svg{
          height: 350px;
          width: 650px;
          float: left;
        }
        #results {
            min-width: 1000px;
            overflow: scroll;
        }
    </style>

    <script>
        var DATA = ${data}

         function draw_stacked(where, source, yaxis_label, max_y){
            nv.addGraph(function() {

                var chart = nv.models.lineChart()
                .margin({left: 100})  //Adjust chart margins to give the x-axis some breathing room.
                .useInteractiveGuideline(true)  //We want nice looking tooltips and a guideline!
                .transitionDuration(350)  //how fast do you want the lines to transition?
                .showLegend(true)       //Show the legend, allowing users to turn on/off line series.
                .showYAxis(true)        //Show the y-axis
                .showXAxis(true)
                .x(function(d) { return d[0]})
                .y(function(d) { return d[1]})
                .clipEdge(true)
                .forceY([0,max_y]);

                chart.yAxis
                    .axisLabel(yaxis_label)
                    .showMaxMin(true)
                    .tickFormat(d3.format(',.2f'));

                chart.xAxis
                    .axisLabel("Duration in seconds")
                    .tickFormat(d3.format('d'));

                d3.select(where)
                    .datum(source)
                    .transition().call(chart);

                nv.utils.windowResize(chart.update);

                return chart;
            });
        }

        function draw(data, where){
            draw_stacked(where, function(){
                return data["value"]
            }, data['yaxis_label'], data['max_y'])
        }

        $(function(){
            for (var index in DATA) {
               (function(d){
                    where = "#results ." + d['name']
                    draw(d, where)
               })(DATA[index])
            }
        })
    </script>

</head>
    <body>
        <div id="title"> 
            <h2>Ceilometer test results</h2>
        </div>
        ${divs}

    </body>
</html>
