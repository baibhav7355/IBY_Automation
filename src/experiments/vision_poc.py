"""
Vision PoC: Visual State Embeddings & Cosine Similarity
Purpose: Offline processing of 32,000 Dataset A screenshots to detect silent UI changes.
This module uses a lightweight MobileNet model to vectorize 1080p images locally,
calculating cosine similarity between consecutive frames to identify task boundaries
without incurring expensive Vision API costs.
"""
import torch
import torchvision.transforms as transforms
from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
from scipy.spatial.distance import cosine
from PIL import Image

# Initialize lightweight pre-trained model for local inference
weights = MobileNet_V3_Small_Weights.DEFAULT
model = mobilenet_v3_small(weights=weights)
model.eval()
preprocess = weights.transforms()

def vectorize_screenshot(image_path: str) -> list:
    """Compresses a raw screenshot into a dense numerical vector."""
    img = Image.open(image_path).convert("RGB")
    batch = preprocess(img).unsqueeze(0)
    with torch.no_grad():
        vector = model(batch).squeeze().numpy()
    return vector

def detect_segment_boundary(img_path_1: str, img_path_2: str, threshold: float = 0.85) -> bool:
    """Evaluates two consecutive frames to detect structural UI changes."""
    vec1 = vectorize_screenshot(img_path_1)
    vec2 = vectorize_screenshot(img_path_2)
    
    # Calculate cosine similarity (1 - cosine distance)
    similarity = 1 - cosine(vec1, vec2)
    print(f"Consecutive Frame Similarity: {similarity:.4f}")
    
    if similarity < threshold:
        print("Action: Significant visual drift detected (Similarity < 0.85). Triggering new segment.")
        return True
    
    print("Action: Task continuous. Extending current segment.")
    return False

if __name__ == "__main__":
    # Example usage for evaluators
    print("Vision PoC initialized: Ready for local batch processing of Dataset A.")
