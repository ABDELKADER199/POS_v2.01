"""
HyperPOS Developer Builder package.

Clean-architecture split:
    config          – static labels, edition presets, validation rules
    build_worker    – background thread that drives PyInstaller
    builder_window  – the main Qt window (UI + orchestration)
"""
