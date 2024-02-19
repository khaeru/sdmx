import json
import os
from itertools import chain
from pathlib import Path
from typing import Dict, Optional

from jinja2 import Template

TEMPLATE = Template(
    """
<html>
<head>
<style>
body {
  font-family: sans-serif;
}
th.rotate {
  height: 140px;
  white-space: nowrap;
}
th.rotate > div {
  transform: translate(10px, 51px) rotate(315deg);
  width: 30px;
}
tr.result > td {
  height: 30px;
  text-align: center;
}
tr.result > td.source {
  font-weight: bold;
  text-align: right;
}
tr.result > td.pass {
  background: lightgreen;
}
tr.result > td.fail {
  background: pink;
}
tr.result > td.xfail {
  background: tan;
}
tr.result > td.not-implemented {
  background: lightgrey;
}
</style>
</head>
<body>
<h1>SDMX data sources</h1>
<p>
  This page shows the results of automatic tests run for the <a
  href="https://github.com/khaeru/sdmx"><code>sdmx1</code></a> Python package. The
  package includes built-in support for the following known SDMX REST data sources and
  API endpoints.
</p>
<p>Notes:</p>
{% set run_url=env["GITHUB_REPOSITORY"] + "/actions/runs/" + env["GITHUB_RUN_ID"] %}
<ol>
  <li>
    Sources for which only the <code>data</code> resource is tested are those supporting
    SDMX-JSON only. Although the SDMX-JSON standard <em>does</em> specify formats for
    JSON structure messages, <code>sdmx1</code>—and most existing SDMX-JSON–only
    sources—support only data queries.
  </li>
  <li>
    Further information about <code>sdmx1</code> support for each source is available in
    the <a href="https://sdmx1.readthedocs.io/en/latest/sources.html">documentation</a>.
  </li>
  <li>
    A JSON version of these data is available <a href="./all-data.json">here</a>.
  </li>
  <li>
    If this run was triggered on GitHub Actions, complete logs may be available <a
    href="https://github.com/{{ run_url }}">here</a>.
  </li>
</ol>

<p>Table key:</p>
<table>
<tr class="result">
  <td class="pass">✔</td>
  <td style="text-align: left">Pass.</td>
</tr>
<tr class="result">
  <td class="fail">✘</td>
  <td style="text-align: left">Unexpected failure.</td>
</tr>
<tr class="result">
  <td class="xfail"> </td>
  <td style="text-align: left">
    <p>
      Known/expected failure. See GitHub for
      <a href="https://github.com/khaeru/sdmx/labels/data-source">any related issue(s)<a>.
    </p>
    <p>Includes the case where the data source is known to not implement this API
    endpoint, but replies incorrectly with a 4XX (error) HTTP status code instead of
    501.</p>
  </td>
</tr>
<tr class="result">
  <td class="not-implemented"></td>
  <td style="text-align: left">
    Data source does not implement this resource and replies correctly to queries with
    a 501 HTTP status code and/or message.
  </td>
</tr>
<tr class="result">
  <td>—</td>
  <td style="text-align: left">No test for this source and resource.</td>
</tr>
</table>

<table>
<thead>
  <tr>
    <th>Source</td>
    {% for resource in resources %}
    <th class="rotate"><div>{{ resource }}</div></td>
    {% endfor %}
  </tr>
</thead>
{% for source_id, results in data.items() | sort %}
<tr class="result">
  <td class="source">{{ source_id }}</td>
  {% for resource in resources %}
  {% set result = results.get(resource) %}
  {% if result in abbrev %}
  <td class="{{ result }}">{{ abbrev.get(result) }}</td>
  {% else %}
  <td class="fail"><abbr title="{{result}}">{{ abbrev.get("fail") }}</abbr></td>
  {% endif %}
  {% endfor %}
</tr>
{% endfor %}
</table>

</body>
</html>
"""
)

ABBREV = {
    "not-implemented": "",
    "pass": "✔",
    "xfail": "",
    "fail": "✘",
    None: "—",
}


class ServiceReporter:
    """Report tests of individual data sources."""

    def __init__(self, config):
        self.data = {}
        self.resources = set()

    def pytest_runtest_makereport(self, item, call):
        try:
            assert call.when == "call"
            source_id = item.cls.source_id
            endpoint = item.funcargs["endpoint"]
        except (AssertionError, AttributeError, KeyError):
            return

        self.data.setdefault(source_id, dict())

        # Compile a list of exception classes associated with xfail marks
        xfail_classes = []
        for m in filter(lambda m: m.name == "xfail", item.own_markers):
            try:
                xfail_classes.extend(m.kwargs["raises"])  # Sequence of classes
            except TypeError:
                xfail_classes.append(m.kwargs["raises"])  # Single exception class

        try:
            if call.excinfo.type is NotImplementedError:
                result = "not-implemented"
            elif xfail_classes:
                result = "xfail" if call.excinfo.type in xfail_classes else "fail"
            else:
                result = repr(call.excinfo.value)
        except AttributeError:
            result = "pass"

        self.data[source_id][endpoint] = result

    def pytest_sessionfinish(self, session, exitstatus):
        """Write results for each source to a separate JSON file."""
        # Base path for all output
        base_path = session.config.invocation_params.dir.joinpath("source-tests")
        base_path.mkdir(exist_ok=True)

        # Distinct file name suffix for each worker if using pytest-xdist
        pxw = os.environ.get("PYTEST_XDIST_WORKER")
        suffix = "" if pxw is None else f"-{pxw}"

        for source_id, data in self.data.items():
            # File path for this particular source & worker
            path = base_path.joinpath(source_id + suffix).with_suffix(".json")
            # Dump the data for this source only
            with open(path, "w") as f:
                json.dump({source_id: data}, f)


def main(base_path: Optional[Path] = None):
    """Collate results from multiple JSON files."""
    base_path = base_path or Path.cwd().joinpath("source-tests")

    # Locate, read, and merge JSON files
    data: Dict[str, Dict[str, str]] = {}
    for path in base_path.glob("**/*.json"):
        # Update `data` with the file contents
        with open(path) as f:
            for source_id, source_data in json.load(f).items():
                data.setdefault(source_id, {}).update(source_data)

    with open(base_path.joinpath("all-data.json"), "w") as f:
        json.dump(data, f)

    # Compile list of resources that were tested
    resources = set(chain(*[v.keys() for v in data.values()]))

    # Render and write report
    base_path.joinpath("index.html").write_text(
        TEMPLATE.render(
            data=data,
            abbrev=ABBREV,
            resources=sorted(resources),
            env=dict(GITHUB_REPOSITORY="", GITHUB_RUN_ID="") | os.environ,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":  # pragma: no cover
    main(Path.cwd().joinpath("source-tests"))
