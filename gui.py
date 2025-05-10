import tkinter as tk
from tkinter import filedialog, scrolledtext
from PIL import Image, ImageTk
from collections import Counter
from db import insert_clothing_item, fetch_wardrobe_items, delete_clothing_item, validate_user, create_user, get_wardrobe_id
from colors_test import generate_and_print_outfits, _closest_color_name

WARDROBE_ID = 1  # Assuming default

def get_dominant_color(image, resize_to=(100, 100)):
    small_img = image.resize(resize_to)
    pixels = list(small_img.getdata())
    color_counts = Counter(pixels)
    return color_counts.most_common(1)[0][0]

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
                launch_gui(username)  # Start GUI with logged-in user
            else:
                tk.messagebox.showerror("Error", "Invalid credentials")
        else:
            try:
                create_user(username, password)
                tk.messagebox.showinfo("Success", "Account created. Please log in.")
                switch_mode()
            except:
                tk.messagebox.showerror("Error", "Username already exists")

    action_btn = tk.Button(login_win, text="Login", command=submit)
    action_btn.pack(pady=10)

    tk.Button(login_win, text="Switch to Sign Up", command=switch_mode).pack()

    login_win.mainloop()


def launch_gui(username):
    window = tk.Tk()
    window.title("Outfit Matcher")
    window.geometry("900x600")

    current_category = tk.StringVar(value="tops")
    WARDROBE_ID = get_wardrobe_id(username)

    # Sidebar
    frame = tk.Frame(window)
    frame.pack(side=tk.LEFT, fill=tk.Y)

    tk.Label(frame, text="Select Clothing Type:").pack()
    for category in ["tops", "pants", "shoes", "jackets"]:
        tk.Radiobutton(frame, text=category.capitalize(), variable=current_category, value=category).pack(anchor=tk.W)

    output_text = scrolledtext.ScrolledText(window, width=60, height=30)
    output_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    tk.Label(frame, text="Delete Item ID:").pack(pady=(10, 0))
    delete_id_entry = tk.Entry(frame, width=10)
    delete_id_entry.pack()

    def delete_item():
        try:
            item_id = int(delete_id_entry.get())
            delete_clothing_item(item_id)
            output_text.insert(tk.END, f"✅ Deleted item with ID {item_id}.\n")
            delete_id_entry.delete(0, tk.END)
            view_wardrobe()  # Refresh view
        except Exception as e:
            output_text.insert(tk.END, f"⚠️ Error deleting item: {e}\n")

    tk.Button(frame, text="Delete Item", command=delete_item).pack(pady=5)

    
    def view_wardrobe():
        wardrobe = fetch_wardrobe_items(WARDROBE_ID)
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, f"👕 {username.capitalize()}'s Current Wardrobe Contents:\n\n")
        for category, items in wardrobe.items():
            output_text.insert(tk.END, f"{category.capitalize()} ({len(items)}):\n")
            for item in items:
                rgb = item['rgb']
                name = _closest_color_name(rgb)
                output_text.insert(tk.END, f"  [ID {item['id']}] - {name} ({rgb})\n")
            output_text.insert(tk.END, "\n")
        output_text.see(tk.END)
    
    tk.Button(frame, text="View Wardrobe", command=view_wardrobe).pack(pady=10)
    
    # Upload image + auto sample
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

            # Automatically pick dominant color
            rgb = get_dominant_color(original_img)
            insert_clothing_item(WARDROBE_ID, current_category.get(), rgb)
            name = _closest_color_name(rgb)
            output_text.insert(tk.END, f"Auto-added {name} ({rgb}) to {current_category.get()}.\n")
            output_text.see(tk.END)

    tk.Button(frame, text="Upload Image", command=upload_image).pack(pady=10)

    def generate_outfits():
        # Fetch wardrobe from database
        wardrobe_db = fetch_wardrobe_items(WARDROBE_ID)

        # Flatten wardrobe to match expected format: {tops: [rgb, ...], ...}
        wardrobe = {
            category: [item['rgb'] for item in items]
            for category, items in wardrobe_db.items()
        }

        # Clear the output box
        output_text.delete(1.0, tk.END)

        # Redirect stdout to show results in GUI
        import sys
        sys.stdout = StdoutRedirector(output_text)

        try:
            generate_and_print_outfits(wardrobe)
        except Exception as e:
            print(f"⚠️ Error generating outfits: {e}")
        finally:
            sys.stdout = sys.__stdout__


    tk.Button(frame, text="Generate Outfits", command=generate_outfits).pack(pady=10)

    # Optional: manual click override
    def on_click(event):
        if hasattr(canvas, "img") and hasattr(canvas, "original_img"):
            img = canvas.original_img
            if 0 <= event.x < img.width and 0 <= event.y < img.height:
                rgb = img.getpixel((event.x, event.y))
                insert_clothing_item(WARDROBE_ID, current_category.get(), rgb)
                name = _closest_color_name(rgb)
                output_text.insert(tk.END, f"Manually added {name} ({rgb}) to {current_category.get()}.\n")
                output_text.see(tk.END)

    canvas = tk.Canvas(window, width=300, height=300, bg='gray')
    canvas.pack(side=tk.LEFT, padx=10)
    canvas.bind("<Button-1>", on_click)

    window.mainloop()

# Redirect stdout to GUI
import io
class StdoutRedirector(io.StringIO):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, s):
        self.text_widget.insert(tk.END, s)
        self.text_widget.see(tk.END)

    def flush(self):
        pass

if __name__ == '__main__':
    show_login_screen()
