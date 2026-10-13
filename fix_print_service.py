import os

file_path = r'd:\Python Desktop\POS_V2\application\services\print_service_facade.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

singleton_code = """
_print_service = None

def get_print_service():
    global _print_service
    if _print_service is None:
        _print_service = PrintServiceFacade()
    return _print_service
"""

if "def get_print_service" not in content:
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write("\n" + singleton_code)
    print("Added get_print_service")
