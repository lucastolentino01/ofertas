"""Temas visuais. Escolha com a variável THEME (techbarato ou luluba)."""
import os

TEMAS = {
    "techbarato": {
        "marca": "TECH BARATO",
        "selo": "ACHADINHO DO DIA",
        "emoji": "🔥",
        "botao": "COMPRAR NA SHOPEE",
        "cta": "LINK NO TELEGRAM",
        "seta": "  →  ",
        # cores (R, G, B)
        "fundo": (18, 18, 20), "fundo_brilho": (50, 50, 56),
        "texto": (255, 255, 255), "texto_suave": (160, 160, 168),
        "destaque": (255, 106, 43), "sobre_destaque": (18, 18, 20),
        "cartao": (255, 255, 255),
        # fontes (arquivo, variação)
        "f_titulo": ("InterDisplay-Black.otf", None),
        "f_marca": ("InterDisplay-Black.otf", None),
        "f_bold": ("Inter-Bold.otf", None),
        "f_med": ("Inter-Medium.otf", None),
        # site
        "css": {"bg": "#f6f6f4", "card": "#fff", "txt": "#1b1b1b", "sub": "#6b6b6b",
                "acc": "#ee4d2d", "line": "#e6e4df", "dark_bg": "#121212", "dark_card": "#1d1d1d",
                "dark_txt": "#f1f1f1", "dark_sub": "#a3a3a3", "dark_line": "#2c2c2c"},
        "fonte_site": "system-ui,-apple-system,Segoe UI,Roboto,sans-serif",
        "google_fonts": "",
        "titulo_site": "font-weight:800",
    },
    "luluba": {
        "marca": "Luluba",
        "selo": "ACHADINHO LINDO",
        "emoji": "✨",
        "botao": "QUERO O MEU",
        "cta": "LINK NO CANAL",
        "seta": ": ",
        "fundo": (247, 239, 234), "fundo_brilho": (233, 207, 195),
        "texto": (43, 31, 34), "texto_suave": (138, 116, 120),
        "destaque": (194, 105, 122), "sobre_destaque": (255, 255, 255),
        "cartao": (255, 255, 255),
        "f_titulo": ("Lora-Variable.ttf", 700),
        "f_marca": ("Lora-Italic-Variable.ttf", 600),
        "f_bold": ("Poppins-Bold.ttf", None),
        "f_med": ("Poppins-Medium.ttf", None),
        "css": {"bg": "#F7EFEA", "card": "#fff", "txt": "#2B1F22", "sub": "#8a7478",
                "acc": "#C2697A", "line": "#ead9d1", "dark_bg": "#1f1719", "dark_card": "#2b2124",
                "dark_txt": "#f7efea", "dark_sub": "#c9b3b6", "dark_line": "#3a2e31"},
        "fonte_site": "Poppins,system-ui,sans-serif",
        "google_fonts": "https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,600;1,600&family=Poppins:wght@400;500;600&display=swap",
        "titulo_site": "font-family:Lora,serif;font-style:italic;font-weight:600",
    },
}


def tema():
    return TEMAS.get((os.getenv("THEME") or "techbarato").strip().lower(), TEMAS["techbarato"])
