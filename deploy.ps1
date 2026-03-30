(Get-Content .gitignore) -notmatch '^licensing/' | Set-Content .gitignore
railway up --detach
Copy-Item .gitignore.bak .gitignore
Write-Host "Deploy done"
