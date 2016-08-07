#!/usr/bin/env python

from datetime import datetime
import mock
import os

from generate_summary_report import generate_summary_report as generator
from self_tests import base


class SummaryReportTestCase(base.BaseTestCase):

    def _test__parse_filename(self, executor, job_os):
        build = "6.0.1-703-2015-01-02"
        job_id = "env_10-28"

        start_datetime = datetime(year=2015, month=1, day=3,
                                  hour=4, minute=26, second=3)
        end_datetime = datetime(year=2015, month=1, day=3,
                                hour=5, minute=13, second=4)

        path = (
            "build_%(build)s_"
            "11-57-41/jenkins-run_%(executor)s_%(job_id)s-%(os)s-MSK-"
            "%(start_date)s-%(end_date)s" % {
                "build": build,
                "executor": executor, "job_id": job_id, "os": job_os,
                "start_date": start_datetime.strftime("%Y-%m-%d-%H:%M:%S"),
                "end_date": end_datetime.strftime("%Y-%m-%d-%H:%M:%S")})

        filename = os.path.join(generator.EXECUTION_RESULTS, path)

        parsed_data = generator._parse_filename(filename)

        self.assertEqual(build, parsed_data["build"])
        self.assertEqual(executor, parsed_data["executor"])
        self.assertEqual("run_%s_%s" % (executor, job_id),
                         parsed_data["jenkins_job"]["name"])
        self.assertEqual(
            "%(url)s:8080/job/run_%(executor)s_%(job_id)s" % {
                "url": generator.HOSTNAME, "executor": executor,
                "job_id": job_id.replace("-", "/")},
            parsed_data["jenkins_job"]["url"])
        self.assertEqual(start_datetime.strftime("%Y/%m/%d %H:%M:%S"),
                         parsed_data["job_start_date"])
        self.assertEqual(end_datetime.strftime("%Y/%m/%d %H:%M:%S"),
                         parsed_data["job_end_date"])
        self.assertEqual(
            os.path.join(generator.HOSTNAME, "test_results", path),
            parsed_data["results_url"])

    def test__parse_filename_with_rally_executor(self):
        self._test__parse_filename("rally", "centos")

    def test__parse_filename_with_tempest_executor(self):
        self._test__parse_filename("tempest", "bolgenOS")

    @mock.patch("generate_summary_report.generate_summary_report.xunitparser")
    @mock.patch("__builtin__.open", mock.mock_open())
    def test__parse_junit(self, mock_xunitparser):
        class TS(object):
            test_cases = 40

            def countTestCases(self):
                return self.test_cases

            def __iter__(self):
                return self

            def next(self):
                raise StopIteration

        class TR(object):
            failures = ["first_failure", "second_failure"]
            skipped = []
            errors = ["some_error"]

        mock_xunitparser.parse.return_value = (TS(), TR())

        parsed_data = generator._parse_junit("some_file")

        self.assertEqual(TS.test_cases, parsed_data["tests"])
        self.assertEqual(len(TR.failures), parsed_data["failures"])
        self.assertEqual(len(TR.skipped), parsed_data["skipped"])
        self.assertEqual(len(TR.errors), parsed_data["errors"])

    def test__get_node_number(self):
        root = "some_root"
        number_of_nodes = "1000000"
        with mock.patch("__builtin__.open", mock.mock_open()) as mock_open:
            mock_open.return_value.read.return_value = number_of_nodes + "\n"
            self.assertEqual(number_of_nodes, generator._get_node_number(root))
            mock_open.assert_called_once_with(
                os.path.join(root, "number_of_nodes"), "r")

    def test__get_node_number_from_not_exist_file(self):
        root = "some_root"
        mock_open = mock.MagicMock(side_effect=IOError)
        with mock.patch("__builtin__.open", mock_open):
            self.assertEqual("no info", generator._get_node_number(root))
        mock_open.assert_called_once_with(
            os.path.join(root, "number_of_nodes"), "r")

    @mock.patch("generate_summary_report.generate_summary_report."
                "_get_node_number")
    @mock.patch("generate_summary_report.generate_summary_report."
                "_parse_executor_settings")
    @mock.patch("generate_summary_report.generate_summary_report."
                "_parse_cluster_settings")
    @mock.patch("generate_summary_report.generate_summary_report."
                "_parse_junit")
    @mock.patch("generate_summary_report.generate_summary_report."
                "_parse_filename")
    @mock.patch("generate_summary_report.generate_summary_report."
                "_listdir")
    def test_get_tests(self, mock_listdir, mock_parse_filename,
                       mock_parse_junit, mock_parse_cluster_settings,
                       mock_parse_executor_settings, mock_get_node_number):
        job_end_date = "2013"

        def fake_parse_filename(filename):
            parsed_data = {"job_end_date": job_end_date,
                           "executor": "unknown"}
            if filename.find("rally") > -1:
                parsed_data["executor"] = "rally"
            elif filename.find("tempest") > -1:
                parsed_data["executor"] = "tempest"

            return parsed_data

        mock_parse_filename.side_effect = fake_parse_filename
        mock_parse_junit.return_value = {"some_junit_info": "some_value"}
        mock_parse_cluster_settings.return_value = {"components": "components",
                                                    "storage": "storage_info",
                                                    "job_os": ""}
        mock_parse_executor_settings.return_value({})
        mock_get_node_number.return_value = "777"

        file_1 = "rally-report.html"
        file_2 = "tempest-report.html"
        file_3 = "rally-report.xml"

        mock_listdir.return_value = {
            "%s-rally" % generator.EXECUTION_RESULTS: [file_1, file_3],
            "%s-tempest" % generator.EXECUTION_RESULTS: [file_2]
        }
        tests = generator.get_tests()
        self.assertEqual(2, len(tests.keys()))
        self.assertItemsEqual(
            [mock.call(k) for k in mock_listdir.return_value],
            mock_parse_cluster_settings.call_args_list)
        self.assertEqual(
            [dict(
                {"executor": "rally", "job_end_date": job_end_date,
                 "components": mock_parse_cluster_settings()["components"],
                 "storage": mock_parse_cluster_settings()["storage"],
                 "job_nodes": mock_get_node_number.return_value}.items() +
                mock_parse_junit.return_value.items())],
            tests.get("rally"))
        self.assertEqual(
            [dict(
                {"executor": "tempest", "job_end_date": job_end_date,
                 "components": mock_parse_cluster_settings()["components"],
                 "storage": mock_parse_cluster_settings()["storage"],
                 "job_nodes": mock_get_node_number.return_value}.items() +
                mock_parse_junit.return_value.items())],
            tests.get("tempest"))

        self.assertEqual(
            [mock.call(key) for key in mock_listdir.return_value],
            mock_parse_filename.call_args_list)
        self.assertItemsEqual(
            [mock.call(
                "%s-rally/rally-report.xml" % generator.EXECUTION_RESULTS),
             mock.call(
                 "%s-tempest/tempest-report.xml" % generator.EXECUTION_RESULTS)
             ], mock_parse_junit.call_args_list)
        self.assertEqual(
            [mock.call(k) for k in mock_listdir.return_value],
            mock_get_node_number.call_args_list)

    def test__generate_plot(self):
        graph = mock.MagicMock()
        key = "tests"
        tests = [{key: mock.MagicMock()}, {key: mock.MagicMock()}]
        title = "some_title"
        color = "some_color"

        generator._generate_plot(graph, title, color, tests, key)
        graph.fill_between.assert_called_once_with(
            range(0, len(tests)), 0, [t[key] for t in tests],
            facecolor=color, interpolate=True)
        graph.set_title.assert_called_once_with(title)
        graph.set_xlim.assert_called_once_with([0, len(tests) - 1])

    @mock.patch("generate_summary_report.generate_summary_report.plt")
    @mock.patch("generate_summary_report.generate_summary_report."
                "_generate_plot")
    def test_generate_plots(self, mock_genplot, mock_plt):
        executor = "rally"

        fake_fig = mock.MagicMock()
        fake_graphs = [mock.MagicMock(), mock.MagicMock(), mock.MagicMock()]
        mock_plt.subplots.return_value = (fake_fig, fake_graphs)

        fake_tests = {executor: [
            {"failures": 2,
             "skipped": 2},
            {"failures": 2,
             "skipped": 2},
        ]}

        generator.generate_plots(fake_tests, executor)

        mock_plt.subplots.assert_called_once_with(3, 1, sharex=True)
        mock_plt.savefig.assert_called_once_with(
            "%s/%s" % (generator.EXECUTION_RESULTS, executor))

        # NOTE: if _generate_plot is called 3 times, it means that
        # _generate_plot is called for all, skipped and failed tests.
        self.assertEqual(3, mock_genplot.call_count)

    @mock.patch("generate_summary_report.generate_summary_report."
                "generate_html")
    @mock.patch("generate_summary_report.generate_summary_report."
                "generate_plots")
    @mock.patch("generate_summary_report.generate_summary_report."
                "get_tests")
    @mock.patch("generate_summary_report.generate_summary_report."
                "_import_matplotlib")
    def test_main_success(self, mock_import, mock_get_tests, mock_genplots,
                          mock_genhtml):
        mock_import.return_value = 0

        generator.main()

        self.assertEqual(
            [mock.call(mock_get_tests.return_value, "tempest"), mock.call(
                mock_get_tests.return_value, "rally", display_skipped=False)],
            mock_genplots.call_args_list)
        mock_genhtml.assert_called_once_with(mock_get_tests.return_value)

    @mock.patch("generate_summary_report.generate_summary_report."
                "generate_html")
    @mock.patch("generate_summary_report.generate_summary_report."
                "generate_plots")
    @mock.patch("generate_summary_report.generate_summary_report."
                "get_tests")
    @mock.patch("generate_summary_report.generate_summary_report."
                "_import_matplotlib")
    def test_main_failed(self, mock_import, mock_get_tests, mock_genplots,
                         mock_genhtml):
        mock_import.return_value = 1

        self.assertEqual(mock_import.return_value, generator.main())

        self.assertFalse(mock_get_tests.called)
        self.assertFalse(mock_genplots.called)
        self.assertFalse(mock_genhtml.called)
