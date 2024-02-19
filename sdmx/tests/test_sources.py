"""Tests against the actual APIs for specific data sources.

HTTP responses from the data sources are cached in tests/data/cache.
To force the data to be retrieved over the Internet, delete this directory.
"""
# TODO add a pytest argument for clearing this cache in conftest.py
import logging
from pathlib import Path
from typing import Any, Dict, Tuple, Type, Union

import pytest
import requests_mock

import sdmx
from sdmx import Client
from sdmx.exceptions import HTTPError, XMLParseError

log = logging.getLogger(__name__)


NI = "Not implemented in sdmx1"


class DataSourceTest:
    """Base class for data source tests."""

    # TODO also test structure-specific data

    #: Must be one of the IDs in sources.json.
    source_id: str

    #: Failures affecting **all** data sources, internal to :mod:`sdmx`.
    xfail_common: Dict[str, Any] = {}

    #: Mapping of endpoint → Exception subclass. Tests of these endpoints are expected
    #: to fail with the given kind of exception.
    xfail: Dict[str, Union[Type[Exception], Tuple[Type[Exception], str]]] = {}

    #: True to xfail if a 503 Error is returned.
    tolerate_503 = False

    #: Keyword arguments for particular endpoints.
    endpoint_args: Dict[str, Dict[str, Any]] = {}

    @pytest.fixture
    def cache_path(self, test_data_path):
        # Use a common cache file for all agency tests
        (test_data_path / ".cache").mkdir(exist_ok=True)

        yield test_data_path / ".cache" / self.source_id

    @pytest.fixture
    def client(self, cache_path):
        from sdmx.util import HAS_REQUESTS_CACHE

        if HAS_REQUESTS_CACHE:
            kw = dict(cache_name=str(cache_path), backend="sqlite")
        else:
            kw = {}

        return Client(self.source_id, **kw)

    # NB the following can be added to any subclass below for SSL failures. Update the
    #    docstring to describe the nature of the problem.
    # @pytest.fixture
    # def client(self, cache_path):
    #     """Identical to DataSourceTest, except skip SSL certificate verification.
    #
    #     As of [DATE], this source returns an invalid certificate.
    #     """
    #     return Client(
    #         self.source_id, cache_name=str(cache_path), backend="sqlite", verify=False
    #     )

    @pytest.mark.source
    @pytest.mark.network
    def test_endpoint(self, pytestconfig, cache_path, client, endpoint, args):
        # See sdmx.testing._generate_endpoint_tests() for values of `endpoint`
        cache = cache_path.with_suffix(f".{endpoint.name}.xml")

        message = client.get(endpoint, tofile=cache, **args)

        if pytestconfig.getoption("verbose"):
            print(repr(message))
            if endpoint == "dataflow":
                # Display the IDs of data flows; this can be used to identify targets
                # for tests of the data endpoint for a particular source
                for dfd in message.dataflow:
                    print(repr(dfd))

        # For debugging
        # print(cache, cache.read_text(), result, sep="\n\n")
        # assert False

        # All parsed contents can also be converted to pandas
        sdmx.to_pandas(message)


class TestMOCK(DataSourceTest):
    source_id = "MOCK"

    endpoint_args = {
        "schema": dict(context="datastructure"),
    }

    xfail = {
        "metadata": NotImplementedError,  # In .rest.v21.URL.handle_metadata()
        "registration": ValueError,  # In .rest.v21.URL.handle_registration()
    }

    @pytest.fixture(scope="class")
    def client(self, mock_service_adapter):
        """Return a client with mocked responses."""

        c = Client(self.source_id)
        c.session.mount("mock://", mock_service_adapter)

        yield c

    # Same as above, but without the "source" or "network" marks
    def test_endpoint(self, client, endpoint, args):
        client.get(endpoint, **args)


class TestABS(DataSourceTest):
    source_id = "ABS"

    endpoint_args = {
        "data": dict(
            resource_id="ABS,ANA_AGG,1.0.0",
            key="....Q",
            params=dict(startPeriod="2020-Q1", endPeriod="2022-Q4"),
        )
    }


class TestABS_JSON(DataSourceTest):
    source_id = "ABS_JSON"

    endpoint_args = {
        "data": dict(
            resource_id="ABS,ANA_AGG,1.0.0",
            key="....Q",
        )
    }


class TestBBK(DataSourceTest):
    source_id = "BBK"

    # See https://github.com/khaeru/sdmx/issues/82
    xfail = {
        "codelist": XMLParseError,
        "datastructure": XMLParseError,
    }

    endpoint_args = {
        "data": dict(
            resource_id="BBDB2",
            key="H.DE.Y.A.C.IFRS.B.A.K.E.E001.VGH.A",
            params=dict(startPeriod="2017-S1", endPeriod="2019-S1"),
        ),
        "codelist": dict(
            resource_id="CL_BBK_ERX_RATE_TYPE", params=dict(references="none")
        ),
        "conceptscheme": dict(
            resource_id="CS_BBK_ERX",
            params=dict(detail="allstubs", references="parentsandsiblings"),
        ),
        "dataflow": dict(resource_id="BBEX3", params=dict(detail="referencestubs")),
        "datastructure": dict(resource_id="BBK_QFS"),
    }


class TestBIS(DataSourceTest):
    source_id = "BIS"

    endpoint_args = {
        "actualconstraint": dict(resource_id="CBP_D_24D"),
    }


class TestECB(DataSourceTest):
    source_id = "ECB"


# Data for requests_mock; see TestESTAT.mock()
estat_mock = {
    "http://ec.europa.eu/eurostat/SDMX/diss-web/rest/data/nama_10_gdp/..B1GQ+P3.": {
        "body": Path("ESTAT", "footer2.xml"),
        "headers": {
            "Content-Type": "application/vnd.sdmx.genericdata+xml; version=2.1"
        },
    },
    "http://ec.europa.eu/eurostat/SDMX/diss-web/file/7JUdWyAy4fmjBSWT": {
        # This file is a trimmed version of the actual response for the above query
        "body": Path("ESTAT", "footer2.zip"),
        "headers": {"Content-Type": "application/octet-stream"},
    },
}


class TestESTAT(DataSourceTest):
    source_id = "ESTAT"

    @pytest.fixture
    def mock(self, test_data_path):
        # Prepare the mock requests
        fixture = requests_mock.Mocker()
        for url, args in estat_mock.items():
            # str() here is for Python 3.5 compatibility
            args["body"] = open(str(test_data_path / args["body"]), "rb")
            fixture.get(url, **args)

        return fixture

    @pytest.mark.network
    def test_xml_footer(self, mock):
        client = Client(self.source_id)

        with mock:
            msg = client.get(url=list(estat_mock.keys())[0], get_footer_url=(1, 1))

        assert len(msg.data[0].obs) == 43

    @pytest.mark.network
    def test_ss_data(self, client):
        """Test a request for structure-specific data.

        Examples from:
        https://ec.europa.eu/eurostat/web/sdmx-web-services/example-queries
        """
        df_id = "NAMA_10_GDP"
        args = dict(resource_id=df_id)

        # Query for the DSD
        dsd = client.dataflow(**args).dataflow[df_id].structure

        # Even with ?references=all, ESTAT returns a short message with the DSD as an
        # external reference. Query again to get its actual contents.
        if dsd.is_external_reference:
            dsd = client.get(resource=dsd).structure[0]
            log.info(repr(dsd))

        assert not dsd.is_external_reference

        # Example query, using the DSD already retrieved
        args.update(
            dict(
                key=dict(unit=["CP_MEUR"], na_item=["B1GQ"], geo=["LU"]),
                params={"startPeriod": "2012", "endPeriod": "2015"},
                dsd=dsd,
                # commented: for debugging
                # tofile="temp.xml",
            )
        )
        client.data(**args)

    @pytest.mark.network
    def test_gh_116(self, caplog, cache_path, client):
        """Test of https://github.com/khaeru/sdmx/issues/116.

        As of 2024-02-13, the actual web service no longer returns multiple versions of
        the same artefacts for this query.

        See also
        --------
        .test_reader_xml.test_gh_116
        """
        msg = client.get(
            "dataflow", "GOV_10Q_GGNFA", params=dict(detail="referencepartial")
        )

        if cl1 := msg.codelist.get("ESTAT:GEO(13.0)"):  # pragma: no cover
            # Both versions of the GEO codelist are accessible in the message
            cl2 = msg.codelist["ESTAT:GEO(13.1)"]

            # cl1 is complete and items are available
            assert not cl1.is_partial and 0 < len(cl1)
            # cl2 is partial, and fewer codes are included than in cl1
            assert cl2.is_partial and 0 < len(cl2) < len(cl1)
        else:
            assert msg.codelist["GEO"]

        if cl3 := msg.codelist.get("ESTAT:UNIT(15.1)"):  # pragma: no cover
            # Both versions of the UNIT codelist are accessible in the message
            cl4 = msg.codelist["ESTAT:UNIT(15.2)"]

            # cl3 is complete and items are available
            assert not cl3.is_partial and 0 < len(cl3)
            # cl4 is partial, and fewer codes are included than in cl1
            assert cl4.is_partial and 0 < len(cl4) < len(cl3)
        else:
            assert msg.codelist["UNIT"]


class TestESTAT3(DataSourceTest):
    source_id = "ESTAT3"

    # Examples from
    # https://wikis.ec.europa.eu/display/EUROSTATHELP/API+-+Getting+started+with+SDMX3.0+API
    endpoint_args = {
        "codelist": dict(resource_id="FREQ"),
        "conceptscheme": dict(resource_id="TESEM160"),
        "data": dict(
            context="dataflow", resource_id="ISOC_CI_ID_H", last_n_observations=100
        ),
        "dataflow": dict(resource_id="ISOC_CI_ID_H", version="1.0"),
        "datastructure": dict(resource_id="PRC_DAP13", params=dict(references="none")),
    }


class TestESTAT_COMEXT(DataSourceTest):
    source_id = "ESTAT_COMEXT"

    endpoint_args = {
        "data": dict(
            resource_id="DS-059271",
            params=dict(startPeriod="2023"),
        ),
    }


class TestCOMP(DataSourceTest):
    source_id = "COMP"

    endpoint_args = {
        "data": dict(resource_id="AID_RAIL"),
        "dataflow": dict(resource_id="AID_SCB_OBJ"),
    }


class TestEMPL(DataSourceTest):
    source_id = "EMPL"

    endpoint_args = {
        "data": dict(resource_id="LMP_IND_EXP"),
        "dataflow": dict(resource_id="LMP_IND_EXP"),
    }


class TestGROW(DataSourceTest):
    source_id = "GROW"

    endpoint_args = {
        "data": dict(resource_id="POST_CUBE1_X"),
        "dataflow": dict(resource_id="POST_CUBE1_X"),
    }


class TestILO(DataSourceTest):
    source_id = "ILO"
    xfail = {
        "agencyscheme": HTTPError,  # 400
        # TODO provide endpoint_args for the following 3 to select 1 or a few objects
        "codelist": HTTPError,  # 413 Client Error: Payload Too Large
        "contentconstraint": HTTPError,  # 413 Client Error: Payload Too Large
        "datastructure": HTTPError,  # 413 Client Error: Payload Too Large
        "organisationscheme": HTTPError,  # 400
        "structure": HTTPError,  # 400
        "structureset": NotImplementedError,  # 501
    }

    @pytest.mark.network
    def test_codelist(self, cache_path, client):
        client.get(
            "codelist", "CL_ECO", tofile=cache_path.with_suffix("." + "codelist-CL_ECO")
        )

    @pytest.mark.network
    def test_gh_96(self, caplog, cache_path, client):
        """Test of https://github.com/khaeru/sdmx/issues/96.

        As of 2024-02-13, the web service no longer has the prior limitations on
        the `references` query parameter, so the special handling is removed.
        """
        client.get("codelist", "CL_ECO", params=dict(references="parentsandsiblings"))

        # As of 2024-02-13, no longer needed
        # assert (
        #     "ILO does not support references='parentsandsiblings'; discarded"
        #     in caplog.messages
        # )


class TestIMF(DataSourceTest):
    source_id = "IMF"


class TestINEGI(DataSourceTest):
    source_id = "INEGI"

    xfail = {
        "organisationscheme": HTTPError,  # 400
        "structure": NotImplementedError,  # 501
        "structureset": NotImplementedError,  # 501
    }

    endpoint_args = dict(
        # 404 Not Found when the own source's ID ("INEGI") is used
        conceptscheme=dict(provider="ALL")
    )


class TestINSEE(DataSourceTest):
    source_id = "INSEE"

    xfail = {
        "agencyscheme": HTTPError,  # 400
        "contentconstraint": HTTPError,  # 400
        "organisationscheme": HTTPError,  # 400
        "structure": HTTPError,  # 400
        "structureset": HTTPError,  # 400
    }


class TestISTAT(DataSourceTest):
    source_id = "ISTAT"
    xfail = {
        "organisationscheme": HTTPError,  # 400
        "structure": NotImplementedError,  # 501
    }
    endpoint_args = {
        "actualconstraint": dict(resource_id="CONS_92_143"),
    }

    @pytest.mark.network
    def test_gh_75(self, client):
        """Test of https://github.com/dr-leo/pandaSDMX/pull/75.

        - As of the original report on 2019-06-02, the 4th dimension was ``TIPO_DATO``,
          and the 5th ``TIPO_GESTIONE``.
        - As of 2021-01-30, these are transposed, and the 4th dimension name is
          ``TIPO_GEST``.
        - As of 2022-11-03, the dataflow uses yet another new DSD with the ID
          IT1:DCIS_SERVSOCEDU1(1.0).
        """

        df_id = "47_850"

        # Reported Dataflow query works
        # Without references="datastructure", this is a very slow query
        df = client.dataflow(df_id, params={"references": "datastructure"}).dataflow[
            df_id
        ]

        # dict() key for the query
        data_key = dict(
            FREQ=["A"],
            REF_AREA=["001001+001002"],
            DATA_TYPE=["AUTP"],
            TYPE_SOCIO_EDUC_SERVICE=["ALL"],
            TYPE_MANAGEMENT=["ALL"],
            HOLDER_SECTOR_PUBPRIV=["1"],
        )

        # Dimension components are in the correct order
        assert [dim.id for dim in df.structure.dimensions.components] == list(
            data_key.keys()
        ) + ["TIME_PERIOD"]

        # Reported data query works
        # NB the reported query key was "A.001001+001002.1.AUTP.ALL.ALL"; adjusted per
        #    the DSD change (above).
        client.data(df_id, key="A.001001+001002.AUTP.ALL.ALL.1")

        # Use a dict() key to force Client to make a sub-query for the DSD
        client.data(df_id, key=data_key)

    @pytest.mark.network
    def test_gh_104(self, client):
        """Test of https://github.com/khaeru/sdmx/issues/104.

        See also
        --------
        .test_reader_xml.test_gh_104
        """
        df_id = "22_289"

        dsd = (
            client.dataflow(df_id, params={"references": "datastructure"})
            .dataflow[df_id]
            .structure
        )

        # Data message is successfully parsed
        message = client.data(
            df_id,
            key=dict(AGE="TOTAL", SEX=["1", "2"], MARITAL_STATUS="99", REF_AREA="IT"),
            dsd=dsd,
            # tofile="debug.xml",
        )
        # Provided DSD is used to structure the data set(s) in the message
        assert dsd is message.data[0].structured_by


class TestLSD(DataSourceTest):
    source_id = "LSD"
    endpoint_args = {
        # Using the example from the documentation
        "data": dict(
            resource_id="S3R629_M3010217",
            params=dict(startPeriod="2005-01", endPeriod="2007-01"),
        )
    }

    @pytest.fixture
    def client(self, cache_path):
        """Identical to DataSourceTest, except skip SSL certificate verification.

        As of 2021-01-30, this source returns a certificate that is treated as invalid
        by the GitHub Actions job runner; but *not* on a local machine.
        """
        return Client(
            self.source_id, cache_name=str(cache_path), backend="sqlite", verify=False
        )


class TestNB(DataSourceTest):
    """Norges Bank.

    This source returns a valid SDMX Error message (100 No Results Found) for the
    'categoryscheme' endpoint.
    """

    source_id = "NB"


class TestNBB(DataSourceTest):
    source_id = "NBB"
    endpoint_args = {
        "data": dict(
            resource_id="REGPOP",
            key="POPULA.000.",
            params=dict(startTime=2013, endTime=2017),
        )
    }


class TestOECD(DataSourceTest):
    source_id = "OECD"
    endpoint_args = {
        "actualconstraint": dict(resource_id="CR_A_DSD_DEBT_TRANS_COLL@DF_MICRO"),
        "data": dict(
            resource_id="DSD_MSTI@DF_MSTI",
            headers={"Accept-Encoding": "compress, gzip"},
        ),
    }


class TestOECD_JSON(DataSourceTest):
    source_id = "OECD_JSON"

    endpoint_args = {
        "data": dict(
            resource_id="ITF_GOODS_TRANSPORT",
            key=".T-CONT-RL-TEU+T-CONT-RL-TON",
            # Uncomment this to test https://github.com/khaeru/sdmx/issues/64; also
            # covered by a specimen in sdmx-test-data
            # resource_id="PART2",
        )
    }

    @pytest.fixture
    def client(self, cache_path):
        # Same as the default implementation, only using oecd_json.Client
        from sdmx.source.oecd_json import Client

        return Client(self.source_id, cache_name=str(cache_path), backend="sqlite")


class TestSGR(DataSourceTest):
    source_id = "SGR"


class TestSGR3(DataSourceTest):
    """Query the `SGR` source using SDMX 3.0."""

    source_id = "SGR"
    endpoint_args = {"codelist": dict(params=dict(format="sdmx-3.0"))}


class TestSPC(DataSourceTest):
    source_id = "SPC"
    xfail = {
        "organisationscheme": HTTPError,  # 400
        "structure": NotImplementedError,  # 501
    }
    endpoint_args = {
        "actualconstraint": dict(resource_id="CR_A_DF_ADBKI"),
        "data": dict(
            resource_id="DF_CPI",
            key="A.CK+FJ..",
            params=dict(startPeriod=2010, endPeriod=2015),
        ),
    }


class TestSTAT_EE(DataSourceTest):
    source_id = "STAT_EE"
    endpoint_args = {
        # Using the example from the documentation
        "data": dict(
            resource_id="VK12",
            key="TRD_VAL+TRD_VAL_PREV..TOTAL.A",
            params=dict(startTime=2013, endTime=2017),
        )
    }


class TestUNESCO(DataSourceTest):
    """UNESCO.

    Most endpoints are marked XFAIL because the service requires registration.
    """

    source_id = "UNESCO"
    xfail = {
        # Requires registration
        "categoryscheme": HTTPError,
        "codelist": HTTPError,
        "conceptscheme": HTTPError,
        "dataflow": HTTPError,
        "provisionagreement": HTTPError,
        # Because 'supports_series_keys_only' was set
        # TODO check
        # 'datastructure': NotImplementedError,
    }


class TestUNICEF(DataSourceTest):
    source_id = "UNICEF"

    @pytest.mark.network
    def test_data(self, client):
        dsd = client.dataflow("GLOBAL_DATAFLOW").structure[0]
        client.data("GLOBAL_DATAFLOW", key="ALB+DZA.MNCH_INSTDEL.", dsd=dsd)

    @pytest.mark.network
    def test_cd2030(self, client):
        """Test that :ref:`Countdown to 2030 <CD2030>` data can be queried."""
        dsd = client.dataflow("CONSOLIDATED", provider="CD2030").structure[0]

        # D5: Births
        client.data("CONSOLIDATED", key=dict(INDICATOR="D5"), dsd=dsd)


class TestUNSD(DataSourceTest):
    source_id = "UNSD"
    xfail = {
        "organisationscheme": HTTPError,  # 400
        "structure": NotImplementedError,  # 501
    }


class TestWB(DataSourceTest):
    source_id = "WB"
    xfail = {
        "contentconstraint": NotImplementedError,  # 501
        "organisationscheme": HTTPError,  # 400
        "structure": NotImplementedError,  # 501
        "structureset": NotImplementedError,  # 501
    }

    @pytest.mark.network
    def test_gh_78(self, client):
        """Test of https://github.com/khaeru/sdmx/78.

        This response required adding support for ``<mes:Department>`` and
        ``<mes:Role>`` to :mod:`.reader.xml`.
        """
        client.data("DF_WITS_Tariff_TRAINS", key=".840.000.020110.reported")


class TestWB_WDI(DataSourceTest):
    source_id = "WB_WDI"

    endpoint_args = {
        # Example from the documentation website
        "data": dict(
            resource_id="WDI",
            key="A.SP_POP_TOTL.AFG",
            params=dict(startPeriod="2011", endPeriod="2011"),
        )
    }
