import logging
from collections.abc import Mapping

import pandas as pd
import pytest

import sdmx
from sdmx import message
from sdmx.model import v21 as model
from sdmx.model.v21 import Key
from sdmx.testing import MessageTest


class StructuredMessageTest(MessageTest):
    """Variant of MessageTest for structure-specific messages."""

    directory = "ECB_EXR"
    dsd_filename: str

    # Fixtures
    @pytest.fixture(scope="class")
    def dsd(self, path):
        yield sdmx.read_sdmx(path / self.dsd_filename).structure[0]

    @pytest.fixture(scope="class")
    def msg(self, path, dsd):
        yield sdmx.read_sdmx(path / self.filename, dsd=dsd)

    # Tests for every class
    def test_msg(self, caplog, path, dsd):
        # The message can be parsed
        with caplog.at_level(logging.WARNING):
            sdmx.read_sdmx(path / self.filename, dsd=dsd)

        # No warnings are emitted per missing dsd= argument (khaeru/sdmx#146)
        assert [] == caplog.messages

    def test_structured_by(self, dsd, msg):
        # The DSD was used to parse the message
        assert msg.data[0].structured_by is dsd


class TestFlatDataSet(StructuredMessageTest):
    filename = "ng-flat-ss.xml"
    dsd_filename = "ng-structure-full.xml"

    def test_msg_type(self, msg):
        assert isinstance(msg, message.DataMessage)
        # assert msg.data[0].dim_at_obs == 'AllDimensions'

    def test_dataset_cls(self, msg):
        assert isinstance(msg.data[0], model.DataSet)

    def test_generic_obs(self, msg):
        data = msg.data[0]
        # empty series list
        assert len(list(data.series)) == 0
        obs_list = data.obs
        assert len(obs_list) == 12
        o0 = obs_list[0]

        # Flat data set → all six dimensions are at the observation level
        assert len(o0) == 6
        assert o0.key.FREQ == "M"
        assert o0.key.CURRENCY == "CHF"
        assert o0.value == "1.3413"

        # All attributes are at the observation level
        assert len(o0.attrib) == 7
        assert o0.attrib.OBS_STATUS == "A"
        assert o0.attrib.DECIMALS == "4"

    def test_write2pandas(self, msg):
        data_series = sdmx.to_pandas(msg, attributes="")
        assert isinstance(data_series, pd.Series)


class TestSeriesDataSet(StructuredMessageTest):
    filename = "ng-ts-gf-ss.xml"
    dsd_filename = "ng-structure-full.xml"

    def test_msg_type(self, dsd, msg):
        # assert msg.data[0].dim_at_obs == 'TIME_PERIOD'
        pass

    def test_dataset_cls(self, msg):
        assert isinstance(msg.data[0], model.DataSet)

    def test_obs(self, msg):
        data = msg.data[0]
        assert 12 == len(data.obs)

        series_list = list(data.series)
        assert 4 == len(series_list)

        s3 = series_list[3]
        assert isinstance(s3, model.SeriesKey)

        # Time series data set → five dimensions are at the SeriesKey level
        assert 5 == len(s3)
        assert "USD" == s3.CURRENCY

        # 5 of 7 attributes are at the Observation level
        assert 5 == len(s3.attrib)
        assert "4" == s3.attrib.DECIMALS

        obs_list = data.series[s3]
        assert 3 == len(obs_list)
        o2 = obs_list[2]

        # One remaining dimension is at the Observation Level
        assert 1 == len(o2.dimension)
        assert Key(TIME_PERIOD="2010-10") == o2.dim
        assert "1.3898" == o2.value

        # Two remaining attributes are at the Observation level
        assert 2 == len(o2.attached_attribute)
        assert "A" == o2.attrib.OBS_STATUS

    def test_pandas(self, msg):
        data = msg.data[0]

        # Expected number of observations and series
        assert len(data.obs) == 12
        assert len(data.series) == 4

        # Single series can be converted to pandas
        s3 = sdmx.to_pandas(data.series[3], attributes="")
        assert isinstance(s3, pd.Series)
        # With expected values
        assert s3.iloc[0] == 1.2894

        # Single series can be converted with attributes
        s3_attr = sdmx.to_pandas(data.series[3], attributes="osgd")

        # yields a DataFrame
        assert isinstance(s3_attr, pd.DataFrame)
        assert s3_attr.shape == (3, 8)

        assert s3_attr.iloc[0].value == 1.2894

        # Attributes of observations can be accessed
        assert s3_attr.iloc[0].OBS_STATUS == "A"

    def test_write2pandas(self, msg):
        df = sdmx.to_pandas(msg, attributes="")
        assert isinstance(df, pd.Series)
        assert df.shape == (12,)
        # with metadata
        df = sdmx.to_pandas(msg, attributes="osgd")
        assert df.shape == (12, 8)
        assert df.iloc[1].OBS_STATUS == "A"


class TestSeriesDataSet2(StructuredMessageTest):
    filename = "ng-ts-ss.xml"
    dsd_filename = "ng-structure-full.xml"

    def test_msg_type(self, dsd, msg):
        # assert msg.data[0].dim_at_obs == 'TIME_PERIOD'
        pass

    def test_dataset_cls(self, msg):
        assert isinstance(msg.data[0], model.DataSet)

    def test_structured_obs(self, msg):
        data = msg.data[0]

        # Expected number of observations and series
        assert 12 == len(data.obs)
        assert 4 == len(data.series)

        # SeriesKey is accessible by index using DictLike
        s3 = list(data.series.keys())[3]
        assert isinstance(s3, model.SeriesKey)

        # SeriesKey has expected number of dimensions and values
        assert 5 == len(s3)
        assert "USD" == s3.CURRENCY

        # SeriesKey has expected number of attributes and values
        assert 5 == len(s3.attrib)
        assert "4" == s3.attrib.DECIMALS

        # Series observations can be accessed
        obs_list = data.series[s3]
        assert 3 == len(obs_list)
        o2 = obs_list[2]
        assert 1 == len(o2.dimension)
        assert Key(TIME_PERIOD="2010-10") == o2.dim
        assert "1.3898" == o2.value
        assert "A" == o2.attrib.OBS_STATUS

    def test_dataframe(self, msg):
        data = msg.data[0]
        s = sdmx.to_pandas(data, attributes="")
        assert isinstance(s, pd.Series)
        assert len(s) == 12


class TestSeriesData_SiblingGroup_TS(StructuredMessageTest):
    filename = "sg-ts-ss.xml"
    dsd_filename = "sg-structure.xml"

    def test_groups(self, msg):
        data = msg.data[0]
        assert len(data.group) == 4
        assert len(data.series) == 4
        g2 = list(data.group.keys())[2]
        assert g2.CURRENCY == "JPY"
        assert g2.attrib.TITLE == "ECB reference exchange rate, Japanese yen/Euro"

        # Check direct attributes of SeriesKey
        s = list(data.series)[0]
        assert 4 == len(s.attrib)

        # Check group attributes of a series
        g_attrib = s.group_attrib
        assert isinstance(g_attrib, Mapping)
        assert 1 == len(g_attrib)


class TestSeriesData_RateGroup_TS(StructuredMessageTest):
    filename = "rg-ts-ss.xml"
    dsd_filename = "rg-structure.xml"

    def test_dsd(self, dsd):
        ad = dsd.attributes
        for id in ("CONF_STATUS_OBS", "OBS_STATUS"):
            assert isinstance(ad.get(id).related_to, model.PrimaryMeasureRelationship)
        for id in ("COLL_METHOD", "TITLE"):
            assert isinstance(ad.get(id).related_to, model.GroupRelationship)
        for id in ("DECIMALS", "UNIT_MEASURE", "UNIT_MULT"):
            assert isinstance(ad.get(id).related_to, model.DimensionRelationship)

    def test_groups(self, msg):
        data = msg.data[0]
        assert len(data.group) == 5
        assert len(data.series) == 4
        g2 = list(data.group.keys())[2]
        assert g2.CURRENCY == "GBP"
        assert (
            g2.attrib.TITLE == "ECB reference exchange rate, U.K. Pound sterling /Euro"
        )

        # Check group attributes of a series
        s = list(data.series)[0]
        g_attrib = s.group_attrib
        assert isinstance(g_attrib, Mapping)
        assert 5 == len(g_attrib)
