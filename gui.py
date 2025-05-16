import tkinter as tk
from tkinter import filedialog
from PIL import ImageTk, Image
from db import *
from colors_test import generate_outfit_suggestions, _closest_color_name

class WardrobeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Outfit Matcher for Colorblind Users")
        self.root.geometry("1200x700")

        self.username_label = tk.Label(root, text='Email or Username',font=("Arial", 12))
        self.username_entry = tk.Entry(root, font=("Arial", 12))
        self.password_label = tk.Label(root, text='Password',font=("Arial", 12))
        self.password_entry = tk.Entry(root, show="*", font=("Arial", 12))
        self.auth_button = tk.Button(root, text="Login", command=self.authenticate, font=("Arial", 12))
        self.toggle_mode_button = tk.Button(root, text="Switch to Sign Up", command=self.toggle_mode, font=("Arial", 12))

        self.mode = "login"
        self.username_label.pack(pady=5)
        self.username_entry.pack(pady=5)
        self.password_label.pack(pady=5)
        self.password_entry.pack(pady=5)
        self.auth_button.pack(pady=5)
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

    def logout(self):
        self.current_user = None
        self.wardrobe_id = None
        for widget in self.root.winfo_children():
            widget.destroy()
        self.__init__(self.root)  # Reinitialize to show login/signup screen
    
    def load_main_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        paned_window.pack(fill=tk.BOTH, expand=True)

        left_panel = tk.Frame(paned_window, padx=10, pady=10)
        right_panel = tk.Frame(paned_window, padx=10, pady=10)

        paned_window.add(left_panel, minsize=200)
        paned_window.add(right_panel, minsize=1000)

        # Left panel with buttons
        tk.Button(left_panel, text="Upload Item", command=self.upload_item, font=("Arial", 12)).pack(pady=8, fill=tk.X)
        tk.Button(left_panel, text="Generate Outfits", command=self.show_outfit_suggestions, font=("Arial", 12)).pack(pady=8, fill=tk.X)
        tk.Button(left_panel, text="View Saved Outfits", command=self.view_saved_outfits, font=("Arial", 12)).pack(pady=8, fill=tk.X)
        tk.Button(left_panel, text="View Wardrobe", command=self.display_wardrobe, font=("Arial", 12)).pack(pady=8, fill=tk.X)
        tk.Button(left_panel, text="Logout", command=self.logout, font=("Arial", 12)).pack(pady=8, fill=tk.X)
        
        self.right_panel = right_panel
        self.outfit_frame = right_panel

        from tkinter.scrolledtext import ScrolledText

        self.wardrobe_display = ScrolledText(self.root, height=8, font=("Consolas", 11))
        self.wardrobe_display.pack(side="bottom", fill="x", padx=10, pady=5)
        self.wardrobe_display.config(state="disabled")

        self.refresh_wardrobe_display()

    def log(self, widget, message):
        widget.config(state="normal")
        widget.insert(tk.END, message + "\n")
        widget.see(tk.END)
        widget.config(state="disabled")

    def upload_item(self):
        filepath = filedialog.askopenfilename()
        if not filepath:
            return

        img = Image.open(filepath).convert("RGB")

        def on_click(event):
            try:
                rgb = img.getpixel((event.x, event.y))
            except IndexError:
                self.log(self.wardrobe_display, "⚠️ Click inside the image bounds.")
                return
            clothing_type = clothing_type_var.get()
            insert_clothing_item(self.wardrobe_id, clothing_type, rgb[:3])
            self.log(self.wardrobe_display, f"Added {clothing_type}: {rgb} ({_closest_color_name(rgb)})")
            top.destroy()
            self.refresh_wardrobe_display()

        top = tk.Toplevel(self.root)
        canvas = tk.Canvas(top, width=img.width, height=img.height)
        canvas.pack()
        tk_img = ImageTk.PhotoImage(file=filepath)
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)
        canvas.image = tk_img
        canvas.bind("<Button-1>", on_click)

        clothing_type_var = tk.StringVar(top)
        clothing_type_var.set("tops")
        tk.OptionMenu(top, clothing_type_var, "tops", "pants", "shoes", "jackets").pack()

    def refresh_wardrobe_display(self):
        self.wardrobe = fetch_wardrobe_items(self.wardrobe_id)
        self.display_wardrobe()

    def delete_item(self, item_id):
        try:
            delete_clothing_item(item_id)
            self.log(self.wardrobe_display, f"✅ Deleted item with ID {item_id}.")
            self.refresh_wardrobe_display()
        except Exception as e:
            self.log(self.wardrobe_display, f"❌ Error deleting item: {e}")
    
    def display_wardrobe(self):
        for widget in self.outfit_frame.winfo_children():
            widget.destroy()

        canvas = tk.Canvas(self.outfit_frame)
        scrollbar = tk.Scrollbar(self.outfit_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        col = 0
        for category, items in self.wardrobe.items():
            cat_frame = tk.LabelFrame(scrollable_frame, text=category.capitalize(), font=("Arial", 12, "bold"))
            cat_frame.grid(row=0, column=col, padx=10, pady=10, sticky="nw")
            col += 1

            for item in items:
                color_name = _closest_color_name(item['rgb'])
                label = tk.Label(cat_frame, text=f"{color_name} - {item['rgb']}", font=("Arial", 11))
                label.pack(anchor="w")

                tk.Button(cat_frame, text="Delete", font=("Arial", 10),
                        command=lambda i=item['id']: self.delete_item(i)).pack(pady=2)


    def show_outfit_suggestions(self):
        self.display_outfits(generate_outfit_suggestions({k: [i['rgb'] for i in v] for k, v in self.wardrobe.items()}))

    def view_saved_outfits(self):
        self.display_outfits(fetch_saved_outfits(self.wardrobe_id), saved=True)

    def display_outfits(self, outfits, saved=False):
        for widget in self.outfit_frame.winfo_children():
            widget.destroy()

        canvas = tk.Canvas(self.outfit_frame)
        scrollbar = tk.Scrollbar(self.outfit_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        seen = set()
        row = 0
        col = 0
        
        for outfit in outfits:
            if saved:
                top_rgb, pant_rgb, shoe_rgb, jacket_rgb, score = outfit
            else:
                top_rgb, pant_rgb, shoe_rgb, score, jacket_rgb = outfit

            key = (top_rgb, pant_rgb, shoe_rgb, jacket_rgb)
            if not saved and key in seen:
                continue
            seen.add(key)

            frame = tk.Frame(scrollable_frame, bd=1, relief=tk.SOLID, padx=10, pady=10)
            frame.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            tk.Label(frame, text=f"Top: {_closest_color_name(top_rgb)} {top_rgb}", font=("Arial", 11)).pack(anchor="w")
            tk.Label(frame, text=f"Pant: {_closest_color_name(pant_rgb)} {pant_rgb}", font=("Arial", 11)).pack(anchor="w")
            tk.Label(frame, text=f"Shoe: {_closest_color_name(shoe_rgb)} {shoe_rgb}", font=("Arial", 11)).pack(anchor="w")
            if jacket_rgb and all(v is not None for v in jacket_rgb):
                tk.Label(frame, text=f"Jacket: {_closest_color_name(jacket_rgb)} {jacket_rgb}", font=("Arial", 11)).pack(anchor="w")
            tk.Label(frame, text=f"Score: {score}", font=("Arial", 11, "italic")).pack(anchor="w")

            if not saved:
                def save_callback(t=top_rgb, p=pant_rgb, s=shoe_rgb, j=jacket_rgb, sc=score):
                    top_id = get_item_id_by_color(self.wardrobe_id, "tops", t)
                    pant_id = get_item_id_by_color(self.wardrobe_id, "pants", p)
                    shoe_id = get_item_id_by_color(self.wardrobe_id, "shoes", s)
                    jacket_id = get_item_id_by_color(self.wardrobe_id, "jackets", j) if j else None
                    if save_outfit(self.wardrobe_id, top_id, pant_id, shoe_id, jacket_id, sc):
                        self.log(self.wardrobe_display, "Outfit saved!")
                    else: 
                        self.log(self.wardrobe_display, "Outfit already saved!")
                tk.Button(frame, text="Save Outfit", command=save_callback, font=("Arial", 11)).pack(pady=5)

            col += 1
            if col > 3:
                col = 0
                row += 1

    

if __name__ == "__main__":
    root = tk.Tk()
    app = WardrobeApp(root)
    root.mainloop()
