from playwright.sync_api import sync_playwright, Error
from ai import Ai
import keyboard
import time
import re
import threading


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
# PAGE TEXT EXTRACTOR (MULTI TAB SAFE)
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

        self.ai = Ai()

        self.ai_output = ""
        self.write_index = 0

        self.context = None

    # ----------------------------
    # HOTKEYS
    # ----------------------------
    def start_hotkey_listener(self):
        keyboard.add_hotkey(self.START_KEY, self._start_writing)
        keyboard.add_hotkey(self.STOP_KEY, self._stop_writing)
        keyboard.add_hotkey(self.CONTINUE_KEY, self._continue_writing)

    def _start_writing(self):
        if self.state == "IDLE":
            print("Start triggered.")
            self.state = "WRITING"
            self.want_extract = True
            self.ai_output = ""
            self.write_index = 0

    def _stop_writing(self):
        if self.state == "WRITING":
            print("Paused.")
            self.state = "PAUSED"

    def _continue_writing(self):
        if self.state == "PAUSED":
            print("Resumed.")
            self.state = "WRITING"

    # ----------------------------
    # GET ACTIVE TAB (LAST OPENED)
    # ----------------------------
    def get_active_page(self):
        try:
            pages = self.context.pages
            if not pages:
                return None

            # last tab (index -1)
            return pages[-1]

        except Exception:
            return None

    # ----------------------------
    # EXTRACTION
    # ----------------------------
    def extract_text(self, page):
        if self.extracting:
            return

        self.extracting = True

        try:
            if page.is_closed():
                return

            page.wait_for_load_state("networkidle", timeout=10000)

            raw_text = page.inner_text("body")
            filtered_text = filter_page_text(raw_text)

            output = self.ai.write_code(filtered_text)

            self.ai_output = output
            self.write_index = 0
            self.want_extract = False

        except Error as e:
            print("Extraction error:", e)
            self.want_extract = True

        except Exception as e:
            print("Unexpected extraction error:", e)
            self.want_extract = False

        finally:
            self.extracting = False

    # ----------------------------
    # MAIN LOOP
    # ----------------------------
    def run(self, start_url: str | None = None):

        try:
            with sync_playwright() as p:

                self.context = p.chromium.launch_persistent_context(
                    user_data_dir="user_data",
                    channel="msedge",
                    headless=False
                )

                if start_url:
                    page = self.context.new_page()
                    page.goto(start_url)

                self.start_hotkey_listener()

                print("CTRL+SHIFT+F8 → Start")
                print("CTRL → Pause")
                print("SHIFT → Resume")
                print("Close browser to exit.")

                while self.running:

                    pages = self.context.pages

                    if not pages:
                        print("All tabs closed. Exiting.")
                        break

                    active_page = self.get_active_page()

                    if not active_page or active_page.is_closed():
                        time.sleep(0.2)
                        continue

                    if self.state == "WRITING":

                        if self.want_extract and not self.extracting:
                            self.extract_text(active_page)

                        elif self.ai_output:

                            if self.write_index < len(self.ai_output):
                                keyboard.write(self.ai_output[self.write_index])
                                self.write_index += 1
                            else:
                                print("Finished writing.")
                                self.state = "IDLE"
                                self.ai_output = ""
                                self.write_index = 0

                    time.sleep(0.01)

        except KeyboardInterrupt:
            print("Keyboard interrupt detected.")

        except Exception as e:
            print("Fatal error:", e)

        finally:
            self.running = False
            keyboard.unhook_all_hotkeys()

            try:
                if self.context:
                    self.context.close()
            except:
                pass

            print("Exited cleanly.")
