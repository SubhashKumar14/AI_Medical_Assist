"""
OCR Engine for Medical Report Text Extraction

Extracts text from PDF and image files using Tesseract/PaddleOCR.
Handles various medical report formats.
"""

import io
import os
from typing import Optional
from pathlib import Path

# Try to import OCR libraries
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import pdf2image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False


class OCREngine:
    """
    OCR Engine for extracting text from medical reports.
    
    Supports:
    - PDF files (converted to images first)
    - PNG, JPG, JPEG images
    - Falls back between Tesseract and PaddleOCR
    """
    
    def __init__(self, use_paddle: bool = False):
        """
        Initialize OCR engine.
        
        Args:
            use_paddle: Use PaddleOCR instead of Tesseract (better for complex layouts)
        """
        self.use_paddle = use_paddle and PADDLE_AVAILABLE
        
        if self.use_paddle:
            self.paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        
        # Tesseract configuration for medical documents
        self.tesseract_config = '--oem 3 --psm 6'
    
    def extract_text(self, content: bytes, content_type: str) -> str:
        """
        Extract text from file content.
        
        Args:
            content: Raw file bytes
            content_type: MIME type (application/pdf, image/png, etc.)
            
        Returns:
            Extracted text string
        """
        try:
            if 'pdf' in content_type.lower():
                return self._extract_from_pdf(content)
            elif 'image' in content_type.lower():
                return self._extract_from_image(content)
            else:
                raise ValueError(f"Unsupported content type: {content_type}")
        except Exception as e:
            # Return error message that can be handled upstream
            return f"[OCR Error: {str(e)}]"
    
    def _extract_from_pdf(self, content: bytes) -> str:
        """Extract text from PDF file."""
        if not PDF2IMAGE_AVAILABLE:
            return "[Error: PDF processing not available. Install pdf2image and poppler.]"
        
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_bytes(content, dpi=300)
            
            all_text = []
            for i, image in enumerate(images):
                page_text = self._ocr_image(image)
                all_text.append(f"--- Page {i + 1} ---\n{page_text}")
            
            return "\n\n".join(all_text)
        except Exception as e:
            return f"[PDF extraction error: {str(e)}]"
    
    def _extract_from_image(self, content: bytes) -> str:
        """Extract text from image file."""
        try:
            image = Image.open(io.BytesIO(content))
            return self._ocr_image(image)
        except Exception as e:
            return f"[Image extraction error: {str(e)}]"
    
    def _ocr_image(self, image: 'Image.Image') -> str:
        """
        Perform OCR on a PIL Image.
        
        Uses PaddleOCR or Tesseract based on configuration.
        """
        if self.use_paddle:
            return self._paddle_ocr(image)
        else:
            return self._tesseract_ocr(image)
    
    def _tesseract_ocr(self, image: 'Image.Image') -> str:
        """Extract text using Tesseract OCR."""
        if not TESSERACT_AVAILABLE:
            return "[Error: Tesseract not available. Install pytesseract and tesseract-ocr.]"
        
        try:
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Perform OCR
            text = pytesseract.image_to_string(image, config=self.tesseract_config)
            return text.strip()
        except Exception as e:
            return f"[Tesseract error: {str(e)}]"
    
    def _paddle_ocr(self, image: 'Image.Image') -> str:
        """Extract text using PaddleOCR."""
        if not PADDLE_AVAILABLE:
            return "[Error: PaddleOCR not available. Install paddleocr.]"
        
        try:
            import numpy as np
            
            # Convert PIL to numpy array
            image_np = np.array(image)
            
            # Perform OCR
            result = self.paddle_ocr.ocr(image_np, cls=True)
            
            # Extract text from results
            lines = []
            for line in result:
                if line:
                    for word_info in line:
                        if word_info and len(word_info) > 1:
                            text = word_info[1][0]
                            lines.append(text)
            
            return "\n".join(lines)
        except Exception as e:
            return f"[PaddleOCR error: {str(e)}]"
    
    def preprocess_image(self, image: 'Image.Image') -> 'Image.Image':
        """
        Preprocess image for better OCR results.
        
        Applies:
        - Grayscale conversion
        - Contrast enhancement
        - Noise reduction
        """
        try:
            from PIL import ImageEnhance, ImageFilter
            
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Sharpen
            image = image.filter(ImageFilter.SHARPEN)
            
            return image
        except Exception:
            return image


# Singleton instance
_ocr_engine: Optional[OCREngine] = None

def get_ocr_engine() -> OCREngine:
    """Get or create OCR engine singleton."""
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCREngine()
    return _ocr_engine
