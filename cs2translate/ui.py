import io

from tkinter import filedialog as fd
from tkinter import messagebox as mb
import customtkinter as ctk

from cs2translate.config import Config
from cs2translate.translator import Translation
from cs2translate.langs import (
    get_supported_language_names,
    language_code_to_name,
    language_name_to_code,
    lid176_language_code_to_name,
)

def configure_ctk_theme(dark: bool = True):
    ctk.set_appearance_mode("dark" if dark else "light")
    ctk.set_default_color_theme("blue")

class Group(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, config: Config, on_apply: callable):
        super().__init__(master)
        self.title("Settings")
        self.resizable(False, False)
        self.grab_set()

        self._on_apply = on_apply
        self._create_widgets()
        self._sync_widgets(config)

    def _add_setting(
        self,
        widget: type[ctk.CTkBaseClass],
        label: str | None = None,
        padx = 4,
        pady = (6, 6)
    ):
        """
        Helper for packing setting widgets with consistent padding as well as
        creating optional labels for them.
        """
        if label is not None:
            # create additional label widget
            label = ctk.CTkLabel(widget.master, height=16, text=label, anchor=ctk.W)
            label.pack(fill=ctk.X, padx=padx+2, pady=(pady[1], 0))

            # this now becomes the space in between label and widget
            pady = (4, pady[1])

        # pack widget below correctly
        widget.pack(fill=ctk.X, padx=padx, pady=pady)

    def _create_widgets(self):
        self._create_widgets_path()
        self._create_widgets_target_lang()
        self._create_widgets_ignore_own()
        self._create_widgets_ignore_english()

        bottom_group = Group(self)
        bottom_group.pack(
            side=ctk.BOTTOM,
            fill=ctk.X,
            padx=4,
            pady=4
        )

        # restore defaults button
        ctk.CTkButton(
            bottom_group,
            width=128,
            height=25,
            text="Restore Defaults",
            command=self._cmd_restore_defaults
        ).pack(
            side=ctk.LEFT,
            padx=(0, 32)
        )

        # apply button
        ctk.CTkButton(
            bottom_group,
            width=72,
            height=25,
            text="OK",
            command=self._cmd_apply
        ).pack(
            side=ctk.RIGHT
        )

        # clear chat history button
        ctk.CTkButton(
            self,
            width=128,
            height=25,
            text="Clear History",
            command=self._cmd_clear_history
        ).pack(
            side=ctk.BOTTOM,
            anchor=ctk.W,
            pady=(6, 0),
            padx=4
        )

    def _create_widgets_path(self):
        group = Group(self)

        # file path entry
        self.path_entry = ctk.CTkEntry(
            group,
            width=256,
            height=25,
            placeholder_text="path/to/console.log",
            border_width=1,
        )
        self.path_entry.pack(
            side=ctk.LEFT,
            fill=ctk.X,
            expand=True
        )

        # browse button
        ctk.CTkButton(
            group,
            width=72,
            height=25,
            text="Browse",
            command=self._cmd_browse_log_path
        ).pack(
            side=ctk.LEFT,
            padx=(4, 0)
        )

        self._add_setting(
            group,
            label="Location of console.log:"
        )

    def _create_widgets_target_lang(self):
        self.target_lang_combo = ctk.CTkComboBox(
            self,
            height=25,
            values=get_supported_language_names(),
            border_width=1
        )
        self._add_setting(
            self.target_lang_combo,
            label="Translate into:"
        )

    def _create_widgets_ignore_own(self):
        group = Group(self)
        self.ignore_own_var = ctk.BooleanVar(group)

        # ignore own messages toggle
        ctk.CTkCheckBox(
            group,
            height=25,
            text="Ignore my own messages",
            variable=self.ignore_own_var,
            border_width=1,
            checkbox_width=20,
            checkbox_height=20
        ).pack(
            side=ctk.LEFT,
            fill=ctk.X,
            expand=True
        )

        # entry for username
        self.name_entry = ctk.CTkEntry(
            group,
            height=25,
            placeholder_text="Username",
            border_width=1
        )
        self.name_entry.pack(
            side=ctk.RIGHT,
            padx=(4, 0),
            fill=ctk.X,
            expand=True
        )

        self._add_setting(group)

    def _create_widgets_ignore_english(self):
        self.ignore_english_var = ctk.BooleanVar(self)
        widget = ctk.CTkCheckBox(
            self,
            height=25,
            text="Ignore messages in English",
            variable=self.ignore_english_var,
            # TODO: export this into _STANDARD_CHECK_BOX_PARAMS (and similar)
            border_width=1,
            checkbox_width=20,
            checkbox_height=20
        )
        self._add_setting(
            widget,
            pady=(0, 6) # less padding on top so all toggles look like one block
        )

    def _set_entry_text(self, entry: ctk.CTkEntry, text: str):
        entry.delete(0, ctk.END)
        if text.strip():
            entry.insert(0, text)
        else:
            # manually force CTk to show the placeholder again
            entry._activate_placeholder()

    def _sync_widgets(self, config: Config):
        self._set_entry_text(self.path_entry, config.console_log_path)
        self._set_entry_text(self.name_entry, config.own_username)

        lang = language_code_to_name(config.output_language)
        self.target_lang_combo.set(lang)

        self.ignore_own_var.set(config.ignore_own_messages)
        self.ignore_english_var.set(config.ignore_english)

    def _cmd_browse_log_path(self):
        path = fd.askopenfilename(
            title="Select console.log",
            filetypes=[
                ("Log files", "*.log"),
                ("All files", "*.*")
            ]
        )
        if path:
            self._set_entry_text(self.path_entry, path)

    def _confirm(self, title: str, message: str):
        return mb.askyesno(title, message, parent=self)

    def _cmd_clear_history(self):
        if self._confirm(
            "Clear History",
            "Clear translation history?\nAll previously translated messages will be deleted.",
        ):
            self.master.clear_messages()

    def _cmd_restore_defaults(self):
        if self._confirm(
            "Restore Defaults",
            "Restore default settings?\nAll of your changes will be permanently lost.",
        ):
            self._sync_widgets(Config())

    def _report_invalid(self, name: str):
        mb.showerror(
            "Invalid Setting",
            f"Please enter a valid {name}."
        )

    def _cmd_apply(self):
        # username provided?
        if self.ignore_own_var.get() and not self.name_entry.get().strip():
            self._report_invalid("username")
            return

        # target language valid?
        output_lang = self.target_lang_combo.get().strip()
        output_lang = language_name_to_code(output_lang)
        if output_lang is None:
            self._report_invalid("target language")
            return

        self._on_apply(Config(
            console_log_path    = self.path_entry.get().strip(),
            output_language     = output_lang,
            ignore_own_messages = self.ignore_own_var.get(),
            own_username        = self.name_entry.get().strip(),
            ignore_english      = self.ignore_english_var.get()
        ))
        self.destroy()

class AppWindow(ctk.CTk):
    def __init__(self, on_open_settings: callable):
        # create window
        super().__init__()
        self.title("CS2 Translator")
        self.geometry("360x480")
        self.minsize(360, 480)

        self._on_open_settings = on_open_settings
        self._create_widgets()

    def _create_widgets(self):
        # bottom button container
        bottom_group = Group(self)
        bottom_group.pack(
            side=ctk.BOTTOM,
            fill=ctk.X,
            padx=(8, 4),
            pady=4
        )

        # status message display
        self.status_label = ctk.CTkLabel(
            bottom_group,
            height=25,
            text="",
            anchor=ctk.W,
            text_color="gray60"
        )
        self.status_label.pack(
            side=ctk.LEFT,
            fill=ctk.X
        )

        # settings button
        ctk.CTkButton(
            bottom_group,
            width=64,
            height=25,
            text="Settings",
            command=self._on_open_settings,
        ).pack(
            side=ctk.RIGHT
        )

        # chat box (absorb remaining space)
        self.chat_box = ctk.CTkTextbox(
            self,
            wrap=ctk.WORD,
            state=ctk.DISABLED,
            font=ctk.CTkFont("Consolas", 14),
            corner_radius=0,
            text_color="gray80"
        )
        self.chat_box.pack(
            fill=ctk.BOTH,
            expand=True
        )

    def set_status_message(self, message: str):
        self.status_label.configure(text=message)

    def display_messages(self, items: list[Translation]):
        # format and concatenate the messages
        # [<chat>] <player>: (from <language>/error) <message>
        buffer = io.StringIO()
        for it in items:
            buffer.write(f"[{it.message.chat}] {it.message.player}: ")
            if it.text:
                if it.lang:
                    lang_name = lid176_language_code_to_name(it.lang)
                    buffer.write(f"(from {lang_name}) ")
                buffer.write(it.text)
                buffer.write("\n")
            else:
                if it.error is not None:
                    buffer.write("(error)")
                buffer.write(it.message.text)
                buffer.write("\n")

        # display in chat textbox
        self.chat_box.configure(state="normal")
        self.chat_box.insert(ctk.END, buffer.getvalue())
        self.chat_box.see(ctk.END)
        self.chat_box.configure(state="disabled")

    def clear_messages(self):
        self.chat_box.configure(state="normal")
        self.chat_box.delete(0.0, ctk.END)
        self.chat_box.configure(state="disabled")
