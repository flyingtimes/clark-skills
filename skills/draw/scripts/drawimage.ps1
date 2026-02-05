# save-ollama-image.ps1
# Usage:
#   .\drawimage.ps1 "a cute cat wearing sunglasses" "cat.png"
#   .\drawimage.ps1 "cyberpunk city at night" "cyberpunk.jpg"

param(
    [Parameter(Mandatory=$false, Position=0)]
    [string]$prompt = "a sunset over mountains",

    [Parameter(Mandatory=$false, Position=1)]
    [string]$output = "output.jpg",

    [Parameter(Mandatory=$false)]
    [int]$width = 1024,

    [Parameter(Mandatory=$false)]
    [int]$height = 768,

    [Parameter(Mandatory=$false)]
    [string]$model = "x/z-image-turbo"
)

$body = @{
    model  = $model
    prompt = $prompt
    width  = $width
    height = $height
    stream = $false
} | ConvertTo-Json -Compress

Write-Host "Generating image... Prompt: $prompt"
Write-Host "Target file: $output"

try {
    $response = Invoke-RestMethod -Uri "http://mac:11434/api/generate" `
                                  -Method Post `
                                  -Body $body `
                                  -ContentType "application/json" `
                                  -TimeoutSec 300

    if ($response.image -and $response.image -match "^[A-Za-z0-9+/=]+$") {
        [IO.File]::WriteAllBytes($output, [Convert]::FromBase64String($response.image))

        $size = "{0:N0} KB" -f ((Get-Item $output).Length / 1KB)
        Write-Host "Success! Image saved to: $output" -ForegroundColor Green
        Write-Host "File size: $size" -ForegroundColor Cyan
    }
    else {
        Write-Host "Generation failed: No valid image data in response" -ForegroundColor Yellow
        Write-Host "Response:" $response | ConvertTo-Json -Depth 3
    }
}
catch {
    Write-Host "Error occurred:" -ForegroundColor Red
    Write-Host $_.Exception.Message
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $errBody = $reader.ReadToEnd()
        Write-Host "Server response:" $errBody -ForegroundColor DarkRed
    }
}
