
#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

if [ -f HackMIT/bin/activate ]; then
  source HackMIT/bin/activate
fi

python -m pip install --upgrade pip wheel >/dev/null
pip install -q pyinstaller

# Use the generated spec to include Info.plist permissions and icon
pyinstaller --noconfirm EasyDJ.spec

echo "\nApp built at: dist/EasyDJ.app"

