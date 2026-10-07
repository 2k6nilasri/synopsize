import cv2
import numpy as np


def sharpen_image(img: np.ndarray, intensity: float = 1.5) -> np.ndarray:
    """Applies unsharp mask sharpening to improve edge clarity without resizing the image."""
    blurred = cv2.GaussianBlur(img, (0, 0), 1.5)
    return cv2.addWeighted(img, 1.0 + intensity, blurred, -intensity, 0)
