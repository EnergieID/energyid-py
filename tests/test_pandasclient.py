"""Tests for PandasClient data parsing methods."""

from unittest.mock import MagicMock, patch
import pandas as pd

from energyid.pandasclient import PandasClient


class TestPandasClientParsing:
    def setup_method(self):
        self.client = PandasClient(api_key="test-key")

    def test_parse_meter_data_empty(self):
        data = {"data": []}
        result = self.client._parse_meter_data(data, "meter1")
        assert isinstance(result, pd.Series)
        assert result.empty

    def test_parse_meter_data_with_data(self):
        data = {
            "data": [
                {"timestamp": "2024-01-01T00:00:00Z", "value": 100},
                {"timestamp": "2024-01-02T00:00:00Z", "value": 200},
            ]
        }
        result = self.client._parse_meter_data(data, "meter1")
        assert isinstance(result, pd.Series)
        assert len(result) == 2
        assert result.name == "meter1"

    def test_parse_single_series_empty(self):
        result = self.client._parse_single_series([], name="test")
        assert isinstance(result, pd.Series)
        assert result.empty

    def test_parse_single_series_with_data(self):
        data = [
            {"timestamp": "2024-01-01T00:00:00Z", "value": 100},
            {"timestamp": "2024-01-02T00:00:00Z", "value": 200},
        ]
        result = self.client._parse_single_series(data, name="elec")
        assert isinstance(result, pd.Series)
        assert len(result) == 2
        assert result.name == "elec"

    def test_parse_multiple_series(self):
        data = [
            {
                "name": "sub1",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00Z", "value": 10},
                    {"timestamp": "2024-01-02T00:00:00Z", "value": 20},
                ],
            },
            {
                "name": "sub2",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00Z", "value": 30},
                    {"timestamp": "2024-01-02T00:00:00Z", "value": 40},
                ],
            },
        ]
        result = self.client._parse_multiple_series(data, name="elec")
        assert isinstance(result, pd.DataFrame)
        assert result.shape == (2, 2)

    def test_parse_multiple_series_empty(self):
        data = [{"name": "sub1", "data": []}]
        result = self.client._parse_multiple_series(data, name="elec")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_parse_record_data_single(self):
        d = {
            "value": [
                {
                    "data": [
                        {"timestamp": "2024-01-01T00:00:00Z", "value": 100},
                    ]
                }
            ]
        }
        result = self.client._parse_record_data(d, name="elec")
        assert isinstance(result, pd.Series)

    def test_parse_record_data_multiple_series(self):
        d = {
            "value": [
                {
                    "series": [
                        {
                            "name": "import",
                            "data": [
                                {"timestamp": "2024-01-01T00:00:00Z", "value": 100},
                            ],
                        },
                        {
                            "name": "export",
                            "data": [
                                {"timestamp": "2024-01-01T00:00:00Z", "value": 50},
                            ],
                        },
                    ]
                }
            ]
        }
        result = self.client._parse_record_data(d, name="elec")
        assert isinstance(result, pd.DataFrame)

    def test_parse_multiple_values(self):
        d = {
            "value": [
                {
                    "name": "electricity",
                    "series": [
                        {
                            "name": "import",
                            "data": [
                                {"timestamp": "2024-01-01T00:00:00Z", "value": 100}
                            ],
                        }
                    ],
                },
                {
                    "name": "gas",
                    "series": [
                        {
                            "name": "import",
                            "data": [
                                {"timestamp": "2024-01-01T00:00:00Z", "value": 50}
                            ],
                        }
                    ],
                },
            ]
        }
        result = self.client._parse_record_data(d, name="energy")
        assert isinstance(result, pd.DataFrame)


class TestPandasClientMeterReadings:
    def setup_method(self):
        self.client = PandasClient(api_key="test-key")

    def test_get_meter_readings_returns_dataframe(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "readings": [
                {"timestamp": "2024-01-01T00:00:00Z", "value": 100, "key": "k1"},
                {"timestamp": "2024-01-02T00:00:00Z", "value": 200, "key": "k2"},
            ],
            "nextRowKey": None,
        }
        mock_resp.raise_for_status.return_value = None

        with patch.object(self.client.session, "get", return_value=mock_resp):
            df = self.client.get_meter_readings("meter1")
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 2
            assert df.index.name == "timestamp"

    def test_get_meter_readings_empty(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"readings": [], "nextRowKey": None}
        mock_resp.raise_for_status.return_value = None

        with patch.object(self.client.session, "get", return_value=mock_resp):
            df = self.client.get_meter_readings("meter1")
            assert isinstance(df, pd.DataFrame)
            assert df.empty


class TestPandasClientInheritance:
    def test_inherits_from_jsonclient(self):
        from energyid import JSONClient

        assert issubclass(PandasClient, JSONClient)

    def test_api_key_auth_works(self):
        client = PandasClient(api_key="test-key")
        assert client._auth_mode == "api_key"
        assert client.session.headers["Authorization"] == "apiKey test-key"
