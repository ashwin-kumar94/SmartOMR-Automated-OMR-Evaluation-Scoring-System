import cv2
import numpy as np

# Step 1: Load image

def load_image(image_path):
    """Load an image from file."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Image not found: {image_path}")
    return img

# Step 2: Correct orientation and skew

def correct_orientation(img):
    """Convert to grayscale, threshold, and deskew the image."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(thresh > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated, angle

# Step 3: Save rectified image

def save_image(img, path):
    cv2.imwrite(path, img)

def detect_bubble_grid(img):
    """Detect the largest rectangular contour (bubble grid) in the image."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blur, 50, 200)
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest_area = 0
    bubble_grid = None
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > largest_area:
            largest_area = area
            bubble_grid = cnt
    if bubble_grid is None:
        raise Exception("Bubble grid not found.")
    x, y, w, h = cv2.boundingRect(bubble_grid)
    grid_img = img[y:y+h, x:x+w]
    return grid_img, (x, y, w, h)

def detect_filled_bubbles(grid_img, rows=5, cols=20):
    """Detect filled bubbles in the grid image. Returns a matrix of True/False for filled/unfilled."""
    gray = cv2.cvtColor(grid_img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    bubble_matrix = np.zeros((rows, cols), dtype=bool)
    bubble_h = h // rows
    bubble_w = w // cols
    for i in range(rows):
        for j in range(cols):
            y1 = i * bubble_h
            y2 = (i + 1) * bubble_h
            x1 = j * bubble_w
            x2 = (j + 1) * bubble_w
            bubble_roi = gray[y1:y2, x1:x2]
            mean_intensity = np.mean(bubble_roi)
            # Threshold: lower mean means filled
            bubble_matrix[i, j] = mean_intensity < 127
    return bubble_matrix

def load_answer_key(csv_path, rows, cols):
    """Load answer key from CSV file. Returns a boolean matrix."""
    import csv
    key_matrix = np.zeros((rows, cols), dtype=bool)
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            for j, val in enumerate(row):
                key_matrix[i, j] = int(val) == 1
    return key_matrix

# Example usage
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 6:
        print("Usage: python omr_core.py <input_image> <output_image> <rows> <cols> <answer_key_csv>")
        sys.exit(1)
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    rows = int(sys.argv[3])
    cols = int(sys.argv[4])
    answer_key_path = sys.argv[5]
    img = load_image(input_path)
    rectified, angle = correct_orientation(img)
    save_image(rectified, output_path)
    print(f"Rectified image saved to {output_path}, rotation angle: {angle}")
    grid_img, grid_coords = detect_bubble_grid(rectified)
    grid_output_path = output_path.replace('.jpeg', '_grid.jpeg')
    save_image(grid_img, grid_output_path)
    print(f"Bubble grid saved to {grid_output_path}, coordinates: {grid_coords}")
    bubble_matrix = detect_filled_bubbles(grid_img, rows, cols)
    print("Filled bubble matrix (True=filled, False=unfilled):")
    print(bubble_matrix)
    # Load answer key and score
    answer_key = load_answer_key(answer_key_path, rows, cols)
    score = np.sum(bubble_matrix == answer_key)
    print(f"Score: {score} out of {rows * cols}")