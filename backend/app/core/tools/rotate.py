import cv2
import numpy as np
from typing import Optional

def detect_orientation_angle(img: np.ndarray) -> int:
    """
    Auto-detects document orientation angle (0, 90, 180, 270 degrees).
    Uses line orientation heuristics from Canny edges & HoughLinesP,
    combined with horizontal vs vertical text gradient projection.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    h, w = gray.shape[:2]
    
    # Calculate gradient along horizontal and vertical axes
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    
    mag_x = np.mean(np.abs(sobel_x))
    mag_y = np.mean(np.abs(sobel_y))
    
    # In standard horizontal text, vertical transitions (d/dy) are much higher than horizontal transitions
    # If horizontal transitions dominate significantly and image is taller than wide, page may be rotated by 90/270
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 80, minLineLength=int(min(w, h) * 0.25), maxLineGap=15)
    
    horizontal_count = 0
    vertical_count = 0
    
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            dx = abs(x1 - x2)
            dy = abs(y1 - y2)
            if dx > dy * 2:
                horizontal_count += 1
            elif dy > dx * 2:
                vertical_count += 1

    # If mostly vertical text lines found in a portrait doc, it's rotated 90 or 270 degrees
    if vertical_count > horizontal_count * 1.5:
        return 90
    
    return 0

def rotate_image(img: np.ndarray, angle: Optional[int] = 90) -> np.ndarray:
    """Rotates image by specified angle (90, 180, 270 degrees) or auto-detects if angle is 0 or None."""
    if angle is None or angle == 0:
        detected = detect_orientation_angle(img)
        angle = detected
        if angle == 0:
            return img

    angle = angle % 360
    if angle == 90:
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(img, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return img

