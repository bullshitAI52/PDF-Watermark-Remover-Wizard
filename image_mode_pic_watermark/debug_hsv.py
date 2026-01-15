
import cv2
import numpy as np

def analyze_hsv(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read {image_path}")
        return

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Reshape to list of pixels
    pixels = hsv.reshape(-1, 3)
    
    # Filter out white background (low saturation, high value) and black text (low value)
    # White: Saturation < 10, Value > 240
    # Black: Value < 50
    # We want things that are NOT white/grey and NOT black.
    
    mask_not_white = (pixels[:, 1] > 5) | (pixels[:, 2] < 240)
    mask_not_black = pixels[:, 2] > 100 
    
    target_pixels = pixels[mask_not_white & mask_not_black]
    
    if len(target_pixels) == 0:
        print("No colored pixels found matching criteria.")
        return

    # Calculate average and ranges
    h_mean = np.mean(target_pixels[:, 0])
    s_mean = np.mean(target_pixels[:, 1])
    v_mean = np.mean(target_pixels[:, 2])
    
    print(f"Mean HSV: H={h_mean:.1f}, S={s_mean:.1f}, V={v_mean:.1f}")
    print(f"Min HSV: {np.min(target_pixels, axis=0)}")
    print(f"Max HSV: {np.max(target_pixels, axis=0)}")
    
    # Histogram of Hues to see dominant colors
    # H ranges 0-179
    hist = np.bincount(target_pixels[:, 0], minlength=180)
    print("\nDominant Hues (top 10):")
    top_hues = np.argsort(hist)[-10:][::-1]
    for h in top_hues:
        print(f"Hue {h}: {hist[h]} pixels")

if __name__ == "__main__":
    analyze_hsv("/Users/apple/.gemini/antigravity/brain/842d0fd0-a689-4f65-986c-564525b67e8e/uploaded_image_1768467227730.png")
