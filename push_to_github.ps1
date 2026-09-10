# AURA 3D Learning Lab - GitHub Push Helper
$GitExe = "C:\Users\Ashwin Chikkala\.gemini\antigravity-ide\brain\53d5853a-9cc8-4bf4-aeb7-8fe1e6628e1e\scratch\mingit\cmd\git.exe"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Pushing AURA 3D Learning Lab to GitHub" -ForegroundColor Cyan
Write-Host " Target: https://github.com/Ash17abd/aura-project" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

& $GitExe branch -M main
& $GitExe push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] Code successfully pushed to GitHub!" -ForegroundColor Green
    Write-Host "You can now connect this repo to Render.com for 24/7 cloud hosting." -ForegroundColor Green
} else {
    Write-Host "`n[NOTE] If prompted for password, use a GitHub Personal Access Token (classic) with 'repo' scope." -ForegroundColor Yellow
}
