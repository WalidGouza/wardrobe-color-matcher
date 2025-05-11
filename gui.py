import tkinter as tk
from tkinter import filedialog
from PIL import Image
from db import *
from colors_test import generate_outfit_suggestions, _closest_color_name

class WardrobeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Outfit Matcher for Colorblind Users")
        self.root.geometry("1200x700")
        self.root.configure(padx=20, pady=20)

        self.username_entry = tk.Entry(root, font=("Arial", 14))
        self.password_entry = tk.Entry(root, show="*", font=("Arial", 14))
        self.auth_button = tk.Button(root, text="Login", font=("Arial", 12), command=self.authenticate)
        self.toggle_mode_button = tk.Button(root, text="Switch to Sign Up", font=("Arial", 12), command=self.toggle_mode)

        self.mode = "login"  # or "signup"

        tk.Label(root, text="Username", font=("Arial", 12)).pack(pady=5)
        self.username_entry.pack(pady=5, fill="x")
        tk.Label(root, text="Password", font=("Arial", 12)).pack(pady=5)
        self.password_entry.pack(pady=5, fill="x")
        self.auth_button.pack(pady=10)
        self.toggle_mode_button.pack(pady=5)

        self.wardrobe = {}
        self.current_user = None
        self.wardrobe_id = None

    def toggle_mode(self):
        self.mode = "signup" if self.mode == "login" else "login"
        self.auth_button.config(text="Sign Up" if self.mode == "signup" else "Login")
        self.toggle_mode_button.config(text="Switch to Login" if self.mode == "signup" else "Switch to Sign Up")

    def authenticate(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if self.mode == "login":
            if validate_user(username, password):
                self.current_user = username
                self.wardrobe_id = get_wardrobe_id(username)
                self.load_main_ui()
        else:
            create_user(username, password)
            self.current_user = username
            self.wardrobe_id = get_wardrobe_id(username)
            self.load_main_ui()

    def load_main_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        # Main horizontal container
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel (wardrobe + controls)
        left_panel = tk.Frame(main_frame, padx=10, pady=10)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)

        # Right panel (outfits)
        self.outfit_frame = tk.Frame(main_frame, padx=10, pady=10)
        self.outfit_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Controls in left panel
        tk.Button(left_panel, text="Upload Item", command=self.upload_item).pack(pady=5, fill=tk.X)
        tk.Button(left_panel, text="Generate Outfits", command=self.show_outfit_suggestions).pack(pady=5, fill=tk.X)
        tk.Button(left_panel, text="View Saved Outfits", command=self.view_saved_outfits).pack(pady=5, fill=tk.X)

        self.wardrobe_display = tk.Text(left_panel, height=15, width=40)
        self.wardrobe_display.pack(pady=10)

        tk.Label(left_panel, text="Delete Item ID:").pack(pady=(10, 0))
        self.delete_id_entry = tk.Entry(left_panel, width=10)
        self.delete_id_entry.pack()
        tk.Button(left_panel, text="Delete Item", command=self.delete_item).pack(pady=5)

        self.refresh_wardrobe_display()


    def log(self, widget, message):
        widget.insert(tk.END, message + "\n")
        widget.see(tk.END)

    def delete_item(self):
        try:
            item_id = int(self.delete_id_entry.get())
            delete_clothing_item(item_id)
            self.log(self.wardrobe_display, f"✅ Deleted item with ID {item_id}.")
            self.delete_id_entry.delete(0, tk.END)
            self.refresh_wardrobe_display()
        except ValueError:
            self.log(self.wardrobe_display, "❌ Please enter a valid integer ID.")
        except Exception as e:
            self.log(self.wardrobe_display, f"❌ Error deleting item: {e}")
    
    def upload_item(self):
        filepath = filedialog.askopenfilename()
        if not filepath:
            return

        img = Image.open(filepath)

        def on_click(event):
            try:
                rgb = img.getpixel((event.x, event.y))
            except IndexError:
                self.log(self.wardrobe_display, "⚠️ Click inside the image bounds.")
                return
            clothing_type = clothing_type_var.get()
            insert_clothing_item(self.wardrobe_id, clothing_type, rgb)
            self.log(self.wardrobe_display, f"Added {clothing_type}: {rgb} ({_closest_color_name(rgb)})")
            top.destroy()
            self.refresh_wardrobe_display()

        top = tk.Toplevel(self.root)
        top.title("Select Color")
        canvas = tk.Canvas(top, width=img.width, height=img.height)
        canvas.pack()
        tk_img = tk.PhotoImage(file=filepath)
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
        canvas.image = tk_img
        canvas.bind("<Button-1>", on_click)

        clothing_type_var = tk.StringVar(top)
        clothing_type_var.set("tops")
        tk.OptionMenu(top, clothing_type_var, "tops", "pants", "shoes", "jackets").pack(pady=5)

    def refresh_wardrobe_display(self):
        self.wardrobe = fetch_wardrobe_items(self.wardrobe_id)
        self.wardrobe_display.delete(1.0, tk.END)
        for category, items in self.wardrobe.items():
            self.wardrobe_display.insert(tk.END, f"{category}:")
            for item in items:
                color_name = _closest_color_name(item['rgb'])
                self.wardrobe_display.insert(tk.END, f" - {item['rgb']} ({color_name})\n")

    def show_outfit_suggestions(self):
        for widget in self.outfit_frame.winfo_children():
            widget.destroy()

        canvas = tk.Canvas(self.outfit_frame)
        scrollbar = tk.Scrollbar(self.outfit_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        suggestions = generate_outfit_suggestions({k: [i['rgb'] for i in v] for k, v in self.wardrobe.items()})
        seen = set()

        for top, pant, shoe, score, jacket in suggestions:
            key = (top, pant, shoe, jacket)
            if key in seen:
                continue
            seen.add(key)

            frame = tk.Frame(scrollable_frame, bd=1, relief=tk.SOLID, padx=10, pady=10)
            frame.pack(padx=5, pady=10, fill="x")

            tk.Label(frame, text=f"Top: {_closest_color_name(top)} {top}", font=("Arial", 12)).pack(anchor="w")
            tk.Label(frame, text=f"Pant: {_closest_color_name(pant)} {pant}", font=("Arial", 12)).pack(anchor="w")
            tk.Label(frame, text=f"Shoe: {_closest_color_name(shoe)} {shoe}", font=("Arial", 12)).pack(anchor="w")
            if jacket and all(v is not None for v in jacket):
                tk.Label(frame, text=f"Jacket: {_closest_color_name(jacket)} {jacket}", font=("Arial", 12)).pack(anchor="w")
            else:
                jacket = None
            tk.Label(frame, text=f"Score: {score}", font=("Arial", 12)).pack(anchor="w")

            def save_callback(t=top, p=pant, s=shoe, j=jacket, sc=score):
                top_id = get_item_id_by_color(self.wardrobe_id, "tops", t)
                pant_id = get_item_id_by_color(self.wardrobe_id, "pants", p)
                shoe_id = get_item_id_by_color(self.wardrobe_id, "shoes", s)
                jacket_id = get_item_id_by_color(self.wardrobe_id, "jackets", j) if j else None
                if save_outfit(self.wardrobe_id, top_id, pant_id, shoe_id, jacket_id, sc):
                    self.log(self.wardrobe_display, "✅ Outfit saved!")
                else:
                    self.log(self.wardrobe_display, "⚠️ Outfit already exists.")

            tk.Button(frame, text="Save Outfit", font=("Arial", 11), command=save_callback).pack(pady=5)

    def view_saved_outfits(self):
        for widget in self.outfit_frame.winfo_children():
            widget.destroy()

        canvas = tk.Canvas(self.outfit_frame)
        scrollbar = tk.Scrollbar(self.outfit_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        saved_outfits = fetch_saved_outfits(self.wardrobe_id)

        for outfit in saved_outfits:
            top_rgb, pant_rgb, shoe_rgb, jacket_rgb, score = outfit

            frame = tk.Frame(scrollable_frame, bd=1, relief=tk.SOLID, padx=10, pady=10)
            frame.pack(padx=5, pady=10, fill="x")

            tk.Label(frame, text=f"Top: {_closest_color_name(top_rgb)} {top_rgb}", font=("Arial", 12)).pack(anchor="w")
            tk.Label(frame, text=f"Pant: {_closest_color_name(pant_rgb)} {pant_rgb}", font=("Arial", 12)).pack(anchor="w")
            tk.Label(frame, text=f"Shoe: {_closest_color_name(shoe_rgb)} {shoe_rgb}", font=("Arial", 12)).pack(anchor="w")
            if jacket_rgb and all(v is not None for v in jacket_rgb):
                tk.Label(frame, text=f"Jacket: {_closest_color_name(jacket_rgb)} {jacket_rgb}", font=("Arial", 12)).pack(anchor="w")
            tk.Label(frame, text=f"Score: {score}", font=("Arial", 12)).pack(anchor="w")

if __name__ == "__main__":
    root = tk.Tk()
    app = WardrobeApp(root)
    root.mainloop()