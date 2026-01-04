import multiprocessing


class Config:
    MAX_WORKERS = min(5, multiprocessing.cpu_count())
    DOWNLOAD_TIMEOUT = (10, 60)
    RATE_LIMIT_DELAY = 0.3
    MAX_RETRIES = 3
    CHUNK_SIZE = 8192
    MAX_FILENAME_LENGTH = 200
    MIN_FREE_SPACE_MB = 100
    PROGRESS_UPDATE_INTERVAL = 0.1
    MAX_FOLDER_NAME_LENGTH = 40

    # Network timeouts and delays
    API_TIMEOUT = 30  # API request timeout in seconds
    RETRY_DELAY = 2.0  # Delay before retry in seconds
    CATALOG_SCRAPE_DELAY = 0.5  # Delay between catalog thread scrapes

    # Smart rate limiting
    BASE_DELAY = 0.3
    BACKOFF_MULTIPLIER = 1.5
    MAX_DELAY = 5.0

    MEDIA_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        ".webm",
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".pdf",
        ".txt",
        ".zip",
        ".rar",
    }

    PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

    VIDEO_EXTENSIONS = {".webm", ".mp4", ".mov", ".avi", ".mkv"}

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
