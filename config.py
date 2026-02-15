from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"
TOKENIZE_DIR = DATA_DIR / "tokenize"

PROFESSION_KEYWORDS = {
    "programmer": [
        "keyboard", "ketik", "ngetik", "tuts", "travel", "pencet",
        "ram", "memory", "memori", "multitasking", "buka banyak", "chrome",
        "layar", "screen", "monitor", "mata", "jernih", "tajam",
        "cepat", "kencang", "kenceng", "ngebut", "sat set", "lancar",
        "ssd", "booting", "nyala", "loading",
        "coding", "koding", "code", "program", "docker", "virtual", "wsl", "linux",
        "panas", "adem", "dingin", "fan", "kipas",
        "kerja", "work", "kantor", "tugas"
    ],
    "designer": [
        "warna", "color", "srgb", "akurat", "gonjreng", "pucat",
        "layar", "screen", "panel", "ips", "oled", "resolusi", "pixel",
        "render", "rendering", "export", "gpu", "vga", "grafis",
        "adobe", "photoshop", "illustrator", "premiere", "corel", "canva",
        "berat", "ringan", "bawa", "tas",
        "baterai", "awet", "tahan lama" 
    ],
    "student": [
        "baterai", "awet", "tahan", "cas", "charge",
        "ringan", "enteng", "tipis", "bawa",
        "kamera", "cam", "webcam", "zoom", "meet", "gmeet", "teams",
        "murah", "harga", "budget", "kantong", "worth",
        "ngetik", "tugas", "skripsi", "makalah", "word", "excel", "office",
        "speaker", "suara", "mic"
    ],
    "gamer": [
        "fps", "frame", "rata kanan", "smooth", "patah", "drop",
        "panas", "overheat", "hangat", "kipas", "berisik", "cooling", "adem",
        "vga", "gpu", "rtx", "gtx", "radeon", "nvidia",
        "layar", "hz", "hertz", "refresh", "ms",
        "game", "gaming", "main", "valorant", "dota", "genshin", "pubg"
    ],
}