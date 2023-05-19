import os

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
tr.result > td.pass {
  background: lightgreen;
}
tr.result > td.fail {
  background: pink;
}
tr.result > td.xfail {
  background: orange;
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
  package includes built-in support for the following known SDMX REST data sources.
</p>
<p>Notes:</p>
{% set run_url=env["GITHUB_REPOSITORY"] + "/actions/runs/" + env["GITHUB_RUN_ID"] %}
<ol>
  <li>
    Sources for which only the <code>data</code> resource is tested are those supporting
    SDMX-JSON only. Although the SDMX-JSON standard <em>does</em> specify formats for
    JSON structure messages, <code>sdmx1</code>—and most existing SDMX-JSON-only
    sources—support only data queries.
  </li>
  <li>
    If this run was triggered on GitHub Actions, complete logs may be available <a
    href="https://github.com/{{ run_url }}">here</a>.
  </li>
</ol>
<table>
<thead>
  <tr>
    <th>Source</td>
    {% for resource in resources %}
    <th class="rotate"><div>{{ resource.name }}</div></td>
    {% endfor %}
  </tr>
</thead>
{% for source_id, results in data.items() %}
<tr class="result">
  <td><strong>{{ source_id }}</strong></td>
  {% for resource in resources %}
  {% set result = results.get(resource) %}
  <td class="{{ result }}">{{ abbrev.get(result) }}</td>
  {% endfor %}
</tr>
{% endfor %}
</table>

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
  <td class="xfail">✔</td>
  <td style="text-align: left">
    <p>Known/expected failure. See GitHub for any related issue(s).</p>
    <p>Includes the case where the data source is known to not implement this resource,
    but replies incorrectly with a 4XX (error) HTTP status code instead of a 501.</p>
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
</body>
</html>
"""
)

ABBREV = {
    "not-implemented": "",
    "pass": "✔",
    "xfail": "✔",
    "fail": "✘",
    None: "—",
}


class ServiceReporter:
    def __init__(self, config):
        self.path = config.invocation_params.dir.joinpath("sources", "index.html")
        self.path.parent.mkdir(exist_ok=True)
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
                result = str(call.excinfo.type)
        except AttributeError:
            result = "pass"

        self.resources.add(endpoint)
        self.data[source_id][endpoint] = result

    def pytest_sessionfinish(self, session, exitstatus):
        if not self.data:
            return
        with open(self.path, "w") as f:
            f.write(
                TEMPLATE.render(
                    data=self.data,
                    abbrev=ABBREV,
                    resources=sorted(self.resources),
                    env=dict(GITHUB_REPOSITORY="", GITHUB_RUN_ID="") | os.environ,
                )
            )
