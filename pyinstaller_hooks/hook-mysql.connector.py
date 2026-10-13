from PyInstaller.utils.hooks import collect_data_files, collect_submodules


datas = collect_data_files("mysql.connector", includes=["locales/**"])
hiddenimports = collect_submodules("mysql.connector.locales")
