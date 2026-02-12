from playwright.sync_api import sync_playwright
from playwright._impl._errors import Error
from ai import Ai
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


def format(text):
    return text.replace("}", "")


# ======================================================
# PAGE TEXT EXTRACTOR
# ======================================================
class PageTextExtractor:

    START_KEY = "ctrl+shift+f8"
    STOP_KEY = "ctrl"
    CONTINUE_KEY = "shift"

    def __init__(self):
        self.state = "IDLE"          # IDLE | WRITING | PAUSED
        self.extracting = False
        self.running = True
        self.want_extract = False

        self.ai = Ai()

        # Streaming buffer
        self.ai_output = ""
        self.write_index = 0

    # ----------------------------
    # Hotkeys
    # ----------------------------
    def start_hotkey_listener(self):
        keyboard.add_hotkey(self.START_KEY, self._start_writing)
        keyboard.add_hotkey(self.STOP_KEY, self._stop_writing)
        keyboard.add_hotkey(self.CONTINUE_KEY, self._continue_writing)

    def _start_writing(self):
        if self.state == "IDLE":
            self.state = "WRITING"
            self.want_extract = True
            self.ai_output = ""
            self.write_index = 0

    def _stop_writing(self):
        if self.state == "WRITING":
            self.state = "PAUSED"

    def _continue_writing(self):
        if self.state == "PAUSED":
            self.state = "WRITING"

    # ----------------------------
    # Extraction
    # ----------------------------
    def _extract_text_when_ready(self, page):
        if self.extracting or page.is_closed():
            return

        self.extracting = True

        try:
            page.wait_for_load_state("networkidle", timeout=10000)
            raw_text = page.inner_text("body")
            filtered_text = filter_page_text(raw_text)

            output = self.ai.write_code(filtered_text)

            self.ai_output = format(output)
            self.write_index = 0
            self.want_extract = False

        except Error:
            self.want_extract = True  # retry next loop

        finally:
            self.extracting = False

    # ----------------------------
    # Main Loop
    # ----------------------------
    def run(self, start_url: str):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    channel="msedge",
                    headless=False
                )

                page = browser.new_page()
                page.goto(start_url)

                self.start_hotkey_listener()

                print("CTRL+ALT+E → Start")
                print("CTRL+ALT+S → Stop")
                print("CTRL+ALT+D → Continue")
                print("Close browser to exit.")

                while self.running and not page.is_closed():

                    if self.state == "WRITING":

                        # If no output yet, extract
                        if self.want_extract and not self.extracting:
                            self._extract_text_when_ready(page)

                        # If we have AI output, type progressively
                        elif self.ai_output:

                            if self.write_index < len(self.ai_output):
                                keyboard.write(self.ai_output[self.write_index])
                                self.write_index += 1
                                time.sleep(0.01)
                            else:
                                # Finished writing
                                self.state = "IDLE"
                                self.ai_output = ""
                                self.write_index = 0

                    time.sleep(0.01)

        except KeyboardInterrupt:
            self.running = False

        finally:
            self.running = False
            keyboard.unhook_all_hotkeys()
            print("Exited cleanly.")
