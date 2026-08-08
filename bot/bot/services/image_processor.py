from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from config.logger import logger


class ImageProcessor:
    """Screenshot uchun yumshoq preprocessing.

    Screenshot allaqachon toza va anti-aliased bo'ladi — Otsu binarization
    yoki og'ir denoising uni buzadi. Shuning uchun faqat:
      1. Grayscale (EasyOCR gray'ni yaxshi qabul qiladi)
      2. Kichik rasmni 2x upscale (kichik matnlar aniqroq o'qiladi)
      3. Yengil CLAHE (past-kontrastli screenshot uchun)
    """

    UPSCALE_THRESHOLD_PX = 1000  # kichik tomon shundan kichik bo'lsa upscale

    def preprocess(self, image_path: str | Path) -> np.ndarray:
        path = Path(image_path)
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f"Rasm o'qilmadi: {path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 1) Yengil kontrast (juda past clipLimit)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 2) Upscale — faqat rasm kichik bo'lsa
        h, w = enhanced.shape
        if min(h, w) < self.UPSCALE_THRESHOLD_PX:
            scale = 2
            enhanced = cv2.resize(
                enhanced, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC
            )
            logger.debug(f"Rasm upscale qilindi: {w}x{h} -> {w*scale}x{h*scale}")

        logger.debug(f"Image preprocessed: {path.name}, shape={enhanced.shape}")
        return enhanced

    def load_original_gray(self, image_path: str | Path) -> np.ndarray | None:
        """Asl (deyarli xom) grayscale variant — solishtirish uchun."""
        img = cv2.imread(str(image_path))
        if img is None:
            return None
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    def save_debug(self, image: np.ndarray, output_path: str | Path) -> None:
        cv2.imwrite(str(output_path), image)
