from four_charm.core.scraper import FourChanScraper
from four_charm.config import Config


def test_parse_url_thread_and_catalog():
    scraper = FourChanScraper()

    thread = scraper.parse_url("https://boards.4chan.org/g/thread/123456789")
    catalog = scraper.parse_url("https://boards.4chan.org/g/catalog")
    invalid = scraper.parse_url("https://example.com/not-4chan")

    assert thread == {"board": "g", "type": "thread", "thread_id": "123456789"}
    assert catalog == {"board": "g", "type": "catalog", "thread_id": None}
    assert invalid is None


def test_build_session_base_name_limits_length_and_sanitizes():
    scraper = FourChanScraper()
    long_board = "a" * (Config.MAX_FOLDER_NAME_LENGTH + 10)
    base = scraper.build_session_base_name({"board": long_board, "type": "board", "thread_id": None})

    assert len(base) <= Config.MAX_FOLDER_NAME_LENGTH
    assert "/" not in base and "\\" not in base
    assert base  # non-empty
