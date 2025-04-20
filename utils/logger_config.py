import platform
import logging
import logging.config

try:
    import colorlog
    COLORLOG_AVAILABLE = True
except ImportError:
    COLORLOG_AVAILABLE = False

LOGGING_NAME = "InsightFace"

def set_logging(name=LOGGING_NAME, verbose=True, debug=False):
    level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
    # - %(name)s
    formatter_str = "%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    # Formatters
    formatters = {
        name: {
            "format": formatter_str,
            "datefmt": datefmt
        }
    }

    if COLORLOG_AVAILABLE:
        formatters["color"] = {
            "()": "colorlog.ColoredFormatter",
            "format": "%(log_color)s" + formatter_str,
            "datefmt": datefmt,
            "log_colors": {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            }
        }

    # Only console handler
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "level": level,
            "formatter": "color" if COLORLOG_AVAILABLE else name
        }
    }

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "loggers": {
            name: {
                "handlers": ["console"],
                "level": level,
                "propagate": False
            }
        }
    })

    # Emoji safe logging cho Windows (nếu cần)
    logger = logging.getLogger(name)
    if platform.system() == 'Windows':
        for fn in logger.info, logger.warning:
            setattr(logger, fn.__name__, lambda x: fn(str(x)))

# Gọi khởi tạo logger
set_logging(debug=True)
LOGGER = logging.getLogger(LOGGING_NAME)
