from pathlib import Path
import sys
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vesper.rules import GOVERNMENT_WARNING


OUTPUT = ROOT / "sample_labels"


def font(size: int, bold: bool = False):
    names = ["arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def label(name: str, *, brand="VESPER RESERVE", spirit="VODKA", alcohol="40% ALCOHOL BY VOLUME (80 PROOF)",
          volume="750 mL", warning=GOVERNMENT_WARNING, rotate=0):
    image = Image.new("RGB", (1200, 1600), "#f4efe4")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((70, 60, 1130, 1540), 28, outline="#b88a3b", width=6)
    draw.text((600, 160), brand, font=font(70, True), fill="#152421", anchor="mm")
    draw.text((600, 275), spirit, font=font(48), fill="#6f5427", anchor="mm")
    draw.line((240, 335, 960, 335), fill="#b88a3b", width=3)
    draw.text((600, 440), alcohol, font=font(36, True), fill="#152421", anchor="mm")
    draw.text((600, 540), volume, font=font(40), fill="#152421", anchor="mm")
    y = 760
    for idx, line in enumerate(wrap(warning, 68)):
        draw.text((130, y), line, font=font(24, idx == 0), fill="#152421")
        y += 40
    draw.text((600, 1400), "BOTTLED BY VESPER SPIRITS, BALTIMORE, MD", font=font(22), fill="#59635f", anchor="mm")
    if rotate:
        image = image.rotate(rotate, expand=True, fillcolor="white")
    image.save(OUTPUT / name, quality=94)


def main():
    OUTPUT.mkdir(exist_ok=True)
    label("01_perfect_match.png")
    label("02_wrong_abv.png", alcohol="45% ALCOHOL BY VOLUME (90 PROOF)")
    label("03_wrong_proof.png", alcohol="40% ALCOHOL BY VOLUME (86 PROOF)")
    label("04_missing_warning.png", warning="")
    label("05_wrong_net_contents.png", volume="700 mL")
    label("06_rotated_label.png", rotate=90)
    label("07_class_mismatch.png", spirit="GIN")
    label(
        "08_low_contrast.png",
        brand="VESPER RESERVE", spirit="VODKA",
        warning=GOVERNMENT_WARNING.replace("health problems.", "health problem.")
    )
    print(f"Generated 8 sample labels in {OUTPUT}")


if __name__ == "__main__":
    main()
