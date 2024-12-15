import os
from basicsr.utils import imwrite
from gfpgan.utils import GFPGANer
import numpy as np 

GFPGAN_model_path = os.path.expanduser("~/Models/GFPGANv1.3.pth")

class GFPGANInference:
    def __init__(self, model_path=GFPGAN_model_path, upscale=2, arch='clean', channel_multiplier=2, bg_upsampler=None):
        """
        Initialize the GFPGAN inference model.

        Parameters:
            model_path (str): Path to the pretrained model.
            upscale (int): Upscaling factor.
            arch (str): Model architecture.
            channel_multiplier (int): Channel multiplier for the model.
            bg_upsampler: Background upsampler, if any.
        """
        self.restorer = GFPGANer(
            model_path=model_path,
            upscale=upscale,
            arch=arch,
            channel_multiplier=channel_multiplier,
            bg_upsampler=bg_upsampler
        )

    def inference(self, img):
        """
        Perform inference on an input image.

        Parameters:
            img (numpy.ndarray): Input image as a NumPy array.

        Returns:
            list: Restored faces.
        """
        # Run the restoration
        _, _, restored_img = self.restorer.enhance(
            img, has_aligned=False, only_center_face=False, paste_back=True, weight=0.5
        )
        return restored_img

    @staticmethod
    def save_faces(restored_faces, output_dir, basename, suffix=None):
        """
        Save restored faces to the specified directory.

        Parameters:
            restored_faces (list): List of restored faces.
            output_dir (str): Directory to save the faces.
            basename (str): Base name for saved files.
            suffix (str): Optional suffix for file names.
        """
        os.makedirs(os.path.join(output_dir, 'restored_faces'), exist_ok=True)

        for idx, restored_face in enumerate(restored_faces):
            # Save restored face
            if suffix is not None:
                save_face_name = f'{basename}_{idx:02d}_{suffix}.png'
            else:
                save_face_name = f'{basename}_{idx:02d}.png'

            save_restore_path = os.path.join(output_dir, 'restored_faces', save_face_name)
            imwrite(restored_face, save_restore_path)

    @staticmethod
    def is_small_face(bbox, min_size=50):
        """
        Kiểm tra xem khuôn mặt có kích thước nhỏ hơn ngưỡng cho phép hay không.

        Args:
            bbox (list or numpy.ndarray): Bounding box 1D ở dạng [x1, y1, x2, y2].
            min_size (int): Ngưỡng tối thiểu cho chiều rộng hoặc chiều cao (default: 50).

        Returns:
            bool: True nếu khuôn mặt là nhỏ, False nếu ngược lại.
        """
        if not isinstance(bbox, (list, np.ndarray)) or len(bbox) != 4:
            raise ValueError(f"Expected bbox to be a list or numpy array of length 4, got {type(bbox)} with shape {len(bbox)}")

        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1

        return width < min_size or height < min_size


