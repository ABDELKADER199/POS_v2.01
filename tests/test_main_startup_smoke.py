import importlib
import os
import sys


def test_main_module_imports_and_exposes_entry_point():
    main_module = importlib.import_module("main")

    assert callable(main_module.main)
    assert main_module.MainWindow is not None
    assert os.path.dirname(os.path.abspath(main_module.__file__)) in sys.path


def test_main_initializes_application_without_opening_real_ui(monkeypatch):
    main_module = importlib.import_module("main")
    events = []

    class FakeApplication:
        def __init__(self, argv):
            events.append(("app_created", argv))

        def setLayoutDirection(self, direction):
            events.append(("layout_direction", direction))

        def setFont(self, font):
            events.append(("font", font.family(), font.pointSize()))

        def setStyle(self, style):
            events.append(("style", style))

        def exec(self):
            events.append(("exec",))
            return 0

    class FakeMainWindow:
        def __init__(self):
            events.append(("window_created",))

        def show(self):
            events.append(("window_shown",))

    def fake_exit(code):
        events.append(("exit", code))
        raise SystemExit(code)

    monkeypatch.setattr(main_module, "QApplication", FakeApplication)
    monkeypatch.setattr(main_module, "MainWindow", FakeMainWindow)
    monkeypatch.setattr(main_module.sys, "exit", fake_exit)

    try:
        main_module.main()
    except SystemExit as exc:
        assert exc.code == 0

    assert events[0][0] == "app_created"
    assert ("font", "Tahoma", 10) in events
    assert ("style", "Fusion") in events
    assert ("window_created",) in events
    assert ("window_shown",) in events
    assert ("exec",) in events
    assert events[-1] == ("exit", 0)
