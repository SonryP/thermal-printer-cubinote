# pyinstaller build for the single-file windows exe:
#     pyinstaller --noconfirm thermal-printer.spec
# the result lands in dist/ThermalPrinter.exe. config.yaml, the gallery and
# thermal-printer.log are written next to the exe at runtime.

from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ["src/main.py"],
    pathex=["."],
    # customtkinter loads its themes from json files at runtime, and the
    # unicode fallback font ships with the project
    datas=collect_data_files("customtkinter") + [("fonts", "fonts")],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="ThermalPrinter",
    console=False,
    upx=False,
)
