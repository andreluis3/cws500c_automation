from cx_Freeze import setup, Executable
import sys

build_exe_options = {
    "packages": ["tkinter", "serial", "PIL", "matplotlib", "kiwisolver"],  
    "include_files": [("continue.png", "continue.png"), 
        ("continue_lime.png", "continue_lime.png"), 
        ("pause.png", "pause.png"), 
        ("pause_lime.png", "pause_lime.png"), 
        ("play.png", "play.png"), 
        ("play_lime.png", "play_lime.png"), 
        ("stop.png", "stop.png"), 
        ("stop_lime.png", "stop_lime.png")
        ]
    }

# Definição da base para Windows
base = None
if sys.platform == 'win32':
    base = "Win32GUI"

# Configuração do cx_Freeze
setup(
    name="EMTEST-LGE",
    version="20",
    description="Software para controle do geradores EMTEST",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base)]
)
