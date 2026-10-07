import cv2
import numpy as np

def adjust_contrast(img: np.ndarray, alpha: float = 1.3, beta: int = 10) -> np.ndarray:
    """
    Adjusts contrast (alpha) and brightness (beta).
    alpha: Contrast control [1.0 - 3.0]
    beta: Brightness control [-100 - 100]
    """
    adjusted = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
    return adjusted
