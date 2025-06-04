import colorsys
import webcolors
from itertools import product, combinations
from collections import Counter
import base64
from io import BytesIO
from PIL import Image

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

def generate_color_box_base64(rgb, size=(200, 200)):
    img = Image.new('RGB', size, rgb)
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    base64_img = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{base64_img}"

def get_dominant_color(image, resize_to=(100, 100)):
    small_img = image.resize(resize_to)
    pixels = list(small_img.getdata())
    color_counts = Counter(pixels)
    return color_counts.most_common(1)[0][0]

# Generate combinations and print
def generate_outfit_suggestions(wardrobe):
    """
    wardrobe: {
      'tops':    [ { 'rgb':(...), 'image':... }, … ],
      'pants':   [ { … }, … ],
      'shoes':   [ { … }, … ],
      'jackets': [ { … }, … ]    # may be empty
    }
    Returns: [
      {
        'top':    { 'rgb':…, 'image':… },
        'pants':  { 'rgb':…, 'image':… },
        'shoes':  { 'rgb':…, 'image':… },
        'jacket': { 'rgb':…, 'image':… } | None,
        'score':  float
      },
      …
    ]
    """
    jackets = wardrobe.get("jackets", [])
    
    outfits = []

    def build_and_append(top_item, pant_item, shoe_item, jacket_item):
        # pull out the rgb tuples for scoring
        colors = [top_item['rgb'], pant_item['rgb'], shoe_item['rgb']]
        if jacket_item:
            colors.append(jacket_item['rgb'])
        score = _score_outfit(*colors)
        if score > MIN_ACCEPTABLE_SCORE:
            outfits.append({
                'top':    top_item,
                'pants':  pant_item,
                'shoes':  shoe_item,
                'jacket': jacket_item,
                'score':  score
            })

    if jackets:
        # with jacket
        for top_it, pant_it, shoe_it, jacket_it in product(wardrobe['tops'], wardrobe['pants'], wardrobe['shoes'], wardrobe['jackets']):
            build_and_append(top_it, pant_it, shoe_it, jacket_it)
        # without jacket
        for top_it, pant_it, shoe_it in product(wardrobe['tops'], wardrobe['pants'], wardrobe['shoes']):
            build_and_append(top_it, pant_it, shoe_it, None)
    else:
        # only without jacket
        for top_it, pant_it, shoe_it in product(wardrobe['tops'], wardrobe['pants'], wardrobe['shoes']):
            build_and_append(top_it, pant_it, shoe_it, None)

    # sort by score descending
    outfits.sort(key=lambda o: o['score'], reverse=True)
    return outfits

def suggest_outfit_for_item(user_input, wardrobe):
    """
    user_input: dict like {
                            'id': item_id,
                            'type': item_type,
                            'rgb': item_rgb,
                            'image': item_image
                        }
    wardrobe:   dict with keys 'tops', 'pants', etc.
                and values like: [ { 'rgb':…, 'image':… }, … ]
    returns: list of dicts like:
        {
            'top':    { … },
            'pants':  { … },
            'shoes':  { … },
            'jacket': { … } or None,
            'score':  float
        }
    """
    
    valid_types = {"tops", "pants", "shoes", "jackets"}

    wardrobe_items = {t: wardrobe.get(t, []) for t in valid_types}
    has_jackets = bool(wardrobe_items["jackets"])
    jacket_options = wardrobe_items["jackets"]
    jacket_options_with_none = jacket_options + [None] if has_jackets else [None]

    suggestions = []

    def build_outfit(top, pant, shoe, jacket):
        colors = [top['rgb'], pant['rgb'], shoe['rgb']]
        if jacket:
            colors.append(jacket['rgb'])
        score = _score_outfit(*colors)
        if score > MIN_ACCEPTABLE_SCORE:
            suggestions.append({
                'top': top,
                'pants': pant,
                'shoes': shoe,
                'jacket': jacket,
                'score': score
            })

    if user_input['type'] == "tops":
        for pant in wardrobe_items["pants"]:
            for shoe in wardrobe_items["shoes"]:
                for jacket in jacket_options_with_none:
                    top = {'id': user_input['id'], 'rgb': user_input['rgb'], 'image': user_input['image']}
                    build_outfit(top, pant, shoe, jacket)
    elif user_input['type'] == "pants":
        for top in wardrobe_items["tops"]:
            for shoe in wardrobe_items["shoes"]:
                for jacket in jacket_options_with_none:
                    pant = {'id': user_input['id'], 'rgb': user_input['rgb'], 'image': user_input['image']}
                    build_outfit(top, pant, shoe, jacket)
    elif user_input['type'] == "shoes":
        for top in wardrobe_items["tops"]:
            for pant in wardrobe_items["pants"]:
                for jacket in jacket_options_with_none:
                    shoe = {'id': user_input['id'], 'rgb': user_input['rgb'], 'image': user_input['image']}
                    build_outfit(top, pant, shoe, jacket)
    elif user_input['type'] == "jackets":
        for top in wardrobe_items["tops"]:
            for pant in wardrobe_items["pants"]:
                for shoe in wardrobe_items["shoes"]:
                    jacket = {'id': user_input['id'], 'rgb': user_input['rgb'], 'image': user_input['image']}
                    build_outfit(top, pant, shoe, jacket)

    suggestions.sort(key=lambda o: o['score'], reverse=True)
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

def suggestions_for_item(user_input):
    """
    Suggests matching color combinations for a given clothing item.
    Not based on wardrobe — provides guidance for potential future purchases.

    :param user_input: dict — 'type': one of "tops", "pants", "shoes", or "jackets", 'rgb': (R, G, B) values of the chosen item
    :return: list of suggestions, each as a dict of id, item-type to RGB values, image
    """

    user_input['type'], user_input['rgb'] = next(iter(user_input.items()))
    
    valid_types = {"tops", "pants", "shoes", "jackets"}
    if user_input['type'] not in valid_types:
        raise ValueError(f"Invalid user_input['type']: {user_input['type']}. Must be one of {valid_types}.")

    # These are example classic wardrobe-friendly colors per category
    sample_colors = {
        'tops': [
            (255, 255, 255),  # white
            (0, 0, 0),        # black
            (210, 180, 140),  # tan
            (144, 238, 144),  # light green
            (173, 216, 230),  # light blue
        ],
        'pants': [
            (255, 255, 255),  # white
            (0, 0, 0),        # black
            (245, 245, 220),  # beige
            (128, 128, 128),  # gray
            (0, 0, 128),      # navy
        ],
        'shoes': [
            (0, 0, 0),        # black
            (255, 255, 255),  # white
            (160, 82, 45),    # brown
        ],
        'jackets': [
            (0, 0, 0),        # black
            (255, 255, 255),  # white
            (128, 128, 128),  # gray
            (245, 245, 220),  # beige
        ]
    }

    def generate_theory_colors(base_rgb):
        h, s, v = ___rgb_to_hsv(base_rgb)
        dynamic = set()

        # Complementary
        dynamic.add(tuple(map(int, __get_complementary_color(base_rgb))))

        # Analogous ±30°
        for offset in (-30, 30):
            h_rot = (h + offset / 360.0) % 1.0
            dynamic.add(tuple(map(int, ___hsv_to_rgb((h_rot, s, v)))))

        # Neutrals
        dynamic.update([
            (255, 255, 255), (0, 0, 0),
            (128, 128, 128), (245, 245, 220), (160, 82, 45)
        ])

        return list(dynamic)

    all_types = ['tops', 'pants', 'shoes', 'jackets']
    palette = {}
    
    for t in all_types:
        if t == user_input['type']:
            continue
        if t == 'jackets':
            palette[t] = sample_colors[t]
        else:
            palette[t] = list(set(sample_colors[t] + generate_theory_colors(user_input['rgb'])))

    jacket_options = palette['jackets'] + [None] if user_input['type'] != 'jackets' else [user_input['rgb'], None]
    tops_options = palette['tops'] if user_input['type'] != 'tops' else [user_input['rgb']]
    pants_options = palette['pants'] if user_input['type'] != 'pants' else [user_input['rgb']]
    shoes_options = palette['shoes'] if user_input['type'] != 'shoes' else [user_input['rgb']]

    suggestions = []
    for top, pant, shoe, jacket in product(tops_options, pants_options, shoes_options, jacket_options):
        parts = {
            'top': top,
            'pants': pant,
            'shoes': shoe,
            'jacket': jacket
        }

        colors = [c for c in [top, pant, shoe, jacket] if c is not None]
        score = _score_outfit(*colors)
        if score >= 3.0:
            suggestions.append({
                'top': {'rgb': parts['top'], 'image': generate_color_box_base64(parts['top'])},
                'pants': {'rgb': parts['pants'], 'image': generate_color_box_base64(parts['pants'])},
                'shoes': {'rgb': parts['shoes'], 'image': generate_color_box_base64(parts['shoes'])},
                'jacket': {'rgb': parts['jacket'], 'image': generate_color_box_base64(parts['jacket'])} if parts['jacket'] else None,
                'score': round(score, 2)
            })

    # Sort suggestions by score descending
    suggestions.sort(key=lambda x: x['score'], reverse=True)
    
    return suggestions
    
if __name__ == '__main__':
    # Example inputs
    user_input = {
            "tops": (0, 0, 0)
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
    
    suggestions = suggestions_for_item(user_input)
    print(suggestions)
    # selected = prompt_user_for_clothing_types(wardrobe)
    # generate_outfits_based_on_selection(wardrobe, selected)
    # generate_and_print_outfits(wardrobe)
    # suggest_outfit_for_item(user_input, wardrobe)