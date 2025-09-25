import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import google.generativeai as genai
import os
import re
import speech_recognition as sr
from gtts import gTTS
from playsound import playsound
from datetime import datetime
import time
import sys
import json

# --- AI Configuration ---
AI_NAME = "Sarah"

# --- Gemini API Configuration ---
API_KEY = os.getenv("google api key")

if not API_KEY:
    print("---------------------------------------------------------------------")
    print("CRITICAL ERROR: GOOGLE_API_KEY environment variable not found.")
    print("Please set your API key as a permanent environment variable in your system.")
    print("    For Windows: Search 'Environment Variables', add new User Variable GOOGLE_API_KEY")
    print("    For Linux/macOS: Add 'export GOOGLE_API_KEY=\"YOUR_KEY_HERE\"' to ~/.bashrc or ~/.zshrc")
    print("---------------------------------------------------------------------")
    messagebox.showerror("API Key Error", "GOOGLE_API_KEY environment variable not found. Please set your API key to proceed.")
    sys.exit("Exiting: API Key is required.")

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    messagebox.showerror("Gemini Error", f"Failed to configure Gemini API or initialize model: {e}. Check your API key and internet connection.")
    sys.exit("Exiting: Gemini API configuration failed.")

# --- Language Mapping for gTTS ---
LANG_CODES = {
    "english": "en",  "hindi": "hi", "spanish": "es", "french": "fr",
    "german": "de", "italian": "it",  "japanese": "ja", "korean": "ko",
    "chinese": "zh-cn", "marathi": "mr", "bengali": "bn", "gujarati":
    "gu", "punjabi": "pa", "tamil": "ta", "telugu": "te", "kannada":
    "kn", "malayalam": "ml", "urdu": "ur"
}

# --- Native Language Names for Display ---
NATIVE_LANG_NAMES = {
    "english": "English",
    "hindi": "हिन्दी",
    "spanish": "Español",
    "french": "Français",
    "german": "Deutsch",
    "italian": "Italiano",
    "japanese": "日本語",
    "korean": "한국어",
    "chinese": "中文 (简体)",
    "marathi": "मराठी",
    "bengali": "বাংলা",
    "gujarati": "ગુજરાતી",
    "punjabi": "ਪੰਜਾਬੀ",
    "tamil": "தமிழ்",
    "telugu": "తెలుగు",
    "kannada": "ಕನ್ನಡ",
    "malayalam": "മലയാളം",
    "urdu": "اردو"
}

# --- Reverse mapping for converting native name back to English name ---
REVERSE_NATIVE_LANG_NAMES = {v: k for k, v in NATIVE_LANG_NAMES.items()}

# --- Text-to-Speech Function (Sarah's Voice) ---
def speak_text(text, lang_code='en', filename='sarah_response.mp3'):
    """Converts text to speech using gTTS and plays it. Requires an internet connection."""
    try:
        clean_text = re.sub(r'[*_`]', '', text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        if not clean_text:
            return

        tts = gTTS(text=clean_text, lang=lang_code, slow=False)
        tts.save(filename)
        playsound(filename)
    except Exception as e:
        print(f"Error playing sound: {e}. This might be due to missing audio drivers (e.g., FFmpeg) or 'playsound' dependencies (like PyObjC for macOS or pywin32 for Windows).")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

# --- Speech-to-Text Function (Your Voice Commands) ---
def listen_command(lang_recognize="en-IN"):
    """Listens for voice input from the microphone and converts it to text."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.8)

        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=8)
            text = r.recognize_google(audio, language=lang_recognize)
            return text
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            return f"Error: Could not request results from Google Speech Recognition service; {e}"
        except sr.WaitTimeoutError:
            return ""
        except Exception as e:
            return f"Error during speech recognition: {e}"

# --- Greeting Function ---
def get_time_based_greeting():
    """Returns a greeting based on the current time of day."""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "Good morning"
    elif 12 <= current_hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"

# --- Chat History Management ---
CHAT_HISTORY_FILE = "chat_history.json"

def load_chat_history():
    """Loads chat history from a JSON file."""
    if os.path.exists(CHAT_HISTORY_FILE):
        try:
            with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
                # Ensure the history format is compatible with Gemini's expectations
                # Gemini expects {'role': 'user'/'model', 'parts': [{'text': '...'}]}
                # Our history stores plain text, so we'll convert it for Gemini
                gemini_formatted_history = []
                for entry in history:
                    role = 'user' if entry['sender'] == 'You' else 'model'
                    gemini_formatted_history.append({'role': role, 'parts': [{'text': entry['message']}]})
                return history, gemini_formatted_history
        except json.JSONDecodeError:
            print("Error decoding chat history file. Starting with empty history.")
            return [], []
    return [], []

def save_chat_history(history):
    """Saves chat history to a JSON file."""
    try:
        with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving chat history: {e}")

# --- GUI Application Class (CustomTkinter) ---
class SarahChatbotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"{AI_NAME} AI Assistant")
        self.geometry("800x950")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Chat History ---
        self.chat_messages_display = [] # Stores messages for GUI display {sender, message, timestamp}
        self.chat_messages_gemini_format = [] # Stores messages in Gemini's format for API
        self.load_history_on_startup()

        # --- Gemini Chat Session ---
        # Initialize chat_session with loaded history for continuity
        self.chat_session = model.start_chat(history=self.chat_messages_gemini_format)
        self.tools = []

        # --- Current Output Language State ---
        self.current_output_lang_english_name = "english"
        self.language_buttons = []

        # --- User Settings Variables ---
        self.current_font_size = ctk.IntVar(value=14)
        self.current_font_family = ctk.StringVar(value="Arial") # New: Default font family
        self.current_bg_color_option = ctk.StringVar(value="Default")
        self.current_text_color_option = ctk.StringVar(value="Default")

        # --- Output Textbox (Chat History) ---
        self.output_box = tk.Text(self, wrap="word", state="disabled",
                                  font=(self.current_font_family.get(), self.current_font_size.get()),
                                  relief="flat",
                                  highlightthickness=0)
        self.output_box.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")

        self.update_output_box_colors()
        self.update_output_box_text_colors()
        self.display_all_history() # Display loaded history on startup

        # --- Input Frame ---
        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.user_input_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Message Sarah...",
                                             height=40,
                                             font=(self.current_font_family.get(), self.current_font_size.get()))
        self.user_input_entry.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="ew")
        self.user_input_entry.bind("<Return>", self.send_text_query_event)

        self.send_button = ctk.CTkButton(self.input_frame, text="Send", command=self.send_text_query,
                                         width=80, height=40, font=(self.current_font_family.get(), self.current_font_size.get(), "bold"))
        self.send_button.grid(row=0, column=1, padx=(0, 0), pady=0)

        # --- Controls Frame (for Speak and Status) ---
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.controls_frame.grid_columnconfigure((0, 1), weight=1)

        self.speak_button = ctk.CTkButton(self.controls_frame, text="Speak to Sarah", command=self.start_voice_query_thread,
                                         font=(self.current_font_family.get(), max(10, self.current_font_size.get() - 2)))
        self.speak_button.grid(row=0, column=0, padx=(0, 5), pady=0, sticky="ew")

        self.status_label = ctk.CTkLabel(self.controls_frame, text="", font=(self.current_font_family.get(), max(10, self.current_font_size.get() - 2), "italic"),
                                         text_color=("gray50", "gray70"))
        self.status_label.grid(row=0, column=1, padx=(5, 0), pady=0, sticky="ew")

        # --- Settings Frame (Font Size, Font Family, Background Color, Text Color) ---
        self.settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.settings_frame.grid(row=3, column=0, padx=20, pady=(10, 10), sticky="ew")
        self.settings_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1) # Expanded columns

        # Font Size
        self.font_size_label = ctk.CTkLabel(self.settings_frame, text="Font Size:", font=(self.current_font_family.get(), 12, "bold"))
        self.font_size_label.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="w")
        self.font_size_option_menu = ctk.CTkOptionMenu(self.settings_frame, values=["10", "12", "14", "16", "18", "20"],
                                                         command=self.change_font_size,
                                                         variable=self.current_font_size,
                                                         font=(self.current_font_family.get(), 12))
        self.font_size_option_menu.grid(row=0, column=1, padx=(0, 20), pady=5, sticky="ew")

        # Font Family
        self.font_family_label = ctk.CTkLabel(self.settings_frame, text="Font Family:", font=(self.current_font_family.get(), 12, "bold"))
        self.font_family_label.grid(row=0, column=2, padx=(0, 5), pady=5, sticky="w")
        # You might want to get a list of available system fonts for a more dynamic option menu
        # For simplicity, providing a few common ones.
        self.font_family_option_menu = ctk.CTkOptionMenu(self.settings_frame,
                                                          values=["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana", "Georgia"],
                                                          command=self.change_font_family,
                                                          variable=self.current_font_family,
                                                          font=(self.current_font_family.get(), 12))
        self.font_family_option_menu.grid(row=0, column=3, padx=(0, 20), pady=5, sticky="ew")

        # Background Color
        self.bg_label = ctk.CTkLabel(self.settings_frame, text="Background:", font=(self.current_font_family.get(), 12, "bold"))
        self.bg_label.grid(row=0, column=4, padx=(0, 5), pady=5, sticky="w")
        self.bg_option_menu = ctk.CTkOptionMenu(self.settings_frame, values=["Default", "Light Blue", "Green", "Purple"],
                                                  command=self.change_background_color,
                                                  variable=self.current_bg_color_option,
                                                  font=(self.current_font_family.get(), 12))
        self.bg_option_menu.grid(row=0, column=5, padx=(0, 20), pady=5, sticky="ew")
       
        # Text Color Option
        self.text_color_label = ctk.CTkLabel(self.settings_frame, text="Text Color:", font=(self.current_font_family.get(), 12, "bold"))
        self.text_color_label.grid(row=0, column=6, padx=(0, 5), pady=5, sticky="w")
        self.text_color_option_menu = ctk.CTkOptionMenu(self.settings_frame, values=["Default", "White", "Black", "Gray", "Red", "Blue"],
                                                         command=self.change_text_color,
                                                         variable=self.current_text_color_option,
                                                         font=(self.current_font_family.get(), 12))
        self.text_color_option_menu.grid(row=0, column=7, padx=(0, 0), pady=5, sticky="ew")

        # --- Language Buttons Frame ---
        self.language_buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.language_buttons_frame.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="ew")
        num_lang_cols = 5
        for i in range(num_lang_cols):
            self.language_buttons_frame.grid_columnconfigure(i, weight=1)

        self.lang_buttons_label = ctk.CTkLabel(self.language_buttons_frame, text="Select Sarah's Output Language:", font=(self.current_font_family.get(), 14, "bold"))
        self.lang_buttons_label.grid(row=0, column=0, columnspan=num_lang_cols, pady=(0, 10), sticky="w")

        row_idx = 1
        col_idx = 0
        for english_name, native_name in NATIVE_LANG_NAMES.items():
            button = ctk.CTkButton(self.language_buttons_frame, text=native_name,
                                   command=lambda name=english_name: self.set_output_language(name),
                                   font=(self.current_font_family.get(), 12))
            button.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="ew")
            self.language_buttons.append((english_name, button))

            col_idx += 1
            if col_idx >= num_lang_cols:
                col_idx = 0
                row_idx += 1

        self._update_language_button_highlight(self.current_output_lang_english_name)

        # Initial greeting only if history is empty
        if not self.chat_messages_display:
            greeting_text = f"{get_time_based_greeting()}! I am {AI_NAME}, your personal AI assistant. How may I help you today?"
            self.display_message(greeting_text, AI_NAME)
            self.speak_initial_greeting()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_history_on_startup(self):
        self.chat_messages_display, self.chat_messages_gemini_format = load_chat_history()
        # Optionally, limit the history loaded into Gemini to avoid context window issues
        # For simplicity, we're loading all, but for very long histories, consider truncating.

    def on_closing(self):
        save_chat_history(self.chat_messages_display)
        self.destroy()

    def display_all_history(self):
        """Displays all loaded chat history in the output box."""
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", tk.END) # Clear existing content

        for msg in self.chat_messages_display:
            sender = msg['sender']
            message = msg['message']
            timestamp = msg['timestamp'] # Use stored timestamp
           
            if sender == AI_NAME:
                self.output_box.insert(tk.END, f"{sender} ({timestamp}): ", "ai")
                self.output_box.insert(tk.END, f"{message}\n\n", "text")
            elif sender == "You":
                self.output_box.insert(tk.END, f"{sender} ({timestamp}): ", "user")
                self.output_box.insert(tk.END, f"{message}\n\n", "text")
            elif sender == "System":
                self.output_box.insert(tk.END, f"{sender} ({timestamp}): ", "system")
                self.output_box.insert(tk.END, f"{message}\n\n", "text")
            else: # For "Error" or other general messages
                self.output_box.insert(tk.END, f"{sender} ({timestamp}): ", "error")
                self.output_box.insert(tk.END, f"{message}\n\n", "text")
       
        self.output_box.see(tk.END)
        self.output_box.configure(state="disabled")

    def update_output_box_colors(self):
        current_mode = ctk.get_appearance_mode()

        if current_mode == "Dark":
            output_box_bg_color_map = {
                "Default": "#1E1E1E",
                "Light Blue": "#4B5B6B",
                "Green": "#4A6E4A",
                "Purple": "#6A4A6A"
            }
        else:
            output_box_bg_color_map = {
                "Default": "white",
                "Light Blue": "#DBEEF4",
                "Green": "#E0FFE0",
                "Purple": "#F0E0F0"
            }

        selected_option = self.current_bg_color_option.get()
        self.output_box.configure(
            background=output_box_bg_color_map.get(selected_option, output_box_bg_color_map["Default"])
        )
        self.change_background_color(selected_option)

    def update_output_box_text_colors(self):
        current_mode = ctk.get_appearance_mode()
       
        text_color_map = {
            "Default": "white" if current_mode == "Dark" else "black",
            "White": "white",
            "Black": "black",
            "Gray": "gray50",
            "Red": "red",
            "Blue": "blue"
        }
       
        selected_option = self.current_text_color_option.get()
        default_text_color_for_box = text_color_map.get(selected_option, text_color_map["Default"])
        self.output_box.configure(foreground=default_text_color_for_box)

        current_font_val = self.current_font_size.get()
        current_font_family = self.current_font_family.get()
       
        self.output_box.tag_configure("user", foreground="blue", font=(current_font_family, current_font_val, "bold"))
        self.output_box.tag_configure("ai", foreground="green", font=(current_font_family, current_font_val, "bold"))
        self.output_box.tag_configure("system", foreground="orange", font=(current_font_family, current_font_val, "bold"))
        self.output_box.tag_configure("error", foreground="red", font=(current_font_family, current_font_val, "bold"))
        self.output_box.tag_configure("text", foreground=default_text_color_for_box, font=(current_font_family, current_font_val))

    def change_font_size(self, new_size_str):
        new_size = int(new_size_str)
        self.current_font_size.set(new_size)
        self._update_all_fonts()
        self.display_message(f"Font size changed to {new_size}.", "System")

    def change_font_family(self, new_family):
        self.current_font_family.set(new_family)
        self._update_all_fonts()
        self.display_message(f"Font family changed to {new_family}.", "System")

    def _update_all_fonts(self):
        """Helper to apply current font size and family to all relevant widgets."""
        current_size = self.current_font_size.get()
        current_family = self.current_font_family.get()

        self.output_box.configure(font=(current_family, current_size))
        self.update_output_box_text_colors()

        self.user_input_entry.configure(font=(current_family, current_size))
        self.send_button.configure(font=(current_family, current_size, "bold"))

        self.speak_button.configure(font=(current_family, max(10, current_size - 2)))
        self.status_label.configure(font=(current_family, max(10, current_size - 2), "italic"))

        self.font_size_label.configure(font=(current_family, max(10, current_size - 2), "bold"))
        self.font_family_label.configure(font=(current_family, max(10, current_size - 2), "bold"))
        self.bg_label.configure(font=(current_family, max(10, current_size - 2), "bold"))
        self.text_color_label.configure(font=(current_family, max(10, current_size - 2), "bold"))
       
        self.font_size_option_menu.configure(font=(current_family, max(10, current_size - 2)))
        self.font_family_option_menu.configure(font=(current_family, max(10, current_size - 2)))
        self.bg_option_menu.configure(font=(current_family, max(10, current_size - 2)))
        self.text_color_option_menu.configure(font=(current_family, max(10, current_size - 2)))

        self.lang_buttons_label.configure(font=(current_family, max(12, current_size)))
        for _, button in self.language_buttons:
            button.configure(font=(current_family, max(10, current_size - 2)))

    def change_background_color(self, new_color_option):
        self.current_bg_color_option.set(new_color_option)

        if ctk.get_appearance_mode() == "Dark":
            app_bg_color_map = {
                "Default": "#212325",
                "Light Blue": "#33495E",
                "Green": "#3A5C3A",
                "Purple": "#5E3A5E"
            }
            output_box_bg_color_map = {
                "Default": "#1E1E1E",
                "Light Blue": "#4B5B6B",
                "Green": "#4A6E4A",
                "Purple": "#6A4A6A"
            }
        else:
            app_bg_color_map = {
                "Default": "#EDEDED",
                "Light Blue": "#CCEBFC",
                "Green": "#CCFCCD",
                "Purple": "#FCCDCC"
            }
            output_box_bg_color_map = {
                "Default": "white",
                "Light Blue": "#DBEEF4",
                "Green": "#E0FFE0",
                "Purple": "#F0E0F0"
            }

        bg_for_app = app_bg_color_map.get(new_color_option, app_bg_color_map["Default"])
        bg_for_output_box = output_box_bg_color_map.get(new_color_option, output_box_bg_color_map["Default"])

        self.configure(fg_color=bg_for_app)
        self.output_box.configure(background=bg_for_output_box)
        self.display_message(f"Background color changed to {new_color_option}.", "System")

    def change_text_color(self, new_color_option):
        self.current_text_color_option.set(new_color_option)
        self.update_output_box_text_colors()
        self.display_message(f"Text color changed to {new_color_option}.", "System")

    def display_message(self, message, sender):
        self.output_box.configure(state="normal")
        timestamp = datetime.now().strftime("%I:%M %p")

        # Store message for history
        self.chat_messages_display.append({"sender": sender, "message": message, "timestamp": timestamp})

        # Also store for Gemini's history, converting 'You' to 'user' and others to 'model'
        # Note: Gemini history alternates, so if we're adding a 'System' or 'Error' message,
        # it might break the conversational flow if not handled carefully.
        # For simplicity, we only add 'You' and 'AI_NAME' messages to Gemini's actual history.
        if sender == "You":
            self.chat_messages_gemini_format.append({'role': 'user', 'parts': [{'text': message}]})
        elif sender == AI_NAME:
            self.chat_messages_gemini_format.append({'role': 'model', 'parts': [{'text': message}]})
        # If history gets too long, consider truncating chat_messages_gemini_format

        current_font_val = self.current_font_size.get()
        current_font_family = self.current_font_family.get()
        current_mode = ctk.get_appearance_mode()
       
        text_color_map = {
            "Default": "white" if current_mode == "Dark" else "black",
            "White": "white",
            "Black": "black",
            "Gray": "gray50",
            "Red": "red",
            "Blue": "blue"
        }
        default_text_color_for_box = text_color_map.get(self.current_text_color_option.get(), text_color_map["Default"])

        self.output_box.tag_configure("user", foreground="blue", font=(current_font_family, current_font_val, "bold"))
        self.output_box.tag_configure("ai", foreground="green", font=(current_font_family, current_font_val, "bold"))
        self.output_box.tag_configure("system", foreground="orange", font=(current_font_family, current_font_val, "bold"))
        self.output_box.tag_configure("error", foreground="red", font=(current_font_family, current_font_val, "bold"))
        self.output_box.tag_configure("text", foreground=default_text_color_for_box, font=(current_font_family, current_font_val))

        if sender == AI_NAME:
            self.output_box.insert(tk.END, f"{sender} ({timestamp}): ", "ai")
            self.output_box.insert(tk.END, f"{message}\n\n", "text")
        elif sender == "You":
            self.output_box.insert(tk.END, f"{sender} ({timestamp}): ", "user")
            self.output_box.insert(tk.END, f"{message}\n\n", "text")
        elif sender == "System":
            self.output_box.insert(tk.END, f"{sender} ({timestamp}): ", "system")
            self.output_box.insert(tk.END, f"{message}\n\n", "text")
        else:
            self.output_box.insert(tk.END, f"{sender} ({timestamp}): ", "error")
            self.output_box.insert(tk.END, f"{message}\n\n", "text")

        self.output_box.see(tk.END)
        self.output_box.configure(state="disabled")

    def speak_initial_greeting(self):
        greeting = get_time_based_greeting()
        welcome_message = f"{greeting}! I am {AI_NAME}, your personal AI assistant. How may I help you today?"
        thread = threading.Thread(target=speak_text, args=(welcome_message, "en"))
        thread.start()

    def _update_language_button_highlight(self, selected_english_name):
        default_fg_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
        selected_fg_color_light = "#67C2EC"
        selected_fg_color_dark = "#3A7EBf"

        if ctk.get_appearance_mode() == "Dark":
            current_selected_color = selected_fg_color_dark
            current_default_color = default_fg_color[1]
        else:
            current_selected_color = selected_fg_color_light
            current_default_color = default_fg_color[0]

        for english_name, button in self.language_buttons:
            if english_name == selected_english_name:
                button.configure(fg_color=current_selected_color)
            else:
                button.configure(fg_color=current_default_color)

    def set_output_language(self, english_lang_name):
        self.current_output_lang_english_name = english_lang_name
        self._update_language_button_highlight(english_lang_name)

        native_name = NATIVE_LANG_NAMES.get(english_lang_name, english_lang_name)
        display_message = f"Sarah's output language switched to {native_name}."
        self.display_message(display_message, "System")

        gtts_lang_code = LANG_CODES.get(english_lang_name.lower(), "en")
       
        confirmation_phrases = {
            "english": "Alright, I will speak in English now.",
            "hindi": "ठीक है, मैं अब हिंदी में बात करूंगी।",
            "spanish": "De acuerdo, hablaré en español ahora.",
            "french": "D'accord, je vais parler en français maintenant.",
            "german": "In Ordnung, ich werde jetzt auf Deutsch sprechen.",
            "italian": "Va bene, parlerò in italiano adesso.",
            "japanese": "はい、日本語で話します。",
            "korean": "네, 이제 한국어로 말할게요.",
            "chinese": "好的，我现在说中文。",
            "marathi": "ठीक आहे, मी आता मराठीत बोलेन.",
            "bengali": "ঠিক আছে, আমি এখন বাংলাতে কথা বলব।",
            "gujarati": "બરાબર, હું હવે ગુજરાતીમાં બોલીશ.",
            "punjabi": "ਠੀਕ ਹੈ, ਮੈਂ ਹੁਣ ਪੰਜਾਬੀ ਵਿੱਚ ਬੋਲਾਂਗੀ।",
            "tamil": "சரி, நான் இப்போது தமிழில் பேசுவேன்.",
            "telugu": "సరే, నేను ఇప్పుడు తెలుగులో మాట్లాడతాను.",
            "kannada": "ಸರಿ, ನಾನು ಈಗ ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡುತ್ತೇನೆ.",
            "malayalam": "ശരി, ഞാൻ ഇപ്പോൾ മലയാളത്തിൽ സംസാരിക്കും.",
            "urdu": "ٹھیک ہے، میں اب اردو میں بات کروں گی۔"
        }
       
        confirmation_phrase = confirmation_phrases.get(english_lang_name.lower(), f"Okay, I will speak in {english_lang_name} now.")

        thread = threading.Thread(target=speak_text, args=(confirmation_phrase, gtts_lang_code))
        thread.start()

    def send_text_query_event(self, event=None):
        self.send_text_query()

    def send_text_query(self):
        user_query = self.user_input_entry.get()
        if not user_query.strip():
            messagebox.showwarning("Input Empty", "Please type your question before sending.")
            return

        self.user_input_entry.delete(0, tk.END)
        self.display_message(user_query, "You")

        self.after(0, lambda: self.status_label.configure(text="Sarah is thinking..."))
        self.user_input_entry.configure(state="disabled")
        self.send_button.configure(state="disabled")
        self.speak_button.configure(state="disabled")

        target_lang_english_name = self.current_output_lang_english_name

        thread = threading.Thread(target=self._process_query, args=(user_query, target_lang_english_name))
        thread.start()

    def start_voice_query_thread(self):
        self.speak_button.configure(state="disabled", text="Listening...")
        self.user_input_entry.configure(state="disabled")
        self.send_button.configure(state="disabled")
        self.after(0, lambda: self.status_label.configure(text="Listening for your voice command (Say 'Sarah' to activate)..."))

        selected_output_lang_english = self.current_output_lang_english_name

        rec_lang_map = {
            "english": "en-US", "hindi": "hi-IN", "spanish": "es-ES", "french": "fr-FR",
            "german": "de-DE", "italian": "it-IT", "japanese": "ja-JP", "korean": "ko-KR",
            "chinese": "zh-CN", "marathi": "mr-IN", "bengali": "bn-IN", "gujarati": "gu-IN",
            "punjabi": "pa-IN", "tamil": "ta-IN", "telugu": "te-IN", "kannada": "kn-IN",
            "malayalam": "ml-IN", "urdu": "ur-PK"
        }
        rec_lang = rec_lang_map.get(selected_output_lang_english.lower(), "en-US")

        thread = threading.Thread(target=self._process_voice_query, args=(rec_lang,))
        thread.start()

    def _process_voice_query(self, rec_lang):
        user_command = listen_command(lang_recognize=rec_lang)
        self.after(0, self._handle_voice_result, user_command, rec_lang)

    def _handle_voice_result(self, user_command, rec_lang):
        self.speak_button.configure(state="normal", text="Speak to Sarah")
        self.user_input_entry.configure(state="normal")
        self.send_button.configure(state="normal")
        self.after(0, lambda: self.status_label.configure(text=""))

        if "Error:" in user_command:
            self.display_message(user_command, "Error")
            return
        elif not user_command.strip():
            self.display_message("No speech detected or could not understand.", "System")
            return

        user_command_lower = user_command.lower()
        wake_up_phrases = [AI_NAME.lower(), f"hey {AI_NAME.lower()}", f"hi {AI_NAME.lower()}"]
       
        # Check for language change commands (even without wake-up)
        # This allows direct commands like "speak in hindi"
        for lang_english_name, lang_native_name in NATIVE_LANG_NAMES.items():
            if f"speak in {lang_english_name}" in user_command_lower or \
               (lang_english_name != "english" and f"{lang_native_name.lower()} bolo" in user_command_lower):
                self.set_output_language(lang_english_name)
                self.after(0, lambda: self.status_label.configure(text=""))
                return
       
        # Check for exit commands
        if "exit" in user_command_lower or "quit" in user_command_lower or "bye" in user_command_lower or "goodbye" in user_command_lower:
            self.display_message("Exiting Sarah. Goodbye!", "System")
            speak_text("Goodbye!", "en")
            self.on_closing() # Call on_closing to save history
            return

        activated_by_wakeup = False
        query_after_wakeup = user_command_lower

        for phrase in wake_up_phrases:
            if phrase in user_command_lower:
                activated_by_wakeup = True
                # Remove the wake-up phrase, ensuring it's not part of the query sent to Gemini
                query_after_wakeup = user_command_lower.replace(phrase, "", 1).strip()
                break

        if activated_by_wakeup:
            self.display_message(user_command, "You (Voice - Wake-up Detected)")
            if not query_after_wakeup:
                self.after(0, lambda: self.status_label.configure(text="Listening for your command..."))
                speak_text("Yes?", LANG_CODES.get(self.current_output_lang_english_name, "en"))
                self.after(500, self.start_voice_query_thread)
                return

            self.after(0, lambda: self.status_label.configure(text="Sarah is thinking..."))
            self.user_input_entry.configure(state="disabled")
            self.send_button.configure(state="disabled")
            self.speak_button.configure(state="disabled")

            target_lang_english_name = self.current_output_lang_english_name

            thread = threading.Thread(target=self._process_query, args=(query_after_wakeup, target_lang_english_name))
            thread.start()
            return
        else:
            # If no wake-up phrase and not a special command, treat as a direct voice query
            self.display_message(user_command, "You (Voice)")
            self.after(0, lambda: self.status_label.configure(text="Sarah is thinking..."))
            self.user_input_entry.configure(state="disabled")
            self.send_button.configure(state="disabled")
            self.speak_button.configure(state="disabled")

            target_lang_english_name = self.current_output_lang_english_name

            thread = threading.Thread(target=self._process_query, args=(user_command, target_lang_english_name))
            thread.start()

    def _process_query(self, user_query, target_lang_english_name):
        try:
            # Ensure the chat session is re-initialized with current history if it's new/reset
            # This is critical for conversation continuity
            response = self.chat_session.send_message(user_query, tools=self.tools)
            ai_response = response.text

            gtts_lang_code = LANG_CODES.get(target_lang_english_name.lower(), "en")
           
            # Use Gemini to translate the response if target language is not English
            if target_lang_english_name != "english":
                try:
                    translation_prompt = f"Translate the following text into {target_lang_english_name}: {ai_response}"
                    translated_response_obj = model.generate_content(translation_prompt)
                    translated_ai_response = translated_response_obj.text
                    # Update the displayed message to the translated one
                    display_ai_response = translated_ai_response
                except Exception as e:
                    print(f"Error translating response: {e}. Falling back to English.")
                    display_ai_response = ai_response # Fallback to original if translation fails
            else:
                display_ai_response = ai_response

            self.after(0, lambda: self.display_message(display_ai_response, AI_NAME))
            self.after(0, lambda: speak_text(display_ai_response, gtts_lang_code))

        except Exception as e:
            error_message = f"An error occurred: {e}. Please check your internet connection or Gemini API key."
            self.after(0, lambda: self.display_message(error_message, "Error"))
            self.after(0, lambda: speak_text("I'm sorry, I encountered an error. Please try again.", "en")) # Always speak error in English

        finally:
            self.after(0, lambda: self.status_label.configure(text=""))
            self.after(0, lambda: self.user_input_entry.configure(state="normal"))
            self.after(0, lambda: self.send_button.configure(state="normal"))
            self.after(0, lambda: self.speak_button.configure(state="normal"))


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = SarahChatbotApp()
    app.mainloop()

