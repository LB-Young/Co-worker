import streamlit.web.cli as stcli
import sys
from pathlib import Path

if __name__ == "__main__":
    frontend_path = str(Path(__file__).parent / "frontend" / "app.py")
    sys.argv = ["streamlit", "run", frontend_path]
    sys.exit(stcli.main())
