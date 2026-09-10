param(
    [string]$Token = ""
)

# AURA 3D Learning Lab - GitHub Push Helper (Headless & Interactive)
$GitExe = "C:\Users\Ashwin Chikkala\.gemini\antigravity-ide\brain\53d5853a-9cc8-4bf4-aeb7-8fe1e6628e1e\scratch\mingit\cmd\git.exe"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Pushing AURA 3D Learning Lab to GitHub" -ForegroundColor Cyan
Write-Host " Target: https://github.com/Ash17abd/aura-project" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

& $GitExe branch -M main

if ($Token -ne "") {
    Write-Host "[INFO] Using headless GitHub token for automated deployment..." -ForegroundColor Green
    $RemoteUrl = "https://x-access-token:${Token}@github.com/Ash17abd/aura-project.git"
    & $GitExe push $RemoteUrl main --force
} else {
    Write-Host "[INFO] Pushing with standard Git credentials..." -ForegroundColor Yellow
    & $GitExe push -u origin main --force
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] Code successfully pushed to GitHub repository!" -ForegroundColor Green
    Write-Host "Your repository is now updated with the uncompressed production codebase." -ForegroundColor Green
    Write-Host "You can now link it to 24/7 cloud container platforms (Koyeb / Hugging Face Spaces)." -ForegroundColor Cyan
} else {
    Write-Host "`n[NOTE] If authentication fails, pass your GitHub token directly for headless push:" -ForegroundColor Yellow
    Write-Host "       .\push_to_github.ps1 -Token 'ghp_YOUR_TOKEN'" -ForegroundColor White
}
