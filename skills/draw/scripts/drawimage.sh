#!/bin/bash
# drawimage.sh
# Usage:
#   ./drawimage.sh "a cute cat wearing sunglasses" "cat.png"
#   ./drawimage.sh "cyberpunk city at night" "cyberpunk.jpg"

set -e

# Default values
PROMPT="${1:-a sunset over mountains}"
OUTPUT="${2:-output.jpg}"
WIDTH="${3:-1024}"
HEIGHT="${4:-768}"
MODEL="${5:-x/z-image-turbo}"
API_URL="${API_URL:-http://mac:11434/api/generate}"

echo "Generating image... Prompt: $PROMPT"
echo "Target file: $OUTPUT"

# Create the JSON payload
BODY=$(jq -n \
  --arg model "$MODEL" \
  --arg prompt "$PROMPT" \
  --argjson width "$WIDTH" \
  --argjson height "$HEIGHT" \
  '{model: $model, prompt: $prompt, width: $width, height: $height, stream: false}')

# Make the API request
RESPONSE=$(curl -s --connect-timeout 10 --max-time 300 \
  -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "$BODY")

# Extract base64 image data from response
IMAGE_DATA=$(echo "$RESPONSE" | jq -r '.image // empty')

if [ -n "$IMAGE_DATA" ] && [[ "$IMAGE_DATA" =~ ^[A-Za-z0-9+/=]+$ ]]; then
    # Decode base64 and save to file
    echo "$IMAGE_DATA" | base64 -d > "$OUTPUT"

    # Get file size
    if command -v stat >/dev/null 2>&1; then
        # macOS uses different stat options
        if [[ "$(uname)" == "Darwin" ]]; then
            SIZE=$(stat -f%z "$OUTPUT" 2>/dev/null || echo "0")
        else
            SIZE=$(stat -c%s "$OUTPUT" 2>/dev/null || echo "0")
        fi
        SIZE_KB=$(awk "BEGIN {printf \"%.2f\", $SIZE/1024}")
        echo "Success! Image saved to: $OUTPUT"
        echo "File size: ${SIZE_KB} KB"
    else
        echo "Success! Image saved to: $OUTPUT"
    fi
else
    echo "Generation failed: No valid image data in response" >&2
    echo "Response: $RESPONSE" >&2
    exit 1
fi
