from PyQt6.QtWidgets import QApplication, QLabel


def main() -> int:
    app = QApplication([])
    window = QLabel("QtWidgets import succeeded")
    window.resize(360, 80)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
