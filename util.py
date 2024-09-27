import sys
from unittest.mock import Mock

def mock_imports(modules_to_mock):
    original_modules = {module: sys.modules.get(module) for module in modules_to_mock}

    for module in modules_to_mock:
        sys.modules[module] = Mock()

    def cleanup():
        for module, original_module in original_modules.items():
            if original_module is not None:
                sys.modules[module] = original_module
            else:
                del sys.modules[module]

    return cleanup

cleanup = mock_imports(['modules', 'modules.script_callbacks', 'gradio'])
try:
    from .scripts import stealth_pnginfo
    from .scripts.stealth_pnginfo import add_data, read_info_from_image_stealth
    stealth_pnginfo.original_read_info_from_image = lambda image: (None, None)
finally:
    cleanup()

class ParamsMock:
    def __init__(self, image, parameters):
        self.image = image
        self.pnginfo = {'parameters': parameters}

def stealth_write(image, parameters, mode='alpha', compressed=False):
    params = ParamsMock(image, parameters)
    add_data(params, mode, compressed)
    return params.image

def stealth_read(image):
    geninfo, _ = read_info_from_image_stealth(image)
    return geninfo
