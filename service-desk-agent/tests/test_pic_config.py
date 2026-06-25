import os
import time
from unittest.mock import patch, MagicMock
import pytest
import pic_config

def test_parse_bool():
    from pic_config import _parse_bool
    assert _parse_bool("TRUE") is True
    assert _parse_bool("true") is True
    assert _parse_bool("FALSE") is False
    assert _parse_bool("") is False
    assert _parse_bool(None) is False

@patch("pic_config.build")
@patch("pic_config.service_account")
def test_load_pic_config_caching(mock_sa, mock_build):
    # Mock Sheets API response
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_sheets = mock_service.spreadsheets.return_value
    mock_values = mock_sheets.values.return_value
    
    mock_data = {
        "valueRanges": [
            # index 0: fallback tab (A=pic_name, B=pic_email, C=pic_account_id, D=role)
            {"values": [["pic_name", "pic_email", "pic_account_id", "role"],
                        ["Pic One", "pic1@test.com", "acc-pic1", ""],
                        ["Fallback PIC", "fallback@test.com", "acc-fallback", "general"],
                        ["DevOps PIC", "devops-fallback@test.com", "acc-devops", "devops"]]},
            # index 1: by_game_id tab (A=game_id, B=team_name, C=team_id, D=pic_email, E=active)
            {"values": [["game_id", "team_name", "team_id", "pic_email", "active"],
                        ["GAME_001", "Game 1", "fabbf1c2-02bb-415a-98ec-a35767bc1287", "pic1@test.com", "TRUE"]]},
            # index 2: special_rules
            {"values": [["rule_name", "enabled", "notes"],
                        ["vnd_vietnamese_detection", "TRUE", ""]]}
        ]
    }
    mock_values.batchGet.return_value.execute.return_value = mock_data

    # Ensure cache is empty
    pic_config._cached_config = None
    pic_config._cached_special_rules = None
    pic_config._last_fetch_time = 0

    os.environ["PIC_CONFIG_SHEET_ID"] = "dummy_sheet_id"

    # First load
    config = pic_config.load_pic_config()
    assert config["by_game_id"]["GAME_001"]["pic_email"] == "pic1@test.com"
    assert config["by_game_id"]["GAME_001"]["team_id"] == "fabbf1c2-02bb-415a-98ec-a35767bc1287"
    assert config["by_game_id"]["GAME_001"]["pic_account_id"] == "acc-pic1"
    assert "by_prefix" not in config
    assert "by_category" not in config
    assert config["fallback"]["general"]["email"] == "fallback@test.com"
    assert config["fallback"]["devops"]["email"] == "devops-fallback@test.com"
    
    rules = pic_config.load_special_rules()
    assert rules["vnd_vietnamese_detection"] is True
    
    # Check sheet API only called once (due to caching)
    assert mock_values.batchGet.call_count == 1
    
    # Second load within TTL (caching)
    config2 = pic_config.load_pic_config()
    assert mock_values.batchGet.call_count == 1
    
    # Force refresh
    config3 = pic_config.load_pic_config(force_refresh=True)
    assert mock_values.batchGet.call_count == 2
