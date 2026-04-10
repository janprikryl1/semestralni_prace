import os
import numpy as np
import cv2
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps
from io import BytesIO
import cairosvg
import math
import time

start_time = time.time()

# --- KONFIGURACE ---
#TEMPLATE_PATH = "base2.png"
LOGO_FOLDER = "logos"
OUTPUT_FOLDER = "coins"
# Barva pro světlé a tmavé části ražby
GOLD_LIGHT = (212, 175, 55)
GOLD_DARK = (100, 70, 20)
GOLD_COLOR = (170, 141, 46)

def colorize_logo(logo, target_color=GOLD_COLOR):
    """
    Chytřejší barvení: Obarví pouze viditelné části loga (symbol),
    nikoliv celé pozadí.
    """
    # Převedeme na stupně šedi pro detekci symbolu
    grayscale = logo.convert("L")

    # Vytvoříme masku: chceme obarvit jen to, co není bílé pozadí (u log s bílým bg)
    # nebo to, co je dostatečně výrazné.
    mask = Image.eval(grayscale, lambda x: 255 if x < 240 else 0)

    # Zkombinujeme s původní alfou loga
    final_mask = ImageChops.multiply(mask, logo.split()[-1])

    # Vytvoříme barevnou vrstvu a spojíme ji přes novou masku
    color_layer = Image.new("RGB", logo.size, target_color)
    return Image.merge("RGBA", (*color_layer.split(), final_mask))

def apply_perspective(logo, yaw_deg=20, pitch_deg=15, roll_deg=-12):
    logo_np = np.array(logo)
    h, w = logo_np.shape[:2]

    src = np.float32([
        [0,0],
        [w,0],
        [w,h],
        [0,h]
    ])

    yaw = math.sin(math.radians(yaw_deg)) * w * 0.4
    pitch = math.sin(math.radians(pitch_deg)) * h * 0.4

    dst = np.float32([
        [yaw, pitch],           # TL
        [w - yaw, pitch],       # TR
        [w - yaw*0.3, h],       # BR
        [yaw*0.3, h]            # BL
    ])

    M = cv2.getPerspectiveTransform(src, dst)

    warped = cv2.warpPerspective(
        logo_np,
        M,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0,0,0,0)
    )

    # --- ROLL ROTACE ---
    center = (w // 2, h // 2)
    R = cv2.getRotationMatrix2D(center, roll_deg, 1.0)

    warped = cv2.warpAffine(
        warped,
        R,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0,0,0,0)
    )

    return Image.fromarray(warped)

def apply_3d_emboss_final(background, logo, position,depth=25):
    # """
    # Aplikuje logo s vnitřním stínem a jemným vnějším leskem na hraně.
    # """
    # x, y = position
    # alpha = logo.split()[-1]

    # # Vytvoření stínu pro hloubku (zapuštění do černé plochy)
    # shadow = alpha.filter(ImageFilter.GaussianBlur(radius=5))
    # shadow_layer = Image.new("RGBA", background.size, (0, 0, 0, 0))
    # # Posun o 2px pro 3D efekt
    # shadow_layer.paste((0, 0, 0, 200), (x + 2, y + 2), mask=shadow)

    # # Složení
    # img = Image.alpha_composite(background, shadow_layer)
    # img.paste(logo, (x, y), logo)

    # return img
    x, y = position
    img = background.copy()

    # ztmavená verze loga pro boky
    enhancer = ImageEnhance.Brightness(logo)
    side_logo = enhancer.enhance(0.25)  # tmavší bok

    # extrusion vrstvy
    for i in range(depth, 0, -1):
        img.paste(side_logo, (x + i, y + i), side_logo)

    # stín
    alpha = logo.split()[-1]
    shadow = alpha.filter(ImageFilter.GaussianBlur(10))
    shadow_layer = Image.new("RGBA", background.size, (0,0,0,0))
    shadow_layer.paste((0,0,0,120), (x+depth+5, y+depth+5), mask=shadow)

    img = Image.alpha_composite(img, shadow_layer)

    # horní logo
    img.paste(logo, (x, y), logo)

    return img

def remove_circle_background_and_recolor(logo, tolerance=45):
    img = np.array(logo.convert("RGBA"))
    h, w = img.shape[:2]
    rgb = img[:, :, :3]
    alpha = img[:, :, 3]

    Y, X = np.ogrid[:h, :w]
    cx, cy = w/2, h/2
    dist = np.sqrt((X-cx)**2 + (Y-cy)**2)
    max_radius = min(w, h) / 2

    angles = np.arctan2(Y - cy, X - cx)
    is_circular = True

    edge_sample_mask = (dist > max_radius * 0.85) & (dist < max_radius * 0.95) & (alpha > 10)
    if not np.any(edge_sample_mask):
        return logo, False, False  # ← opraveno

    unique, counts = np.unique(rgb[edge_sample_mask].reshape(-1, 3), axis=0, return_counts=True)
    dominant_bg = unique[np.argmax(counts)]

    for i in range(12):
        angle_low  = -np.pi + (2 * np.pi / 12) * i
        angle_high = -np.pi + (2 * np.pi / 12) * (i + 1)
        sector_mask = (angles >= angle_low) & (angles < angle_high) & \
                      (dist > max_radius * 0.8) & (dist < max_radius * 0.9)
        if np.any(sector_mask):
            diffs = np.linalg.norm(rgb[sector_mask] - dominant_bg, axis=1)
            if np.mean(diffs < tolerance) < 0.3:
                is_circular = False
                break
        else:
            is_circular = False
            break

    if not is_circular:
        print("Detekován jiný tvar → přeskakuji mazání pozadí.")
        return logo, False, False  # ← opraveno

    diff = np.linalg.norm(rgb - dominant_bg, axis=2)
    color_mask = diff < tolerance

    is_white = (rgb[:,:,0] > 190) & (rgb[:,:,1] > 190) & (rgb[:,:,2] > 190)
    probe_zone = dist < (max_radius * 0.82)
    white_in_safe = np.sum(is_white & probe_zone)
    total_in_safe = np.sum(probe_zone & (alpha > 0))
    white_ratio   = white_in_safe / total_in_safe if total_in_safe > 0 else 0
    is_round      = white_ratio > 0.10  # ← definuj tady

    if is_round:
        safe_zone = dist < (max_radius * 0.82)
    else:
        safe_zone = dist < (max_radius * 0.98)

    is_bg = color_mask & (~safe_zone)
    if is_round:
        is_bg |= (dist > max_radius * 0.95)
    else:
        is_bg |= (dist > max_radius * 0.99)

    new_alpha = np.copy(alpha)
    new_alpha[is_bg] = 0
    result_rgb = np.copy(rgb)

    if is_round:
      mask_to_recolor = is_white & safe_zone
      mask_to_delete_in_safe = color_mask & safe_zone
      
      # Zkontroluj jestli po smazání kruhu zůstane něco barevného
      remaining_colored = (~color_mask) & safe_zone & (alpha > 0) & (~is_white)
      has_colored_symbol = np.sum(remaining_colored) > (np.sum(safe_zone) * 0.05)
      
      if has_colored_symbol:
          # Barevný symbol (BONK) → nesmaž bílou, jen smaž kruh
          new_alpha[mask_to_delete_in_safe] = 0
          print(f"Barevný symbol s kruhem → zachovávám bílé detaily")
      else:
          # Čistě bílý symbol (BTC) → přebarvi
          result_rgb[mask_to_recolor] = dominant_bg
          new_alpha[mask_to_delete_in_safe] = 0
          print(f"Bílé logo → přebarvuji na {dominant_bg}")

    result = np.zeros_like(img)
    result[:, :, :3] = result_rgb
    result[:, :, 3] = new_alpha

    return Image.fromarray(result, "RGBA"), True, is_round

def get_dominant_color(logo):
    img = np.array(logo)
    rgb = img[:, :, :3]
    alpha = img[:, :, 3]

    h, w = rgb.shape[:2]

    # maska viditelných pixelů
    visible = alpha > 10

    # ignorujeme okraje (kde bývá kruh)
    Y, X = np.ogrid[:h, :w]
    cx, cy = w/2, h/2
    dist = np.sqrt((X-cx)**2 + (Y-cy)**2)

    center_mask = dist < min(w,h)*0.35

    mask = visible & center_mask

    pixels = rgb[mask]

    if len(pixels) == 0:
        pixels = rgb[visible]

    unique, counts = np.unique(pixels.reshape(-1,3), axis=0, return_counts=True)
    dominant = unique[np.argmax(counts)]

    return tuple(dominant)

def replace_base_color(base_img, new_color, target=(76,255,0), tolerance=155):
    img = np.array(base_img.convert("RGBA"))
    rgb = img[:,:,:3]
    alpha = img[:,:,3]

    diff = np.linalg.norm(rgb - np.array(target), axis=2)
    mask = diff < tolerance

    # Převedeme do HSV
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    new_hsv = cv2.cvtColor(np.uint8([[new_color]]), cv2.COLOR_RGB2HSV)[0][0]

    # Pouze změníme hue a sytost
    hsv[mask,0] = new_hsv[0]   # hue
    hsv[mask,1] = new_hsv[1]   # saturation

    # Převod zpět na RGB
    rgb_new = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
    img[:,:,:3] = rgb_new
    img[:,:,3] = alpha  # zachování alfakanálu

    return Image.fromarray(img, "RGBA")

def is_warm_color(rgb):
    rgb_np = np.uint8([[rgb]])
    hsv = cv2.cvtColor(rgb_np, cv2.COLOR_RGB2HSV)
    hue = hsv[0][0][0]

    if hue < 45 or hue > 170:
        return True   # teplá
    else:
        return False  # studená

def load_logo(path):
    if path.lower().endswith(".svg"):
        png_data = cairosvg.svg2png(url=path, output_width=800, output_height=800)
        return Image.open(BytesIO(png_data)).convert("RGBA")
    return Image.open(path).convert("RGBA")

# --- HLAVNÍ PROCES ---
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
base_template_gold = Image.open("base_gold.png").convert("RGBA")
base_template_silver = Image.open("base_silver.png").convert("RGBA")

# Oříznutí na čtverec
w, h = base_template_gold.size
size = min(w, h)
left, top = (w - size) // 2, (h - size) // 2
base_template_gold = base_template_gold.crop((left, top, left + size, top + size))
base_template_silver = base_template_silver.crop((left, top, left + size, top + size))

TW, TH = base_template_gold.size
CX, CY = 490, 445 # Střed mince

for file in os.listdir(LOGO_FOLDER):
    path = os.path.join(LOGO_FOLDER, file)
    if not os.path.isfile(path) or file.startswith('.'):
        continue

    print(f"Zpracovávám: {file}")

    # 1. Načtení a transformace na zlato (včetně Shiby!)
    logo = load_logo(path)
    #logo = colorize_logo(logo)
    logo, has_circle, is_round = remove_circle_background_and_recolor(logo)
    #has_circle = False
    # 2. Perspektiva
    logo = apply_perspective(logo)
    dominant_color = get_dominant_color(logo)
    if is_warm_color(dominant_color):
      base_colored = replace_base_color(base_template_gold.copy(), dominant_color)
    else:
      base_colored = replace_base_color(base_template_silver.copy(), dominant_color)

    # 3. Velikost
    if has_circle and not is_round:
        logo_size = int(TW * 0.50)   # mazalo se pozadí ale není kruh (Cronos)
    elif has_circle and is_round:
        logo_size = int(TW * 0.70)   # skutečný kruh (BTC, AVAX, Shiba)
    else:
        logo_size = int(TW * 0.45) 
    logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

    # 4. Pozice
    x = CX - logo_size // 2
    y = CY - logo_size // 2

    # 5. Finální kompozice s hloubkou
    img_final = apply_3d_emboss_final(base_colored.copy(), logo, (x, y))

    # Uložení
    name = os.path.splitext(file)[0] + ".png"
    img_final.save(os.path.join(OUTPUT_FOLDER, name))

end_time = time.time()
elapsed_time = end_time - start_time

print("Hotovo! Všechna loga jsou nyní sjednocena do stylu mince.")

print(f"Čas behu skriptu: {elapsed_time:.4f} sekúnd")
