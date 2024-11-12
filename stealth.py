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

    DESCRIPTION = "Saves the input images to your ComfyUI output directory, with metadata additionally written to the alpha channel or RGB channels."

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
                # Handle `parameters` first if it exists
                if extra_pnginfo is not None and "parameters" in extra_pnginfo:
                    parameters = extra_pnginfo["parameters"] if isinstance(extra_pnginfo["parameters"], str) else json.dumps(extra_pnginfo["parameters"])
                    if not only_stealth:
                        metadata.add_text("parameters", parameters)
                    stealth_metadata["parameters"] = parameters
                if prompt is not None:
                    prompt_json_string = json.dumps(prompt)
                    if not only_stealth:
                        metadata.add_text("prompt", prompt_json_string)
                    stealth_metadata["prompt"] = prompt_json_string
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        if x == "parameters":  # Skip `parameters` as it's already handled
                            continue
                        extra_pnginfo_x_json_string = json.dumps(extra_pnginfo[x])
                        if not only_stealth:
                            metadata.add_text(x, extra_pnginfo_x_json_string)
                        stealth_metadata[x] = extra_pnginfo_x_json_string
                if mode == "alpha":
                    img.putalpha(Image.new("L", img.size, 255))
                img: Image.Image = stealth_write(img, json.dumps(stealth_metadata), mode, compressed)  # type: ignore

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
    import tkinter as tk
    from tkinter import filedialog, messagebox
    from PIL import Image
    from custom_nodes.comfyui_stealth_pnginfo.util import stealth_read, stealth_write

    def load_image():
        file_path = filedialog.askopenfilename(title="Select an Image", filetypes=[("PNG Images", "*.png")])
        if file_path:
            try:
                global image, geninfo
                image = Image.open(file_path)
                geninfo = stealth_read(image)
                metadata_text.delete("1.0", tk.END)
                metadata_text.insert(tk.END, geninfo)
                status_label.config(text="Image loaded successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")

    def save_image():
        new_geninfo = metadata_text.get("1.0", tk.END).strip()

        # Remove the alpha channel by converting to RGB and then adding a new empty alpha channel
        image_rgb = image.convert("RGB")
        image_rgba = image_rgb.convert("RGBA")  # Recreate with an alpha channel but clear it

        # Get values for mode and compressed based on checkbox states
        mode = "rgb" if mode_var.get() else "alpha"
        compressed = bool(compressed_var.get())

        # Write new metadata with selected mode and compressed settings
        stealth_write(image_rgba, new_geninfo, mode=mode, compressed=compressed)

        # Save with file dialog
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG Images", "*.png")])
        if file_path:
            try:
                image_rgba.save(file_path)
                status_label.config(text="Image saved successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save image: {e}")

    # Initialize main window
    root = tk.Tk()
    root.title("Metadata Editor")
    root.geometry("500x500")

    # Load Image Button
    load_button = tk.Button(root, text="Load Image", command=load_image)
    load_button.pack(pady=10)

    # Metadata Text Area
    metadata_text = tk.Text(root, wrap=tk.WORD, height=15, width=50)
    metadata_text.pack(padx=10, pady=10)

    # Mode Checkbox
    mode_var = tk.IntVar(value=0)  # Default is "alpha" (unchecked)
    mode_checkbox = tk.Checkbutton(root, text="Use RGB mode for metadata", variable=mode_var)
    mode_checkbox.pack(pady=5)

    # Compressed Checkbox
    compressed_var = tk.IntVar(value=1)  # Default is True (checked)
    compressed_checkbox = tk.Checkbutton(root, text="Compress metadata", variable=compressed_var)
    compressed_checkbox.pack(pady=5)

    # Save Image Button
    save_button = tk.Button(root, text="Save Image", command=save_image)
    save_button.pack(pady=10)

    # Status Label
    status_label = tk.Label(root, text="", fg="green")
    status_label.pack(pady=10)

    root.mainloop()
