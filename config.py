from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "robust_data"
MODEL_DIR = BASE_DIR / "models"
TOKENIZE_DIR = DATA_DIR / "tokenize"

ASPECT_KEYWORDS = {
    "performa": [
        "cepat", "kencang", "ngebut", "lancar", "mulus", "sat set", "gaming",
        "render", "editing", "multitasking", "ram", "ssd", "prosesor", "vga", 
        "gpu", "intel", "ryzen", "nvidia", "rtx", "lemot", "lag", "hang", 
        "lelet", "loading", "booting", "koding", "docker", "berat", "panas", 
        "overheat", "adem", "dingin", "kipas", "fan", "berisik"
    ],
    "layar": [
        "jernih", "tajam", "bening", "cerah", "bright", "gonjreng", "pucat", 
        "warna", "akurat", "srgb", "ntsc", "ips", "oled", "amoled", "layar", 
        "screen", "panel", "hz", "hertz", "refresh rate", "bezel", "tipis", 
        "resolusi", "fhd", "4k", "retina", "pixel", "dead pixel", "shadow", 
        "bocor", "backlight bleed", "silau", "matte", "glare"
    ],
    "baterai": [
        "awet", "tahan lama", "badak", "boros", "cepat habis", "drop", 
        "cas", "charge", "charger", "charging", "watt", "adapter", "kabel", 
        "type-c", "baterai", "battery", "mah", "tahan", "jam", "standby", 
        "soak", "panas saat cas"
    ],
    "harga": [
        "murah", "mahal", "worth it", "value for money", "terjangkau", 
        "ekonomis", "pricey", "kemahalan", "promo", "diskon", "flash sale", 
        "bonus", "hadiah", "freebie", "ongkir", "budget", "pelajar", 
        "kantong", "investasi", "padan", "sesuai harga"
    ],
}