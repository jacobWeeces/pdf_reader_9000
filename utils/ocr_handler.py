import pytesseract
from PIL import Image as PILImage

class OCRHandler:
    def __init__(self):
        self.engine = pytesseract
        
    def process_image(self, image):
        """Process image through OCR engine"""
        try:
            # Configure OCR for better accuracy
            custom_config = r'--oem 3 --psm 6'
            return self.engine.image_to_string(image, config=custom_config)
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
            
    def process_page(self, page):
        """Process a PyMuPDF page through OCR"""
        if not page:
            return ""
            
        try:
            # Convert page to image for OCR
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
            img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return self.process_image(img)
        except Exception as e:
            print(f"Page OCR Error: {e}")
            return "" 