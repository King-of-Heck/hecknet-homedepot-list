# Homedepot List

Buffers homedepot.ca links from a Discord channel and prints a shopping list with aisle and bay numbers.

Paste homedepot.ca product links into a Discord channel through the week. The
bot buffers them silently and reacts to confirm. When you are heading out,
type `!print` and it looks each product up and prints a list:

    HeckNet
    Home Depot List
    Friday, May 22 2026  @ 21:09
    - DEWALT 5/8 in. x 50 ft. Water Hose
      SKU: 1001833572
      Aisle: 25  Bay: 029

Aisle and bay come from the store's own product API, so they are specific to
the store you configure. There is no browser automation and no authentication.

## Setup

1. Create a bot at the [Discord Developer Portal](https://discord.com/developers/applications),
   enable the Message Content intent, and invite it to your server.
2. Put the token in `DISCORD_TOKEN` and the channel ID in
   `HOME_DEPOT_CHANNEL`.
3. Set `HD_STORE_ID` to your local store. Select a store on homedepot.ca and
   read the number out of the URL.

Lookups are paced two seconds apart and retried three times, which is what it
took to stop the API resetting the connection.

## Requirements

- Windows. Printing goes through the Win32 GDI API.
- Python 3.10 or later.
- An 80mm thermal printer installed as a Windows printer. Built against an
  XP-80C at 203 DPI; other 80mm printers should work if the DPI matches.

```bash
pip install -r requirements.txt
```

Set `PRINTER_NAME` in `homedepot_list.py` to the printer's name as it appears in
Settings > Printers & scanners.

Receipts are rendered as images at 4x and downsampled before printing, which
is what keeps the text dark and legible on a thermal head. Courier is used
throughout; glyphs Courier lacks are composited from Segoe UI Emoji.

## Running

```bash
python homedepot_list.py
```

## A note on the history

Version numbers in the original filenames drifted one ahead of the version history recorded inside them. The changelog is derived from diffing consecutive files rather than from those labels, so it reflects what each file actually contained.

## Versioning

Tagged releases, with the change notes in [CHANGELOG.md](CHANGELOG.md).

## Licence

MIT. See [LICENSE](LICENSE).
