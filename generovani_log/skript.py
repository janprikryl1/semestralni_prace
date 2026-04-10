import os
import io
import numpy as np
import cv2
from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps
from io import BytesIO
import cairosvg
import math
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from functools import lru_cache
import uvicorn
from dotenv import load_dotenv
import mysql.connector
import requests
from contextlib import asynccontextmanager

# --- KONFIGURÁCIA ---
COIN_BASE_URL = "https://api.serious.broker/cryptocurrency_list/images/"
load_dotenv()
db_password = os.getenv("DB_PASSWORD")

# Globálne premenné pre šablóny
BASE_GOLD = None
BASE_SILVER = None

def get_db_connection():
    return mysql.connector.connect(
        host='m9193.svethostingu-multi.cz',
        port=30112,
        user='serious_broker',
        password=db_password,
        database='serious_broker'
    )

def load_templates():
    global BASE_GOLD, BASE_SILVER
    try:
        gold = Image.open("base_gold.png").convert("RGBA")
        silver = Image.open("base_silver.png").convert("RGBA")
        
        # Orezanie na štvorec (stred)
        w, h = gold.size
        size = min(w, h)
        left, top = (w - size) // 2, (h - size) // 2
        BASE_GOLD = gold.crop((left, top, left + size, top + size))
        BASE_SILVER = silver.crop((left, top, left + size, top + size))
        print("✅ Šablóny úspešne načítané.")
    except Exception as e:
        print(f"❌ Chyba pri načítaní šablón: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_templates()
    yield

app = FastAPI(lifespan=lifespan)

# Povolenie CORS pre React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- JADRO TVOJEJ LOGIKY (PRESKOPÍROVANÉ Z LOKÁLNEHO SKRIPTU) ---

def apply_perspective(logo, yaw_deg=20, pitch_deg=15, roll_deg=-12):
    logo_np = np.array(logo)
    h, w = logo_np.shape[:2]
    src = np.float32([[0,0], [w,0], [w,h], [0,h]])
    yaw = math.sin(math.radians(yaw_deg)) * w * 0.4
    pitch = math.sin(math.radians(pitch_deg)) * h * 0.4
    dst = np.float32([
        [yaw, pitch],
        [w - yaw, pitch],
        [w - yaw*0.3, h],
        [yaw*0.3, h]
    ])
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(logo_np, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
    center = (w // 2, h // 2)
    R = cv2.getRotationMatrix2D(center, roll_deg, 1.0)
    warped = cv2.warpAffine(warped, R, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))
    return Image.fromarray(warped)

def apply_3d_emboss_final(background, logo, position, depth=25):
    x, y = position
    img = background.copy()
    enhancer = ImageEnhance.Brightness(logo)
    side_logo = enhancer.enhance(0.25)
    for i in range(depth, 0, -1):
        img.paste(side_logo, (x + i, y + i), side_logo)
    alpha = logo.split()[-1]
    shadow = alpha.filter(ImageFilter.GaussianBlur(10))
    shadow_layer = Image.new("RGBA", background.size, (0,0,0,0))
    shadow_layer.paste((0,0,0,120), (x+depth+5, y+depth+5), mask=shadow)
    img = Image.alpha_composite(img, shadow_layer)
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
    
    edge_sample_mask = (dist > max_radius * 0.85) & (dist < max_radius * 0.95) & (alpha > 10)
    if not np.any(edge_sample_mask):
        return logo, False, False

    unique, counts = np.unique(rgb[edge_sample_mask].reshape(-1, 3), axis=0, return_counts=True)
    dominant_bg = unique[np.argmax(counts)]

    is_circular = True
    for i in range(12):
        angle_low  = -np.pi + (2 * np.pi / 12) * i
        angle_high = -np.pi + (2 * np.pi / 12) * (i + 1)
        sector_mask = (angles >= angle_low) & (angles < angle_high) & (dist > max_radius * 0.8) & (dist < max_radius * 0.9)
        if np.any(sector_mask):
            diffs = np.linalg.norm(rgb[sector_mask] - dominant_bg, axis=1)
            if np.mean(diffs < tolerance) < 0.3:
                is_circular = False
                break
        else:
            is_circular = False
            break

    if not is_circular:
        return logo, False, False

    diff = np.linalg.norm(rgb - dominant_bg, axis=2)
    color_mask = diff < tolerance
    is_white = (rgb[:,:,0] > 190) & (rgb[:,:,1] > 190) & (rgb[:,:,2] > 190)
    probe_zone = dist < (max_radius * 0.82)
    white_in_safe = np.sum(is_white & probe_zone)
    total_in_safe = np.sum(probe_zone & (alpha > 0))
    white_ratio = white_in_safe / total_in_safe if total_in_safe > 0 else 0
    is_round = white_ratio > 0.10

    safe_zone = dist < (max_radius * 0.82) if is_round else dist < (max_radius * 0.98)
    is_bg = (color_mask & (~safe_zone)) | (dist > max_radius * 0.95 if is_round else dist > max_radius * 0.99)

    new_alpha = np.copy(alpha)
    new_alpha[is_bg] = 0
    result_rgb = np.copy(rgb)

    if is_round:
        mask_to_recolor = is_white & safe_zone
        mask_to_delete_in_safe = color_mask & safe_zone
        remaining_colored = (~color_mask) & safe_zone & (alpha > 0) & (~is_white)
        has_colored_symbol = np.sum(remaining_colored) > (np.sum(safe_zone) * 0.05)
        
        if not has_colored_symbol:
            result_rgb[mask_to_recolor] = dominant_bg
        new_alpha[mask_to_delete_in_safe] = 0

    result = np.zeros_like(img)
    result[:, :, :3] = result_rgb
    result[:, :, 3] = new_alpha
    return Image.fromarray(result, "RGBA"), True, is_round

def get_dominant_color(logo):
    img = np.array(logo)
    rgb, alpha = img[:, :, :3], img[:, :, 3]
    h, w = rgb.shape[:2]
    visible = alpha > 10
    Y, X = np.ogrid[:h, :w]
    dist = np.sqrt((X-w/2)**2 + (Y-h/2)**2)
    mask = visible & (dist < min(w,h)*0.35)
    pixels = rgb[mask] if np.any(mask) else rgb[visible]
    if len(pixels) == 0: return (200, 200, 200)
    unique, counts = np.unique(pixels.reshape(-1,3), axis=0, return_counts=True)
    return tuple(unique[np.argmax(counts)])

def replace_base_color(base_img, new_color, target=(76,255,0), tolerance=155):
    img = np.array(base_img.convert("RGBA"))
    rgb, alpha = img[:,:,:3], img[:,:,3]
    diff = np.linalg.norm(rgb - np.array(target), axis=2)
    mask = diff < tolerance
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    new_hsv = cv2.cvtColor(np.uint8([[new_color]]), cv2.COLOR_RGB2HSV)[0][0]
    hsv[mask,0] = new_hsv[0]
    hsv[mask,1] = new_hsv[1]
    rgb_new = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
    img[:,:,:3] = rgb_new
    img[:,:,3] = alpha
    return Image.fromarray(img, "RGBA")

def is_warm_color(rgb):
    hsv = cv2.cvtColor(np.uint8([[rgb]]), cv2.COLOR_RGB2HSV)
    hue = hsv[0][0][0]
    return hue < 45 or hue > 170

# --- DB A API LOGIKA ---

def fetch_image_from_db(crypto_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Pridali sme stĺpec symbol, aby sme vedeli určiť farbu mince aj bez loga
        cur.execute("SELECT photo, symbol FROM coinmarketcap_coin WHERE id = %s", (crypto_id,))
        data = cur.fetchone()
        print(data)
        cur.close()
        conn.close()
        return data if data else (None, None)
    except Exception as e:
        print(f"❌ DB Error: {e}")
        return None, None

@app.get("/coin/{crypto_id}")
async def get_coin(crypto_id: int):
    # 1. Získanie dát z DB
    file_name, symbol = fetch_image_from_db(crypto_id)
    
    # Ak minca vôbec neexistuje v DB, vrátime 404
    if symbol is None and file_name is None:
        raise HTTPException(status_code=404, detail="Minca nenájdená v DB")

    try:
        # Pripravíme si základnú mincu (predvolene zlatá)
        # Ak nie je logo, môžeme farbu určiť podľa symbolu alebo nechať zlatú
        final_coin = BASE_GOLD.copy() 

        # 2. Ak existuje názov súboru, skúsime spracovať logo
        if file_name:
            full_url = f"{COIN_BASE_URL}{file_name}"
            response = requests.get(full_url, timeout=10)
            
            if response.status_code == 200:
                image_data = response.content
                if file_name.lower().endswith('.svg'):
                    image_data = cairosvg.svg2png(bytestring=image_data, output_width=800, output_height=800)
                
                logo = Image.open(io.BytesIO(image_data)).convert("RGBA")
                
                # Spracovanie loga (tvoja logika)
                logo, has_circle, is_round = remove_circle_background_and_recolor(logo)
                logo = apply_perspective(logo)
                
                dominant_color = get_dominant_color(logo)
                template = BASE_GOLD.copy() if is_warm_color(dominant_color) else BASE_SILVER.copy()
                base_colored = replace_base_color(template, dominant_color)

                # Veľkosť a pozícia
                tw = base_colored.width
                if has_circle and not is_round:
                    logo_size = int(tw * 0.50)
                elif has_circle and is_round:
                    logo_size = int(tw * 0.70)
                else:
                    logo_size = int(tw * 0.45)
                    
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                cx, cy = 490, 445
                x, y = cx - logo_size // 2, cy - logo_size // 2
                
                # Výsledok s logom
                final_coin = apply_3d_emboss_final(base_colored, logo, (x, y))
            else:
                print(f"⚠️ Logo {file_name} sa nepodarilo stiahnuť, vraciam prázdnu mincu.")
        else:
            print(f"ℹ️ Minca ID {crypto_id} nemá v DB logo, generujem prázdnu zlatú mincu.")

        # 3. Odoslanie (či už s logom alebo bez neho)
        buf = io.BytesIO()
        final_coin.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")

    except Exception as e:
        print(f"❌ Error processing {crypto_id}: {e}")
        # V prípade kritickej chyby pri spracovaní loga vrátime aspoň čistú zlatú mincu
        buf = io.BytesIO()
        BASE_GOLD.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")
    

# ... tvůj stávající kód (importy, funkce na zpracování obrazu atd.) ...

# URL tvého nového PHP endpointu
UPLOAD_ENDPOINT_URL = "https://api.serious.broker/cryptocurrency_list/public_upload_stylized.php"

def process_and_upload_all():
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        # Vybereme jen ty, které mají fotku a ještě nemají stylizovaný obrázek (volitelné)
        cur.execute("SELECT id, name, symbol, photo FROM coinmarketcap_coin WHERE photo IS NOT NULL AND photo != ''")
        coins = cur.fetchall()
        cur.close()
        conn.close()

        print(f"🚀 Začínám zpracování {len(coins)} mincí...")

        for coin in coins:
            crypto_id = coin['id']
            print(f"Processing ID {crypto_id} ({coin['symbol']})...")

            try:
                # Zavoláme tvou existující logiku pro generování (vytáhneme si kód z get_coin)
                # Pro zjednodušení si v Pythonu vytvoř funkci: generate_coin_image(crypto_id)
                img_data = generate_coin_image_logic(coin) # Tato funkce vrátí BytesIO nebo bytes
                
                if img_data:
                    # Odeslání na PHP endpoint
                    files = {
                        'stylized_image': (f"coin_{crypto_id}.png", img_data, 'image/png')
                    }
                    data = {
                        'id': crypto_id,
                        'name': coin['name'],
                        'symbol': coin['symbol']
                    }
                    
                    response = requests.post(UPLOAD_ENDPOINT_URL, files=files, data=data)
                    
                    if response.status_code == 200:
                        print(f"✅ ID {crypto_id} úspěšně nahráno.")
                    else:
                        print(f"❌ Chyba při nahrávání ID {crypto_id}: {response.text}")

            except Exception as e:
                print(f"⚠️ Selhalo zpracování mince {crypto_id}: {e}")

    except Exception as e:
        print(f"❌ Chyba databáze: {e}")

def generate_coin_image_logic(coin):
    """
    Vezme data o minci a vygeneruje obrázek v paměti.
    Vrací bytes (obsah PNG souboru).
    """
    crypto_id = coin['id']
    file_name = coin['photo']
    symbol = coin['symbol']

    try:
        # Základní šablona
        final_coin = BASE_GOLD.copy() 

        if file_name:
            full_url = f"{COIN_BASE_URL}{file_name}"
            response = requests.get(full_url, timeout=10)
            
            if response.status_code == 200:
                image_data = response.content
                if file_name.lower().endswith('.svg'):
                    image_data = cairosvg.svg2png(bytestring=image_data, output_width=800, output_height=800)
                
                logo = Image.open(io.BytesIO(image_data)).convert("RGBA")
                
                # Tvoje grafická logika
                logo, has_circle, is_round = remove_circle_background_and_recolor(logo)
                logo = apply_perspective(logo)
                
                dominant_color = get_dominant_color(logo)
                template = BASE_GOLD.copy() if is_warm_color(dominant_color) else BASE_SILVER.copy()
                base_colored = replace_base_color(template, dominant_color)

                tw = base_colored.width
                if has_circle and not is_round:
                    logo_size = int(tw * 0.50)
                elif has_circle and is_round:
                    logo_size = int(tw * 0.70)
                else:
                    logo_size = int(tw * 0.45)
                    
                logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                cx, cy = 490, 445
                x, y = cx - logo_size // 2, cy - logo_size // 2
                
                final_coin = apply_3d_emboss_final(base_colored, logo, (x, y))
            else:
                print(f"⚠️ Logo {file_name} nelze stáhnout.")
        
        # Uložíme do bufferu a vrátíme jen čistá data (bytes)
        buf = io.BytesIO()
        final_coin.save(buf, format="PNG")
        return buf.getvalue()

    except Exception as e:
        print(f"❌ Chyba generování u ID {crypto_id}: {e}")
        # V nouzi vygenerujeme aspoň čistou zlatou minci
        buf = io.BytesIO()
        BASE_GOLD.save(buf, format="PNG")
        return buf.getvalue()

def process_and_upload_all():
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        # Načteme ID, jméno, symbol i PHOTO (potřebujeme ho pro generování)
        cur.execute("SELECT id, name, symbol, photo FROM coinmarketcap_coin WHERE photo IS NOT NULL AND photo != ''")
        coins = cur.fetchall()
        cur.close()
        conn.close()

        print(f"🚀 Start: {len(coins)} mincí k nahrání...")

        for coin in coins:
            crypto_id = coin['id']
            try:
                # 1. Vygenerujeme obrázek v paměti
                img_bytes = generate_coin_image_logic(coin)
                
                if img_bytes:
                    # 2. Příprava dat pro POST (musí odpovídat tvému PHP souboru)
                    files = {
                        'stylized_image': (f"coin_{crypto_id}.png", img_bytes, 'image/png')
                    }
                    payload = {
                        'id': crypto_id,
                        'name': coin['name'],
                        'symbol': coin['symbol']
                    }
                    
                    # 3. Odeslání na PHP endpoint
                    resp = requests.post(UPLOAD_ENDPOINT_URL, files=files, data=payload, timeout=20)
                    
                    if resp.status_code == 200:
                        print(f"✅ {coin['symbol']} (ID: {crypto_id}) uloženo.")
                    else:
                        print(f"❌ {coin['symbol']} (ID: {crypto_id}) PHP error: {resp.status_code} - {resp.text}")

            except Exception as e:
                print(f"⚠️ ID {crypto_id} selhalo: {e}")

    except Exception as e:
        print(f"❌ DB Error: {e}")
    
@app.get("/admin/generate-all")
async def trigger_generate_all():
    # Spustí proces na pozadí, aby neblokoval API
    import threading
    threading.Thread(target=process_and_upload_all).start()
    return {"message": "Generování všech mincí bylo spuštěno na pozadí."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)