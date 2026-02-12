---
name: draw
description: Use when the user wants to generate images through an API.
---

# Draw Skill

Generate images through APIs using curl and save them to specified or default directories.

## Overview

This skill provides a standardized approach to generating images via API calls (ollama z-image-turbo model) and saving them to disk with proper directory handling.

## When to Use

- User asks to generate or create an image
- User mentions AI art, image generation, or drawing
- User wants to save an image from an API response

## Quick Reference

| User Input | Action |
|------------|--------|
| Generate image of X | Use configured API to generate, save to default or specified path |
| Save to /path/to/dir | Use that path, create if missing |
| No path specified | Use `<project-root>/assets/`, create if missing |


## Implementation

### Step 1: Determine Output Directory

```bash
# Check if user specified a directory
# If not, use project-root/assets/

PROJECT_ROOT=$(pwd)
OUTPUT_DIR="${USER_DIR:-$PROJECT_ROOT/assets}"

# Create directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"
```

### Step 2: Detect OS and Choose Script

Detect the operating system and use the appropriate script:

```bash
# Detect OS
OS_TYPE=$(uname)

if [[ "$OS_TYPE" == "Darwin" ]]; then
    # macOS
    SCRIPT="./scripts/drawimage.sh"
elif [[ "$OS_TYPE" == "Linux" ]]; then
    # Linux
    SCRIPT="./scripts/drawimage.sh"
else
    # Windows (Git Bash, WSL, or native Windows)
    # Try PowerShell first
    SCRIPT="powershell -ExecutionPolicy Bypass -File ./scripts/drawimage.ps1"
fi
```

### Step 3: Execute Image Generation

**For macOS / Linux:**

```bash
./scripts/drawimage.sh "<prompt>" "<output-path>"
```

**For Windows:**

```powershell
.\scripts\drawimage.ps1 "<prompt>" "<output-path>"
```

**Cross-platform command (works in Git Bash/WSL on Windows):**

```bash
if [[ "$(uname)" == "Darwin" ]] || [[ "$(uname)" == "Linux" ]]; then
    ./scripts/drawimage.sh "$PROMPT" "$OUTPUT_FILE"
else
    powershell -ExecutionPolicy Bypass -File "./scripts/drawimage.ps1" "$PROMPT" "$OUTPUT_FILE"
fi
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `prompt` | Image description/text prompt | "a sunset over mountains" |
| `output` | Output file path (with extension) | "output.jpg" |
| `width` | Image width in pixels | 1024 |
| `height` | Image height in pixels | 768 |
| `model` | AI model to use | "x/z-image-turbo" |


