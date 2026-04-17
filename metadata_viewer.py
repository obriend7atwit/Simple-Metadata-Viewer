import hashlib
import json
import mimetypes
import os
import stat
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


def format_bytes(size):
    units = ["bytes", "KB", "MB", "GB", "TB", "PB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "bytes":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024


def format_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_metadata(file_path):
    path = Path(file_path)
    stats = path.stat()
    mime_type, encoding = mimetypes.guess_type(path.name)

    metadata = {
        "Name": path.name,
        "Full path": str(path.resolve()),
        "Parent folder": str(path.parent.resolve()),
        "Extension": path.suffix or "(none)",
        "MIME type": mime_type or "Unknown",
        "Encoding": encoding or "None detected",
        "Size": format_bytes(stats.st_size),
        "Size in bytes": str(stats.st_size),
        "Created": format_timestamp(stats.st_ctime),
        "Modified": format_timestamp(stats.st_mtime),
        "Last accessed": format_timestamp(stats.st_atime),
        "Read only": "Yes" if not os.access(path, os.W_OK) else "No",
        "Hidden": "Yes" if path.name.startswith(".") else "No",
        "Permissions": stat.filemode(stats.st_mode),
        "Owner user ID": str(stats.st_uid) if hasattr(stats, "st_uid") else "Unavailable",
        "Owner group ID": str(stats.st_gid) if hasattr(stats, "st_gid") else "Unavailable",
        "SHA-256": file_sha256(path),
    }

    return metadata


class MetadataViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Metadata Viewer")
        self.geometry("820x560")
        self.minsize(700, 440)

        self.file_path = tk.StringVar()
        self.metadata = {}

        self._build_ui()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top_frame = ttk.Frame(self, padding=12)
        top_frame.grid(row=0, column=0, sticky="ew")
        top_frame.columnconfigure(0, weight=1)

        path_entry = ttk.Entry(top_frame, textvariable=self.file_path)
        path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        path_entry.bind("<Return>", lambda _event: self.load_metadata())

        browse_button = ttk.Button(top_frame, text="Browse...", command=self.browse_file)
        browse_button.grid(row=0, column=1, padx=(0, 8))

        load_button = ttk.Button(top_frame, text="Load Metadata", command=self.load_metadata)
        load_button.grid(row=0, column=2)

        table_frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("field", "value"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("field", text="Metadata")
        self.tree.heading("value", text="Value")
        self.tree.column("field", width=180, minwidth=140, anchor="w", stretch=False)
        self.tree.column("value", width=560, minwidth=300, anchor="w", stretch=True)
        self.tree.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=y_scroll.set)

        bottom_frame = ttk.Frame(self, padding=(12, 0, 12, 12))
        bottom_frame.grid(row=2, column=0, sticky="ew")
        bottom_frame.columnconfigure(0, weight=1)

        self.status = ttk.Label(bottom_frame, text="Choose a file to inspect.")
        self.status.grid(row=0, column=0, sticky="w")

        copy_button = ttk.Button(bottom_frame, text="Copy JSON", command=self.copy_json)
        copy_button.grid(row=0, column=1, padx=(8, 0))

        save_button = ttk.Button(bottom_frame, text="Save JSON...", command=self.save_json)
        save_button.grid(row=0, column=2, padx=(8, 0))

    def browse_file(self):
        selected = filedialog.askopenfilename(title="Select a file")
        if selected:
            self.file_path.set(selected)
            self.load_metadata()

    def load_metadata(self):
        raw_path = self.file_path.get().strip().strip('"')
        if not raw_path:
            messagebox.showinfo("No file selected", "Choose a file first.")
            return

        path = Path(raw_path)
        if not path.exists():
            messagebox.showerror("File not found", "That path does not exist.")
            return
        if not path.is_file():
            messagebox.showerror("Not a file", "Please choose a file, not a folder.")
            return

        try:
            self.metadata = get_metadata(path)
        except OSError as error:
            messagebox.showerror("Could not read file", str(error))
            return

        self.tree.delete(*self.tree.get_children())
        for field, value in self.metadata.items():
            self.tree.insert("", "end", values=(field, value))

        self.status.config(text=f"Loaded metadata for {path.name}.")

    def metadata_as_json(self):
        if not self.metadata:
            return ""
        return json.dumps(self.metadata, indent=2)

    def copy_json(self):
        content = self.metadata_as_json()
        if not content:
            messagebox.showinfo("No metadata", "Load a file first.")
            return

        self.clipboard_clear()
        self.clipboard_append(content)
        self.status.config(text="Metadata copied to clipboard as JSON.")

    def save_json(self):
        content = self.metadata_as_json()
        if not content:
            messagebox.showinfo("No metadata", "Load a file first.")
            return

        selected = filedialog.asksaveasfilename(
            title="Save metadata",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not selected:
            return

        try:
            Path(selected).write_text(content, encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Could not save file", str(error))
            return

        self.status.config(text=f"Saved metadata to {Path(selected).name}.")


if __name__ == "__main__":
    app = MetadataViewer()
    app.mainloop()
