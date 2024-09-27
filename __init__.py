from . import stealth


NODE_CLASS_MAPPINGS = {
    "CatboxAnonSaveImageStealth": stealth.SaveImageStealth,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "CatboxAnonSaveImageStealth": "Save Image (Stealth)",
}
WEB_DIRECTORY = "./js"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
