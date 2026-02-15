from engine import PageTextExtractor
from logger import Logger
import traceback
import sys


def main():
    logger = Logger()
    logger.log("INFO", "Application started")

    try:
        extractor = PageTextExtractor()
        extractor.run()

    except KeyboardInterrupt:
        logger.log("WARNING", "KeyboardInterrupt received in main")

    except Exception as e:
        error_trace = traceback.format_exc()

        logger.log("ERROR", f"Unhandled exception: {str(e)}")
        logger.log("ERROR", f"Traceback:\n{error_trace}")

        print("Fatal error occurred. Check logs.txt")

    finally:
        logger.log("INFO", "Application terminated")


if __name__ == "__main__":
    main()
