import colorsys
import webcolors
from itertools import product, combinations
from collections import Counter

MIN_ACCEPTABLE_SCORE = 2.5

# Color conversion
def ___rgb_to_hsv(rgb):
    return colorsys.rgb_to_hsv(*[x / 255.0 for x in rgb])

def ___hsv_to_rgb(hsv):
    return tuple(round(x * 255) for x in colorsys.hsv_to_rgb(*hsv))

def ___rotate_hue(h, degrees):
    return (h + degrees / 360.0) % 1.0

# Distance between two colors
def ___color_distance(c1, c2):
    return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5

# Complementary and analogous color logic
def __get_complementary_color(rgb):
    h, s, v = ___rgb_to_hsv(rgb)
    return ___hsv_to_rgb((___rotate_hue(h, 180), s, v))

def __is_complementary(c1, c2, threshold=50):
    return ___color_distance(__get_complementary_color(c1), c2) < threshold

def __is_analogous(c1, c2, threshold=50):
    h1, _, _ = ___rgb_to_hsv(c1)
    h2, _, _ = ___rgb_to_hsv(c2)
    h_diff = min(abs(h1 - h2), 1 - abs(h1 - h2)) * 360
    return h_diff < 30 and ___color_distance(c1, c2) < threshold

def __is_neutral(c1, c2, threshold=50):
    neutrals = [
        (255, 255, 255), (0, 0, 0), (128, 128, 128), (192, 192, 192),
        (160, 82, 45), (245, 245, 220)
    ]
    for neutral in neutrals:
        if ___color_distance(c1, neutral) < threshold or ___color_distance(c2, neutral) < threshold:
            return True
    return False

# Outfit scoring
def _score_outfit(*colors):
    total_score = 0
    comparisons = 0

    for c1, c2 in combinations(colors, 2):
        comparisons += 1
        if __is_complementary(c1, c2):
            total_score += 3  # Strong match
        elif __is_analogous(c1, c2):
            total_score += 2  # Good match
        elif __is_neutral(c1, c2):
            total_score += 1  # Acceptable match
        else:
            total_score += 0  # No match

    if comparisons == 0:
        return 0

    # Normalize to a score out of 5
    max_possible_score = comparisons * 3  # 3 is the highest score per pair
    normalized_score = (total_score / max_possible_score) * 5
    return round(normalized_score, 2)

# Closest color name using webcolors
def _closest_color_name(rgb):
    try:
        return webcolors.rgb_to_name(rgb).title()
    except ValueError:
        min_distance = float('inf')
        closest_name = None
        for name in webcolors.names(spec="css3"):
            r, g, b = webcolors.name_to_rgb(name, spec="css3")
            dist = ___color_distance(rgb, (r, g, b))
            if dist < min_distance:
                min_distance = dist
                closest_name = name.title()
        return closest_name

def get_dominant_color(image, resize_to=(100, 100)):
    small_img = image.resize(resize_to)
    pixels = list(small_img.getdata())
    color_counts = Counter(pixels)
    return color_counts.most_common(1)[0][0]

# Generate combinations and print
def generate_outfit_suggestions(wardrobe):
    
    tops = wardrobe.get("tops", [])
    pants = wardrobe.get("pants", [])
    shoes = wardrobe.get("shoes", [])
    jackets = wardrobe.get("jackets", [])
    
    outfits = []
    if not jackets:
        jackets = [None]  # Jacket is optional

    for top, pant, shoe, jacket in product(tops, pants, shoes, jackets):
        colors = [top, pant, shoe] + ([jacket] if jacket else [])
        score = _score_outfit(*colors)
        if score > MIN_ACCEPTABLE_SCORE:
            outfits.append((top, pant, shoe, jacket, score))

    # Sort outfits by score
    outfits.sort(key=lambda x: x[3], reverse=True)
    return outfits

def suggest_outfit_for_item(user_input, wardrobe):
    if len(user_input) != 1:
        print("Please provide exactly one clothing item and its color.")
        return []

    input_type, input_color = next(iter(user_input.items()))
    valid_types = {"tops", "pants", "shoes", "jackets"}
    
    if input_type not in valid_types:
        print(f"Invalid clothing type: {input_type}. Must be one of {valid_types}.")
        return []

    wardrobe_items = {t: wardrobe.get(t, []) for t in valid_types}

    # Only use jackets if the user has any
    has_jackets = bool(wardrobe_items["jackets"])
    jacket_options = wardrobe_items["jackets"] if has_jackets else [None]


    suggestions = []

    # Define how to compute score
    def build_and_score(top, pant, shoe, jacket):
        score = _score_outfit(top, pant, shoe, jacket)
        return (top, pant, shoe, jacket, score)

    # Logic based on input_type
    if input_type == "tops":
        for pant in wardrobe_items["pants"]:
            for shoe in wardrobe_items["shoes"]:
                for jacket in jacket_options:
                    suggestions.append(build_and_score(input_color, pant, shoe, jacket))
    elif input_type == "pants":
        for top in wardrobe_items["tops"]:
            for shoe in wardrobe_items["shoes"]:
                for jacket in jacket_options:
                    suggestions.append(build_and_score(top, input_color, shoe, jacket))
    elif input_type == "shoes":
        for top in wardrobe_items["tops"]:
            for pant in wardrobe_items["pants"]:
                for jacket in jacket_options:
                    suggestions.append(build_and_score(top, pant, input_color, jacket))
    elif input_type == "jackets":
        for top in wardrobe_items["tops"]:
            for pant in wardrobe_items["pants"]:
                for shoe in wardrobe_items["shoes"]:
                    suggestions.append(build_and_score(top, pant, shoe, input_color))
    
    # Filter and sort
    suggestions = [s for s in suggestions]
    suggestions.sort(key=lambda x: x[3], reverse=True)
    
    return suggestions

def prompt_user_for_clothing_types(wardrobe):
    print("Your Wardrobe contains the following categories:")
    for clothing_type in wardrobe.keys():
        print(f"- {clothing_type.capitalize()} ({len(wardrobe[clothing_type])} items)")
        
    chosen = input("Ener clothing categories to use (comma separated): ").strip().lower()
    selected_types = [t.strip() for t in chosen.split(',') if t.strip() in wardrobe and wardrobe[t.strip()]]
    
    if not selected_types:
        print('No valid selection made. Please try again.')
        return prompt_user_for_clothing_types(wardrobe)
    
    return selected_types

def generate_outfits_based_on_selection(wardrobe, selected_types):
    clothing_items = [wardrobe[ctype] for ctype in selected_types]
    combinations = product(*clothing_items)
    
    outfits = []
    for combo in combinations:
        score = _score_outfit(*combo)
        if score >= MIN_ACCEPTABLE_SCORE:
            outfits.append((combo, score))
    
    outfits.sort(key=lambda x: x[1], reverse=True)
    print(f"---------You have {len(outfits)} good outfits---------")
    for combo, score in outfits:
        desc = [f"{ctype.capitalize()}: {_closest_color_name(c)}" for ctype, c in zip(selected_types, combo)]
        print(" | ".join(desc) + f" | Score: {round(score, 2)}")


if __name__ == '__main__':
    # Example inputs
    user_input = {
            "pants": (0, 0, 0)
        }
    
    wardrobe = {
        'jackets': [
            (0, 0, 0),
            (245, 245, 220)
        ],
        'tops': [
            (173, 216, 230), # Light Blue
            (128, 128, 128), # Gray
            (255, 0, 0), # Red
            (144, 238, 144), # Light Green
            (255, 160, 122), # Salmon
            (210, 180, 140), # Tan
            (0, 0, 0), # Black
            (255, 255, 255), # White
            (70, 130, 180), # Steel Blue
        ],
        'pants': [
            (0, 0, 128), # Navy
            (128, 128, 128), # Gray
            (255, 255, 255), # White
            (0, 0, 0) # Black
        ],
        'shoes': [
            (0, 0, 0), # Black
            (255, 255, 255) # White
        ]
    }
    
    selected = prompt_user_for_clothing_types(wardrobe)
    generate_outfits_based_on_selection(wardrobe, selected)
    
    # generate_and_print_outfits(wardrobe)
    # suggest_outfit_for_item(user_input, wardrobe)
    
