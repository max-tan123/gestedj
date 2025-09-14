
#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

if [ -f HackMIT/bin/activate ]; then
  source HackMIT/bin/activate
fi

python -m pip install --upgrade pip wheel >/dev/null
pip install -q pyinstaller

# Generate a rounded macOS icon from the project PNG (squircle)
if [ -f gestedj_logo1.png ]; then
  python utils/make_macos_icon.py gestedj_logo1.png --out gestedj_logo1.icns >/dev/null
fi

# Use the generated spec to include Info.plist permissions and icon
pyinstaller --noconfirm GesteDJ.spec

echo "\nApp built at: dist/GesteDJ.app"

