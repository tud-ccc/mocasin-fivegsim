import os
import csv

from mocasin.tasks import parse_multirun


def fivegsim_stats_parser(dir):
    with open(os.path.join(dir, "stats.csv"), "r") as f:
        reader = csv.DictReader(f)
        keys = reader.fieldnames
        results = []
        for row in reader:
            results.append(row)
    return results, keys


def fiveg_missrate_parser(dir):
    results = {}
    try:
        with open(os.path.join(dir, "missrate.csv"), "r") as f:
            reader = csv.reader(f, delimiter=",")
            headers = next(reader)
            results = dict(zip(headers, next(reader)))
        return results, headers
    except FileNotFoundError:
        return {}, []


def initialize_stats_parser():
    parse_multirun._parsers.update(
        {
            "5g_stats_parser": (
                "fivegsim.stats_parser",
                "fivegsim_stats_parser",
                "Parses the statistics file from the 5G application.",
            ),
            "5g_missrate_parser": (
                "fivegsim.stats_parser",
                "fiveg_missrate_parser",
                "Parses the number of missed applications from a file",
            ),
        }
    )
