import cv2
import numpy as np

def denoise_image(img: np.ndarray, strength: int = 10) -> np.ndarray:
    """Removes noise and cleans background using Fast Non-Local Means Denoising."""
    if len(img.shape) == 3:
        denoised = cv2.fastNlMeansDenoisingColored(img, None, strength, strength, 7, 21)
    else:
        denoised = cv2.fastNlMeansDenoising(img, None, strength, 7, 21)
    return denoised
