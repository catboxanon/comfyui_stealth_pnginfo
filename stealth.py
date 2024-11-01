import os
import json
from PIL import Image
from PIL.PngImagePlugin import PngInfo
import numpy as np
from nodes import SaveImage
from comfy.cli_args import args
import folder_paths

try:
    from .util import stealth_write
except ImportError:
    stealth_write = lambda *args, **kwargs: None


class SaveImageStealth(SaveImage):
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save."}),
                "filename_prefix": ("STRING", {"default": "ComfyUI-Stealth", "tooltip": "The prefix for the file to save. This may include formatting information such as %date:yyyy-MM-dd% or %Empty Latent Image.width% to include values from nodes."}),
                "mode": (["alpha", "rgb"], {"default": "alpha"}),
                "compressed": ("BOOLEAN", {"default": True, "tooltip": "Compress the metadata using gzip."}),
                "only_stealth": ("BOOLEAN", {"default": False, "tooltip": "Only save stealth metadata (no PNG tEXt chunks)"}),
            },
            "hidden": {
                "prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    DESCRIPTION = "Saves the input images to your ComfyUI output directory, with metadata additionally written to the alpha channel."

    def save_images(self, images, filename_prefix="ComfyUI-Stealth", prompt=None, extra_pnginfo=None, mode="alpha", compressed=True, only_stealth=False):
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
        results = list()
        for (batch_number, image) in enumerate(images):
            i = 255. * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = None
            if not args.disable_metadata:
                stealth_metadata = {}
                metadata = PngInfo()
                if prompt is not None:
                    prompt_json_string = json.dumps(prompt)
                    if not only_stealth:
                        metadata.add_text("prompt", prompt_json_string)
                    stealth_metadata["prompt"] = prompt_json_string
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        extra_pnginfo_x_json_string = json.dumps(extra_pnginfo[x])
                        if not only_stealth:
                            metadata.add_text(x, extra_pnginfo_x_json_string)
                        stealth_metadata[x] = extra_pnginfo_x_json_string
                if mode == "alpha":
                    img.putalpha(Image.new("L", img.size, 255))
                img = stealth_write(img, json.dumps(stealth_metadata), mode, compressed)

            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            file = f"{filename_with_batch_num}_{counter:05}_.png"
            img.save(os.path.join(full_output_folder, file), pnginfo=metadata, compress_level=self.compress_level)
            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": self.type
            })
            counter += 1

        return { "ui": { "images": results } }


if __name__ == "__main__":
    import sys
    from custom_nodes.comfyui_stealth_pnginfo.util import stealth_read
    image = Image.open(sys.argv[1])
    geninfo = stealth_read(image)
    print(geninfo)
