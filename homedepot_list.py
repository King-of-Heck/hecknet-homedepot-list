"""
HeckNet_HomeDepot_1_1.py
Discord bot that watches a single channel for homedepot.ca product links.
When you type !print it scrapes all buffered links and prints a receipt:

    💀 HeckNet 💀
    Home Depot List
    Friday, May 22 2026  @ 21:09
    • DEWALT 5/8 in. x 50 ft. Water Hose
      SKU: 1001833572
      Aisle: 25  Bay: 029
    • ...

Links pasted without !print are silently buffered (bot reacts 🛒).
!print with no buffered links reacts ❓ and does nothing.
Uses homedepot.ca's internal product API directly — no Playwright needed.
"""

import asyncio
import re
import io
from datetime import datetime

import requests
import discord
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageWin
import win32ui


DISCORD_TOKEN       = "YOUR_BOT_TOKEN_HERE"   # paste your bot token here
HOME_DEPOT_CHANNEL  = 0                        # ← paste your channel ID here

PRINTER_NAME = "XP-80C"
FONT_PATH    = "cour.ttf"
FONT_BOLD    = "courbd.ttf"

# Your local Home Depot store ID — used for aisle/bay lookups.
# Find it in the URL when you select a store on homedepot.ca (e.g. storeId=7145).
HD_STORE_ID  = "7080"


PRINTER_DPI  = 203
PAPER_MM     = 80
PAPER_PX     = int(PAPER_MM / 25.4 * PRINTER_DPI)   # ≈ 638 px
MARGIN_PX    = 10
TEXT_PX      = PAPER_PX - 2 * MARGIN_PX
FONT_SIZE       = 36
FONT_SIZE_SM    = 26
SKULL_FONT_SIZE = 24
RENDER_SCALE    = 4
SKULL_Y_OFFSET  = 40


def load_font(bold=False, size=None):
    size = size or FONT_SIZE
    path = FONT_BOLD if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size * RENDER_SCALE)
    except OSError:
        return ImageFont.load_default()

_SKULL_FONT_CANDIDATES = [
    "seguiemj.ttf",
    "C:/Windows/Fonts/seguiemj.ttf",
    "seguisym.ttf",
]

def load_skull_font(size=None):
    size = size or SKULL_FONT_SIZE
    for path in _SKULL_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size * RENDER_SCALE)
        except OSError:
            continue
    return load_font(bold=True, size=size)


HD_URL_RE = re.compile(
    r"https?://(?:www\.)?homedepot\.ca/product/[^/]+/(\d+)",
    re.IGNORECASE
)


HD_URL_RE = re.compile(
    r"https?://(?:www\.)?homedepot\.ca/product/[^/]+/(\d+)",
    re.IGNORECASE
)

HD_API_URL = "https://www.homedepot.ca/api/productsvc/v1/products/{sku}/store/{store}?fields=BASIC_SPA&lang=en"

HD_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json",
    "Accept-Language": "en-CA,en;q=0.9",
    "Referer":         "https://www.homedepot.ca/",
}

HD_NAME_URL = "https://www.homedepot.ca/api/productsvc/v1/products/{sku}?lang=en"

async def scrape_product(url: str) -> dict:
    """
    Fetch product info from homedepot.ca's internal API.
    Returns a dict with keys: name, sku, aisle, bay.
    Missing fields are None.
    """
    m = HD_URL_RE.search(url)
    sku = m.group(1) if m else None

    slug = url.rstrip("/").split("/")[-2] if "/" in url else ""
    name_from_url = slug.replace("-", " ").title()

    result = {
        "name":  name_from_url,
        "sku":   sku,
        "aisle": None,
        "bay":   None,
    }

    if not sku:
        return result

    try:
        api_url = HD_API_URL.format(sku=sku, store=HD_STORE_ID)
        resp = requests.get(api_url, headers=HD_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        aisle_bay = data.get("aisleBay", {})
        if aisle_bay:
            result["aisle"] = aisle_bay.get("aisleLocation")
            result["bay"]   = aisle_bay.get("bayLocation")

        name_url = HD_NAME_URL.format(sku=sku)
        resp2 = requests.get(name_url, headers=HD_HEADERS, timeout=15)
        if resp2.ok:
            data2 = resp2.json()
            name = (
                data2.get("name")
                or data2.get("productName")
                or (data2.get("summary", {}) or {}).get("name")
                or (data2.get("product", {}) or {}).get("name")
            )
            if name:
                result["name"] = name

    except Exception as e:
        print(f"API error for SKU {sku}: {e}")

    return result


def word_wrap(text: str, font, max_width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        candidate = (line + " " + word).strip()
        if font.getlength(candidate) <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines or [""]


def draw_skull_header(draw, text: str, font_text, font_skull, paper_w: int, y: int):
    SKULL   = "\U0001F480"
    gap     = int(font_text.size * 0.4)
    skull_w = int(font_skull.getlength(SKULL))
    text_w  = int(font_text.getlength(text))
    total_w = skull_w + gap + text_w + gap + skull_w
    x = (paper_w - total_w) // 2
    draw.text((x, y + SKULL_Y_OFFSET), SKULL, font=font_skull, fill="black")
    x += skull_w + gap
    draw.text((x, y), text, font=font_text, fill="black")
    x += text_w + gap
    draw.text((x, y + SKULL_Y_OFFSET), SKULL, font=font_skull, fill="black")


def build_homedepot_receipt(products: list[dict], timestamp: datetime) -> Image.Image:
    """
    Renders a Home Depot shopping list receipt.
    products: list of dicts with keys name, sku, aisle, bay.
    """
    S       = RENDER_SCALE
    paper_w = PAPER_PX * S
    margin  = MARGIN_PX * S
    text_w  = TEXT_PX * S
    line_h  = (FONT_SIZE + 6) * S
    line_h_sm = (FONT_SIZE_SM + 4) * S

    font_n     = load_font(bold=False)
    font_b     = load_font(bold=True)
    font_sm    = load_font(bold=False,  size=FONT_SIZE_SM)
    font_sm_b  = load_font(bold=True,   size=FONT_SIZE_SM)
    font_skull = load_skull_font(size=SKULL_FONT_SIZE)
    DIVIDER    = "─" * int(text_w / (FONT_SIZE * S * 0.62))

    ops = []

    def add(text, font=None, align="left"):
        ops.append((text, font or font_n, align))

    def div():
        add(DIVIDER, font_n, "center")

    add("",        font_b,    "center")   # skull placeholder
    div()
    add("Home Depot List", font_b,    "center")
    add(timestamp.strftime("%A, %B %d %Y"), font_sm,  "center")
    add(timestamp.strftime("@ %H:%M"),       font_sm,  "center")
    div()

    for product in products:
        name  = product.get("name")  or "Unknown Product"
        sku   = product.get("sku")
        aisle = product.get("aisle")
        bay   = product.get("bay")

        name_lines = word_wrap(name, font_sm_b, text_w - margin)
        for i, line in enumerate(name_lines):
            prefix = "\u2022 " if i == 0 else "  "
            add(prefix + line, font_sm_b)

        if sku:
            add(f"  SKU: {sku}", font_sm)

        if aisle and bay:
            add(f"  Aisle: {aisle}   Bay: {bay}", font_sm)
        elif aisle:
            add(f"  Aisle: {aisle}", font_sm)
        elif bay:
            add(f"  Bay: {bay}", font_sm)

        div()

    total_h = len(ops) * line_h + line_h * 2 + SKULL_Y_OFFSET
    hi_res  = Image.new("RGB", (paper_w, total_h), "white")
    draw    = ImageDraw.Draw(hi_res)
    y       = margin // 2 + SKULL_Y_OFFSET

    for i, (text, font, align) in enumerate(ops):
        if align == "center":
            bbox = font.getbbox(text)
            tw   = bbox[2] - bbox[0]
            x    = (paper_w - tw) / 2 - bbox[0]
        else:
            x = margin

        if i == 0:
            draw_skull_header(draw, "HeckNet", font_b, font_skull, paper_w, y)
        else:
            draw.text((x, y), text, font=font, fill="black")

        y += line_h

    out_w  = PAPER_PX
    out_h  = int(hi_res.height / S)
    output = hi_res.resize((out_w, out_h), Image.LANCZOS)
    output = ImageEnhance.Contrast(output).enhance(2.5).convert("L").convert("RGB")
    output = output.crop((0, 0, out_w, int(y / S) + 4))
    return output


def send_to_printer(img: Image.Image):
    hdc = win32ui.CreateDC()
    hdc.CreatePrinterDC(PRINTER_NAME)
    pw = hdc.GetDeviceCaps(110)
    if img.width != pw:
        img = img.resize((pw, int(img.height * pw / img.width)), Image.LANCZOS)
    hdc.StartDoc("Home Depot List")
    hdc.StartPage()
    ImageWin.Dib(img).draw(hdc.GetHandleOutput(), (0, 0, img.width, img.height))
    hdc.EndPage()
    hdc.EndDoc()
    hdc.DeleteDC()


_link_buffer: list[str] = []


intents = discord.Intents.default()
intents.message_content = True
client  = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f" Home Depot bot ready: {client.user}")
    print(f"   Watching channel: {HOME_DEPOT_CHANNEL}")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return
    if message.channel.id != HOME_DEPOT_CHANNEL:
        return

    content = message.content.strip()

    if content.lower() == "!print":
        if not _link_buffer:
            await message.add_reaction("❓")
            await message.reply("No links buffered yet — paste some homedepot.ca links first!", delete_after=15)
            return

        urls = list(_link_buffer)
        _link_buffer.clear()

        await message.add_reaction("⏳")
        print(f"!print — scraping {len(urls)} product(s)...")

        async def scrape_and_print():
            products = []
            for url in urls:
                print(f"Scraping: {url}")
                product = await scrape_product(url)
                products.append(product)
                print(f"{product['name']} | SKU {product['sku']} | Aisle {product['aisle']} Bay {product['bay']}")

            try:
                def print_it():
                    img = build_homedepot_receipt(products, datetime.now().astimezone())
                    send_to_printer(img)
                await asyncio.get_event_loop().run_in_executor(None, print_it)
                await message.add_reaction("🖨️")
                print("Printed.")
            except Exception as e:
                print(f"Print error: {e}")
                await message.add_reaction("❌")
                await message.reply(f"⚠️ Print failed: {e}", delete_after=15)

        asyncio.create_task(scrape_and_print())
        return

    added = 0
    for m in HD_URL_RE.finditer(content):
        url = m.group(0)
        if url not in _link_buffer:
            _link_buffer.append(url)
            added += 1

    if added:
        await message.add_reaction("🛒")
        print(f"Buffered {added} link(s). Total: {len(_link_buffer)}")
    elif content:
        await message.add_reaction("❓")


if __name__ == "__main__":
    if DISCORD_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Paste your bot token into DISCORD_TOKEN at the top of the file!")
        exit(1)
    if HOME_DEPOT_CHANNEL == 0:
        print("Paste your channel ID into HOME_DEPOT_CHANNEL at the top of the file!")
        exit(1)
    client.run(DISCORD_TOKEN)
