import tkinter as tk
from tkinter import messagebox
from google import genai
import time
import json
import os
from logger import Logger


class Ai:

    def __init__(self):
        print("[AI] Initializing...")

        # Initialize logger
        self.logger = Logger()

        self.api_keys = self.load_or_get_keys()

        if not self.api_keys:
            raise ValueError("No API keys provided.")

        self.current_key_index = 0
        self.model = "models/gemini-2.5-flash"

        self.custom_prompt = (
            "You are editing an existing C/C++ source file. "
            "Only provide the required missing code fragment. "
            "Do not rewrite or reorder the program. "
            "Do not modify existing variables or structure. "
            "If new variables are required, declare them and do not add comments. "
            "If no code is provided, generate a complete standalone C program including all required #include directives and a main() function. "
            "Each statement must be on a separate line. "
            "Do NOT insert line breaks inside (), []. "
            "Keep for(), while(), if() conditions in a single line. "
            "Use braces {} and semicolons normally. "
            "Do NOT use comments in code. "
            "Minimize token usage. "
            "Do not collapse code into a single line. "
            "Do not indent any lines; every line must begin at column 0. "
            "Output only code."
        )

        self.logger.log("INFO", "AI Initialized")
        print("[AI] Ready")

    # ==========================================
    # JSON HANDLING
    # ==========================================

    def load_keys_from_json(self):
        if not os.path.exists("api_keys.json"):
            return []

        try:
            with open("api_keys.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("keys", [])
        except Exception as e:
            self.logger.log("ERROR", f"Failed to load api_keys.json: {str(e)}")
            return []

    def save_keys_to_json(self, keys):
        try:
            with open("api_keys.json", "w", encoding="utf-8") as f:
                json.dump({"keys": keys}, f, indent=4)
            self.logger.log("SUCCESS", "API keys saved to api_keys.json")
        except Exception as e:
            self.logger.log("ERROR", f"Failed to save API keys: {str(e)}")

    # ==========================================
    # GUI
    # ==========================================

    def load_or_get_keys(self):
        existing_keys = self.load_keys_from_json()
        keys_collected = existing_keys.copy()

        root = tk.Tk()
        root.title("Gemini API Manager")
        root.geometry("500x380")
        root.resizable(False, False)

        top_frame = tk.Frame(root)
        top_frame.pack(pady=12, padx=15, fill="x")

        tk.Label(top_frame, text="Enter API Key:").pack(anchor="w")

        key_entry = tk.Entry(top_frame, show="*", width=60)
        key_entry.pack(fill="x", pady=6)

        button_frame = tk.Frame(root)
        button_frame.pack(pady=5)

        def add_key():
            key = key_entry.get().strip()
            if not key:
                messagebox.showerror("Error", "Key cannot be empty.")
                return

            keys_collected.append(key)
            key_entry.delete(0, tk.END)
            refresh_list()
            self.logger.log("INFO", "New API key added")

        def delete_key(index):
            try:
                keys_collected.pop(index)
                refresh_list()
                self.logger.log("WARNING", f"API key at index {index} deleted")
            except Exception as e:
                self.logger.log("ERROR", f"Delete failed: {str(e)}")

        def submit():
            if not keys_collected:
                messagebox.showerror("Error", "At least one API key required.")
                return
            self.save_keys_to_json(keys_collected)
            root.destroy()

        def skip():
            if not keys_collected:
                messagebox.showerror("Error", "No keys available.")
                return
            root.destroy()

        tk.Button(button_frame, text="Add Key", width=14, command=add_key).pack(side="left", padx=6)
        tk.Button(button_frame, text="Submit", width=14, command=submit).pack(side="left", padx=6)
        tk.Button(button_frame, text="Skip", width=14, command=skip).pack(side="left", padx=6)

        list_container = tk.Frame(root)
        list_container.pack(padx=15, pady=12, fill="both", expand=True)

        canvas = tk.Canvas(list_container, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def refresh_list():
            for widget in scroll_frame.winfo_children():
                widget.destroy()

            for i, key in enumerate(keys_collected):
                row = tk.Frame(scroll_frame)
                row.pack(fill="x", pady=4)

                masked = key[:4] + "****" + key[-4:]

                tk.Label(row, text=masked, anchor="w", width=45).pack(side="left")

                tk.Button(
                    row,
                    text="Delete",
                    width=8,
                    command=lambda idx=i: delete_key(idx)
                ).pack(side="right")

        refresh_list()

        root.mainloop()
        return keys_collected

    # ==========================================
    # CLIENT ROTATION
    # ==========================================

    def get_current_client(self):
        api_key = self.api_keys[self.current_key_index]
        return genai.Client(api_key=api_key)

    def write_code(self, input_text):

        self.logger.log("INFO", "Sending request to Gemini")

        total_keys = len(self.api_keys)

        while True:
            try:
                client = self.get_current_client()

                response = client.models.generate_content(
                    model=self.model,
                    contents=self.custom_prompt + "\n\n" + input_text
                )

                self.logger.log(
                    "SUCCESS",
                    f"Success using key index {self.current_key_index}"
                )

                return response.text

            except Exception as e:

                self.logger.log(
                    "ERROR",
                    f"Key {self.current_key_index} failed: {str(e)}"
                )

                self.current_key_index = (self.current_key_index + 1) % total_keys

                self.logger.log(
                    "WARNING",
                    f"Switching to key index {self.current_key_index}"
                )

                time.sleep(1)

