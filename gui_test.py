import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from PIL import Image, ImageTk
from collections import Counter
from db import fetch_saved_outfits, get_item_id_by_color, insert_clothing_item, fetch_wardrobe_items, delete_clothing_item, validate_user, create_user, get_wardrobe_id, save_outfit
from colors_test import generate_outfit_suggestions, _closest_color_name
from itertools import product

# Extract dominant color

def get_dominant_color(image, resize_to=(100, 100)):
    small_img = image.resize(resize_to)
    pixels = list(small_img.getdata())
    color_counts = Counter(pixels)
    return color_counts.most_common(1)[0][0]

# Auth Screen

def show_login_screen():
    login_win = tk.Tk()
    login_win.title("Login or Sign Up")
    login_win.geometry("300x200")

    mode = tk.StringVar(value="login")

    tk.Label(login_win, text="Username").pack()
    username_entry = tk.Entry(login_win)
    username_entry.pack()

    tk.Label(login_win, text="Password").pack()
    password_entry = tk.Entry(login_win, show="*")
    password_entry.pack()

    def switch_mode():
        mode.set("signup" if mode.get() == "login" else "login")
        action_btn.config(text=mode.get().capitalize())

    def submit():
        username = username_entry.get()
        password = password_entry.get()
        if mode.get() == "login":
            if validate_user(username, password):
                login_win.destroy()
                launch_gui(username)
            else:
                messagebox.showerror("Error", "Invalid credentials")
        else:
            try:
                create_user(username, password)
                messagebox.showinfo("Success", "Account created. Please log in.")
                switch_mode()
            except:
                messagebox.showerror("Error", "Username already exists")

    action_btn = tk.Button(login_win, text="Login", command=submit)
    action_btn.pack(pady=10)
    tk.Button(login_win, text="Switch to Sign Up", command=switch_mode).pack()
    tk.Button(login_win, text="Exit", command=login_win.destroy).pack(pady=10)

    login_win.mainloop()

# Main App

def launch_gui(username):
    window = tk.Tk()
    window.title("Outfit Matcher")
    window.geometry("1200x700")

    current_category = tk.StringVar(value="tops")
    WARDROBE_ID = get_wardrobe_id(username)

    sidebar = tk.Frame(window)
    sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

    tk.Label(sidebar, text="Select Clothing Type:").pack()
    for category in ["tops", "pants", "shoes", "jackets"]:
        tk.Radiobutton(sidebar, text=category.capitalize(), variable=current_category, value=category).pack(anchor=tk.W)

    canvas = tk.Canvas(window, width=300, height=300, bg='gray')
    canvas.pack(side=tk.LEFT, padx=10)

    right_panel = tk.Frame(window)
    right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    wardrobe_display = scrolledtext.ScrolledText(right_panel, width=60, height=15)
    wardrobe_display.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

    outfit_canvas = tk.Canvas(right_panel)
    outfit_scrollbar = tk.Scrollbar(right_panel, orient="vertical", command=outfit_canvas.yview)
    outfit_scrollable_frame = tk.Frame(outfit_canvas)

    outfit_scrollable_frame.bind(
        "<Configure>", lambda e: outfit_canvas.configure(scrollregion=outfit_canvas.bbox("all"))
    )
    
    outfit_canvas.create_window((0, 0), window=outfit_scrollable_frame, anchor="nw")
    outfit_canvas.configure(yscrollcommand=outfit_scrollbar.set)

    outfit_canvas.pack(side="left", fill="both", expand=True)
    outfit_scrollbar.pack(side="right", fill="y")
    
    def log(text_widget, message):
        text_widget.insert(tk.END, message + "\n")
        text_widget.see(tk.END)

    def upload_image():
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            original_img = Image.open(file_path).convert('RGB')
            display_img = original_img.copy()
            display_img.thumbnail((300, 300))

            canvas.img = display_img
            canvas.original_img = original_img
            img_tk = ImageTk.PhotoImage(display_img)

            canvas.image = img_tk
            canvas.delete("all")
            canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)

            rgb = get_dominant_color(original_img)
            insert_clothing_item(WARDROBE_ID, current_category.get(), rgb)
            name = _closest_color_name(rgb)
            log(wardrobe_display, f"✅ Auto-added {name} ({rgb}) to {current_category.get()}.")

    def on_click(event):
        if hasattr(canvas, "original_img"):
            img = canvas.original_img
            if 0 <= event.x < img.width and 0 <= event.y < img.height:
                rgb = img.getpixel((event.x, event.y))
                insert_clothing_item(WARDROBE_ID, current_category.get(), rgb)
                name = _closest_color_name(rgb)
                log(wardrobe_display, f"🖱️ Manually added {name} ({rgb}) to {current_category.get()}.")

    def delete_item():
        try:
            item_id = int(delete_id_entry.get())
            delete_clothing_item(item_id)
            log(wardrobe_display, f"✅ Deleted item with ID {item_id}.")
            delete_id_entry.delete(0, tk.END)
            view_wardrobe()
        except Exception as e:
            log(wardrobe_display, f"❌ Error deleting item: {e}")

    def view_wardrobe():
        wardrobe_display.delete(1.0, tk.END)
        wardrobe = fetch_wardrobe_items(WARDROBE_ID)
        log(wardrobe_display, f"👕 {username.capitalize()}'s Current Wardrobe:")
        for category, items in wardrobe.items():
            log(wardrobe_display, f"{category.capitalize()} ({len(items)}):")
            for item in items:
                rgb = item['rgb']
                name = _closest_color_name(rgb)
                log(wardrobe_display, f"  [ID {item['id']}] - {name} ({rgb})")
    
    saved_outfits_set = set()
    
    def generate_outfits():
        for widget in outfit_scrollable_frame.winfo_children():
            widget.destroy()

        wardrobe = fetch_wardrobe_items(WARDROBE_ID)
        outfit_list = generate_outfit_suggestions(wardrobe)
        for top, pant, shoe, jacket, score in outfit_list:
            text = (
                f"Top: {_closest_color_name(top)} {top}\n"
                f"Pants: {_closest_color_name(pant)} {pant}\n"
                f"Shoes: {_closest_color_name(shoe)} {shoe}\n"
                f"Jacket: {_closest_color_name(jacket)} {jacket}\n"
                f"Score: {score}\n"
            )
            print(f"TEXT: {text}")
            frame = tk.Frame(outfit_scrollable_frame, pady=5, relief="groove", bd=1)
            frame.pack(fill='x', padx=5, pady=2)
            tk.Label(frame, text=text, justify='left', anchor='w').pack(anchor='w')

            def save_callback(t=top, p=pant, s=shoe, j=jacket, sc=score):
                key = (t, p, s)
                if key in saved_outfits_set:
                    log(wardrobe_display, "⚠️ Outfit already saved.")
                    return
                top_id = get_item_id_by_color(WARDROBE_ID, "tops", t)
                pant_id = get_item_id_by_color(WARDROBE_ID, "pants", p)
                shoe_id = get_item_id_by_color(WARDROBE_ID, "shoes", s)
                jacket_id = get_item_id_by_color(WARDROBE_ID, "jackets", j) if j else None
                if top_id and pant_id and shoe_id:
                    save_outfit(WARDROBE_ID, top_id, pant_id, shoe_id, jacket_id, score=sc)
                    saved_outfits_set.add(key)
                    log(wardrobe_display, "✅ Outfit saved!")
                else:
                    log(wardrobe_display, "❌ Could not find matching item IDs.")
            
            tk.Button(frame, text="Save Outfit", command=save_callback).pack(anchor='e')

    def view_saved_outfits():
        for widget in outfit_scrollable_frame.winfo_children():
            widget.destroy()

        outfits = fetch_saved_outfits(WARDROBE_ID)
        for outfit in outfits:
            top_rgb = (outfit['top_r'], outfit['top_g'], outfit['top_b'])
            pants_rgb = (outfit['pants_r'], outfit['pants_g'], outfit['pants_b'])
            shoes_rgb = (outfit['shoes_r'], outfit['shoes_g'], outfit['shoes_b'])
            jacket_rgb = (outfit['jacket_r'], outfit['jacket_g'], outfit['jacket_b'])
            score = outfit['score']
            if jacket_rgb:
                text = (
                    f"Top: {_closest_color_name(top_rgb)} {top_rgb}\n"
                    f"Pants: {_closest_color_name(pants_rgb)} {pants_rgb}\n"
                    f"Shoes: {_closest_color_name(shoes_rgb)} {shoes_rgb}\n"
                    f"Jacket: {_closest_color_name(jacket_rgb)} {jacket_rgb}\n"
                    f"Score: {score}\n"
                )
            else:
                text = (
                    f"Top: {_closest_color_name(top_rgb)} {top_rgb}\n"
                    f"Pants: {_closest_color_name(pants_rgb)} {pants_rgb}\n"
                    f"Shoes: {_closest_color_name(shoes_rgb)} {shoes_rgb}\n"
                    f"Score: {score}\n"
                )
                
            frame = tk.Frame(outfit_scrollable_frame, pady=5, relief="groove", bd=1)
            frame.pack(fill='x', padx=5, pady=2)
            tk.Label(frame, text=text, justify='left', anchor='w').pack(anchor='w')

    # Sidebar controls
    tk.Button(sidebar, text="Upload Image", command=upload_image).pack(pady=10)
    canvas.bind("<Button-1>", on_click)

    tk.Label(sidebar, text="Delete Item ID:").pack(pady=(10, 0))
    delete_id_entry = tk.Entry(sidebar, width=10)
    delete_id_entry.pack()
    tk.Button(sidebar, text="Delete Item", command=delete_item).pack(pady=5)
    tk.Button(sidebar, text="View Wardrobe", command=view_wardrobe).pack(pady=5)
    tk.Button(sidebar, text="Generate Outfits", command=generate_outfits).pack(pady=10)
    tk.Button(sidebar, text="View Saved Outfits", command=view_saved_outfits).pack(pady=5)
    tk.Button(sidebar, text="Logout", command=lambda: (window.destroy(), show_login_screen())).pack(pady=5)

    window.mainloop()

if __name__ == '__main__':
    show_login_screen()
