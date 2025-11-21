import re

def test_url_extraction():
    # Test cases
    test_cases = [
        (
            "Check this out: https://boards.4chan.org/g/thread/123456 and this http://boards.4chan.org/v/thread/789012",
            ["https://boards.4chan.org/g/thread/123456", "http://boards.4chan.org/v/thread/789012"]
        ),
        (
            "Just some random text with no urls",
            []
        ),
        (
            "Mixed urls: https://google.com and https://boards.4chan.org/a/thread/111222",
            ["https://boards.4chan.org/a/thread/111222"]
        ),
        (
            "Multiline text:\nhttps://boards.4chan.org/b/thread/333444\nSome other stuff",
            ["https://boards.4chan.org/b/thread/333444"]
        )
    ]

    print("Running URL extraction tests...")
    for text, expected in test_cases:
        urls = re.findall(r"https?://[^\s]+", text)
        valid_urls = [
            url for url in urls if "boards.4chan.org" in url or "4chan.org" in url
        ]
        
        if valid_urls == expected:
            print(f"✅ PASS: '{text[:30]}...' -> {valid_urls}")
        else:
            print(f"❌ FAIL: '{text[:30]}...' -> Expected {expected}, got {valid_urls}")

if __name__ == "__main__":
    test_url_extraction()
