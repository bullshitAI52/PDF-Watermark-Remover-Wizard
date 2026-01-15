from PIL import Image
from collections import Counter

try:
    img = Image.open("extracted_kspx1.jpg")
    img = img.resize((100, 100))
    pixels = list(img.getdata())
    # remove white/transparent
    pixels = [p for p in pixels if p[0] < 240 or p[1] < 240 or p[2] < 240]
    
    if not pixels:
        print("Image is blank/white.")
    else:
        most_common = Counter(pixels).most_common(5)
        print("Dominant Colors (RGB):")
        for color, count in most_common:
            print(f"  RGB{color} - Count: {count}")
except Exception as e:
    print(e)
