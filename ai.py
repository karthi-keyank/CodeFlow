import tkinter as tk
from tkinter import messagebox
from google import genai


class Ai:

    def __init__(self):
        print("[AI] Initializing...")

        # Always get API key from GUI
        self.api_key = self.get_api_key_from_gui()

        print("[AI] API Key loaded")

        # Create client
        self.client = genai.Client(api_key=self.api_key)
        self.model = "models/gemini-2.5-flash"

        self.custom_prompt = (
            "You are editing an existing C/C++ source file. "
            "Only provide the required missing code fragment. "
            "Do not rewrite or reorder the program. "
            "Do not modify existing variables or structure. "
            "If new variables are required, declare them and add a short inline comment. "
            "Each statement must be on a separate line. "
            "Do NOT insert line breaks inside (), [] "
            "Keep for(), while(), if() conditions in a single line. "
            "Use braces {} and semicolons normally. "
            "Do not collapse code into a single line. "
            "Do not indent any lines; every line must begin at column 0. "
            "Output only code."
        )

        print("[AI] Ready")

    # -----------------------------------
    # GUI API KEY INPUT
    # -----------------------------------
    def get_api_key_from_gui(self):
        key_holder = {"value": None}

        def submit():
            entered_key = entry.get().strip()
            if not entered_key:
                messagebox.showerror("Error", "API key cannot be empty.")
                return

            key_holder["value"] = entered_key
            root.destroy()

        root = tk.Tk()
        root.title("Enter Gemini API Key")
        root.geometry("400x150")
        root.resizable(False, False)

        tk.Label(root, text="Paste your Gemini API Key:").pack(pady=10)

        entry = tk.Entry(root, width=50, show="*")  # hides key like password
        entry.pack(pady=5)
        entry.focus()

        tk.Button(root, text="Submit", command=submit).pack(pady=10)

        root.mainloop()

        if not key_holder["value"]:
            raise ValueError("API key not provided.")

        return key_holder["value"]

    # -----------------------------------
    def write_code(self, input_text):
        print("[AI] Sending request to Gemini...")

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=self.custom_prompt + "\n\n" + input_text
            )

            print("[AI] Response received")
            return response.text

        except Exception as e:
            print("[AI] Error:", e)
            return ""
