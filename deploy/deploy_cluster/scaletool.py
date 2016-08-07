#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import os.path
import sys
import logging

logging.getLogger("stevedore").setLevel(logging.ERROR)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import apps


LOG = logging.getLogger(__name__)


def main():
    parser = create_parser()
    parsed = parser.parse_args()
    app = parsed.callback(parsed)

    configure_logging(parsed.debug)

    try:
        app.do()
    except Exception as exc:
        LOG.exception("App failed: %s", exc)
        return os.EX_SOFTWARE

    return os.EX_OK


def create_parser():
    parser = argparse.ArgumentParser(
        description=(
            "This is a script to deploy OpenStack "
            "environments in scale lab. "
            "Please check subcommand help for details."))

    parser.add_argument(
        "-d", "--debug",
        help="Run script in debug mode.",
        action="store_true",
        default=False)
    parser.add_argument(
        "-c", "--db-connection",
        help="Database connection string for SQLAlchemy.",
        default="postgresql://rally:Ra11y@172.18.160.54/rally")

    parsers = parser.add_subparsers()
    for app in apps.all_apps():
        app.install_parser(parsers)

    return parser


def configure_logging(debug=True):
    level = logging.WARNING
    if debug:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format=(
            "%(asctime)-25s [%(levelname)5s] "
            "%(module)20s:%(lineno)-6d %(message)s"))

    if debug:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


if __name__ == "__main__":
    sys.exit(main())
