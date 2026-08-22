try {
    Get-Content -Raw -Encoding Unicode requirements.txt | Set-Content -Encoding UTF8 requirements.txt
    Write-Output "Converted requirements.txt to UTF-8"
} catch {
    Write-Error "Failed to convert requirements.txt: $_"
}
