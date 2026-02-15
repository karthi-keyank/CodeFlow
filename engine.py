from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from ai import Ai
from logger import Logger

import keyboard
import time
import re


# ======================================================
# FILTER LOGIC – REMOVE ONLY CONFIRMED JUNK
# ======================================================

def filter_page_text(raw_text: str) -> str:
    lines = raw_text.splitlines()
    output = []

    user_header_pattern = re.compile(r'^[A-Z ]+\s[A-Z]-\d{12}@vec$')
    footer_user_pattern = re.compile(r'^\d{12}@vec$')
    progress_line_pattern = re.compile(r'^[\d\s/]+$')
    valid_date_pattern = re.compile(r'^\d{2}-[A-Za-z]{3}-\d{4}$')

    junk_words = {
        "ui-button", "save", "run",
        "home", "reports", "profile", "help", "logout",
    }

    theme_words = {
        "ambiance", "chaos", "clouds midnight", "cobalt",
        "idle fingers", "krtheme", "merbivore", "merbivore soft",
        "mono industrial", "monokai", "pastel on dark",
        "solarized dark", "terminal", "tomorrow night",
        "tomorrow night blue", "tomorrow night bright",
        "tomorrow night 80s", "twilight", "vibrant ink",
        "chrome", "clouds", "crimson editor", "dawn",
        "dreamweaver", "eclipse", "github", "iplastic",
        "solarized light", "textmate", "tomorrow", "xcode",
        "kuroir", "katzenmilch", "sql server",
    }

    skip_next_line = False

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if lower == "valid till:":
            skip_next_line = True
            continue

        if skip_next_line:
            if valid_date_pattern.match(stripped):
                skip_next_line = False
                continue
            skip_next_line = False

        if not stripped:
            continue
        if user_header_pattern.match(stripped):
            continue
        if footer_user_pattern.match(stripped):
            continue
        if progress_line_pattern.match(stripped) and len(stripped) > 5:
            continue
        if lower in junk_words:
            continue
        if lower in theme_words:
            continue

        output.append(stripped)

    return "\n".join(output)


# ======================================================
# PAGE TEXT EXTRACTOR
# ======================================================

class PageTextExtractor:

    START_KEY = "ctrl+shift+f8"
    STOP_KEY = "ctrl"
    CONTINUE_KEY = "shift"

    def __init__(self):
        self.state = "IDLE"
        self.extracting = False
        self.running = True
        self.want_extract = False

        self.logger = Logger()
        self.logger.log("INFO", "PageTextExtractor initialized")

        self.ai = Ai()

        self.ai_output = ""
        self.write_index = 0

        self.driver = None

    # ----------------------------
    # HOTKEYS
    # ----------------------------

    def start_hotkey_listener(self):
        keyboard.add_hotkey(self.START_KEY, self._start_writing)
        keyboard.add_hotkey(self.STOP_KEY, self._stop_writing)
        keyboard.add_hotkey(self.CONTINUE_KEY, self._continue_writing)
        self.logger.log("INFO", "Hotkeys registered")

    def _start_writing(self):
        if self.state == "IDLE":
            self.logger.log("INFO", "Start triggered")
            self.state = "WRITING"
            self.want_extract = True
            self.ai_output = ""
            self.write_index = 0

    def _stop_writing(self):
        if self.state == "WRITING":
            self.logger.log("WARNING", "Paused writing")
            self.state = "PAUSED"

    def _continue_writing(self):
        if self.state == "PAUSED":
            self.logger.log("INFO", "Resumed writing")
            self.state = "WRITING"

    # ----------------------------
    # GET ACTIVE TAB
    # ----------------------------

    def get_active_page(self):
        try:
            handles = self.driver.window_handles
            if not handles:
                return None

            last_handle = handles[-1]
            self.driver.switch_to.window(last_handle)
            return self.driver

        except Exception as e:
            self.logger.log("ERROR", f"Failed to get active tab: {str(e)}")
            return None

    # ----------------------------
    # EXTRACTION
    # ----------------------------

    def extract_text(self, driver):
        if self.extracting:
            return

        self.extracting = True
        self.logger.log("INFO", "Starting text extraction")

        try:
            time.sleep(1)

            body = driver.find_element(By.TAG_NAME, "body")
            raw_text = body.text

            filtered_text = filter_page_text(raw_text)
            self.logger.log("INFO", "Page text filtered successfully")

            output = self.ai.write_code(filtered_text)

            self.ai_output = output
            self.write_index = 0
            self.want_extract = False

            self.logger.log("SUCCESS", "AI response received")

        except WebDriverException as e:
            self.logger.log("ERROR", f"WebDriver extraction error: {str(e)}")
            self.want_extract = True

        except Exception as e:
            self.logger.log("ERROR", f"Unexpected extraction error: {str(e)}")
            self.want_extract = False

        finally:
            self.extracting = False

    # ----------------------------
    # MAIN LOOP
    # ----------------------------

    def run(self, start_url: str | None = None):

        try:
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

            self.logger.log("SUCCESS", "Chrome driver started")

            if start_url:
                self.driver.get(start_url)
                self.logger.log("INFO", f"Opened URL: {start_url}")

            self.start_hotkey_listener()

            while self.running:

                handles = self.driver.window_handles
                if not handles:
                    self.logger.log("WARNING", "All tabs closed")
                    break

                active_page = self.get_active_page()

                if not active_page:
                    time.sleep(0.1)
                    continue

                if self.state == "WRITING":

                    if self.want_extract and not self.extracting:
                        self.extract_text(active_page)

                    elif self.ai_output:

                        if self.write_index < len(self.ai_output):
                            keyboard.write(self.ai_output[self.write_index])
                            self.write_index += 1
                        else:
                            self.logger.log("SUCCESS", "Finished writing output")
                            self.state = "IDLE"
                            self.ai_output = ""
                            self.write_index = 0

                time.sleep(0.0001)

        except KeyboardInterrupt:
            self.logger.log("WARNING", "Keyboard interrupt detected")

        except Exception as e:
            self.logger.log("ERROR", f"Fatal error: {str(e)}")

        finally:
            self.running = False

            try:
                keyboard.unhook_all()
                self.logger.log("INFO", "Hotkeys unhooked")
            except:
                pass

            try:
                if self.driver:
                    self.driver.quit()
                    self.logger.log("INFO", "Driver closed")
            except:
                pass

            self.logger.log("INFO", "Exited cleanly")
