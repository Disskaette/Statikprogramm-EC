import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.title("Scroll-Test")

# --- Container ---
scroll_container = ttk.Frame(root)
scroll_container.pack(fill="both", expand=True)

canvas = tk.Canvas(scroll_container, background="#f4f4f4")
canvas.pack(side="left", fill="both", expand=True)

scrollbar_y = ttk.Scrollbar(
    scroll_container, orient="vertical", command=canvas.yview)
scrollbar_y.pack(side="right", fill="y")

scrollbar_x = ttk.Scrollbar(root, orient="horizontal", command=canvas.xview)
scrollbar_x.pack(side="bottom", fill="x")

canvas.configure(yscrollcommand=scrollbar_y.set,
                 xscrollcommand=scrollbar_x.set)

# --- Inner Frame ---
content_frame = ttk.Frame(canvas)
inner_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")

# --- Inhalt reinpacken (Test) ---
for i in range(50):
    lbl = ttk.Label(content_frame, text=f"Label {i} " + "—" * 30)
    lbl.grid(row=0, column=i, padx=10, pady=20)

# --- Scrollregion automatisch setzen ---


def on_configure(event):
    canvas.configure(scrollregion=canvas.bbox("all"))


content_frame.bind("<Configure>", on_configure)

# --- Dynamisch Breite updaten, wenn Canvas-Window sich verändert ---


def update_inner_width(event):
    canvas.itemconfig(inner_window, width=max(
        content_frame.winfo_reqwidth(), event.width))


canvas.bind("<Configure>", update_inner_width)

# --- Mausrad-Scrolling ---


def on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


def on_shift_mousewheel(event):
    canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")


canvas.bind("<Enter>", lambda e: canvas.bind_all(
    "<MouseWheel>", on_mousewheel))
canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
canvas.bind_all("<Shift-MouseWheel>", on_shift_mousewheel)

root.geometry("800x400")
root.mainloop()
