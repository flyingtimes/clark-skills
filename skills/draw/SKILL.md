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

### Step 2: Configure API Request

Choose the appropriate API based on user preference or available credentials.

**Example:**

```powershell
.\scripts\drawimage.ps1 "<用户给出的画面需求>" "<一个简洁的带输出路径的文件名>"
```

```commandLine
powershell -ExecutionPolicy Bypass -File ".\scripts\drawimage.ps1" "<用户给出的画面需求>" "<一个简洁的带输出路径的文件名>"
```


