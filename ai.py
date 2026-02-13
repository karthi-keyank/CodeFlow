import tkinter as tk
from tkinter import messagebox
from google import genai
import time


class Ai:

    def __init__(self):
        print("[AI] Initializing...")

        # Load multiple API keys
        self.api_keys = self.get_api_keys_from_gui()

        if not self.api_keys:
            raise ValueError("No API keys provided.")

        self.current_key_index = 0
        self.model = "models/gemini-2.5-flash"

        self.custom_prompt = (
            "You are editing an existing C/C++ source file. "
            "Only provide the required missing code fragment. "
            "Do not rewrite or reorder the program. "
            "Do not modify existing variables or structure. "
            "If new variables are required, declare them and add dont add any comments"
            "Each statement must be on a separate line. "
            "Do NOT insert line breaks inside (), [] "
            "Keep for(), while(), if() conditions in a single line. "
            "Use braces {} and semicolons normally. "
            "Do NOT use comments in code. "
            "Try to mizimize the token usages"
            "Do not collapse code into a single line. "
            "Do not indent any lines; every line must begin at column 0. "
            "Output only code."
        )

        print("[AI] Ready")

    # ==========================================
    # MULTIPLE API KEY GUI
    # ==========================================
    def get_api_keys_from_gui(self):
        key_entries = []
        keys_collected = []

        def add_key_field():
            entry = tk.Entry(frame, width=50, show="*")
            entry.pack(pady=3)
            key_entries.append(entry)

        def submit():
            for entry in key_entries:
                key = entry.get().strip()
                if key:
                    keys_collected.append(key)

            if not keys_collected:
                messagebox.showerror("Error", "At least one API key required.")
                return

            root.destroy()

        root = tk.Tk()
        root.title("Enter Gemini API Keys")
        root.geometry("450x400")
        root.resizable(False, False)

        tk.Label(root, text="Add one or more Gemini API Keys:").pack(pady=10)

        frame = tk.Frame(root)
        frame.pack()

        add_key_field()

        tk.Button(root, text="Add Key", command=add_key_field).pack(pady=5)
        tk.Button(root, text="Submit", command=submit).pack(pady=10)

        root.mainloop()

        return keys_collected

    # ==========================================
    # GET CURRENT CLIENT
    # ==========================================
    def get_current_client(self):
        api_key = self.api_keys[self.current_key_index]
        return genai.Client(api_key=api_key)

    # ==========================================
    # INFINITE ROTATING FAILOVER
    # ==========================================
    def write_code(self, input_text):
        print("[AI] Sending request to Gemini...")

        total_keys = len(self.api_keys)

        while True:  # infinite retry loop
            try:
                client = self.get_current_client()

                response = client.models.generate_content(
                    model=self.model,
                    contents=self.custom_prompt + "\n\n" + input_text
                )

                print("[AI] Success using key index:",
                      self.current_key_index)

                return response.text

            except Exception as e:
                print(f"[AI] Key {self.current_key_index} failed:", e)

                # Move to next key (circular rotation)
                self.current_key_index = (self.current_key_index + 1) % total_keys

                print("[AI] Switching to key index:",
                      self.current_key_index)

                # Prevent CPU overload
                time.sleep(1)
