#!/bin/bash
# Build NexusOS GUI (Tauri/Electron)

set -e

GUI_DIR="/data/.openclaw/workspace/nexusos-gui"
OUTPUT_DIR="/data/.openclaw/workspace/nexusos-distro/output"

mkdir -p "$OUTPUT_DIR"

echo "=== Building NexusOS GUI ==="

cd "$GUI_DIR"

# Check if npm/node available
if ! command -v npm &> /dev/null; then
    echo "npm not found, using npx..."
    export PATH="$PATH:/usr/local/bin"
fi

# Install dependencies
echo "Installing dependencies..."
npm install

# Build based on framework
if [ -f "package.json" ]; then
    # Check if Tauri
    if grep -q "tauri" package.json; then
        echo "Building Tauri app..."
        npm run tauri build
    else
        # Plain Electron or web app
        echo "Building web app..."
        npm run build
    fi
fi

# Copy built assets
echo "Copying to output..."
mkdir -p "$OUTPUT_DIR/gui"
cp -r dist/* "$OUTPUT_DIR/gui/" 2>/dev/null || cp -r build/* "$OUTPUT_DIR/gui/" 2>/dev/null || true
cp -r src/*.html src/*.css src/*.js "$OUTPUT_DIR/gui/" 2>/dev/null || true

echo "=== GUI Build Complete ==="
ls -la "$OUTPUT_DIR/gui/"
