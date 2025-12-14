# fix_views.ps1
# Usage:
# 1. Open PowerShell, navigate to the module folder (where the "views" folder is).
#    e.g. cd "C:\Program Files\Odoo 18.0e\server\odoo\addons\kandil_real_estate"
# 2. Optionally allow running this script for this session:
#    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
# 3. Run: .\fix_views.ps1

# Backup views folder first
$viewsPath = ".\views"
$backupPath = Join-Path $viewsPath "backup_$(Get-Date -Format yyyyMMdd_HHmmss)"
New-Item -ItemType Directory -Path $backupPath -Force | Out-Null
Copy-Item -Path (Join-Path $viewsPath "*.xml") -Destination $backupPath -Force

Write-Output "Backup of views created at: $backupPath"

# Process each xml file in views
Get-ChildItem -Path .\views\*.xml -Recurse | ForEach-Object {
    $path = $_.FullName
    $text = Get-Content $path -Raw

    # Replace <tree> with <list> and closing tags
    $text = $text -replace '<\s*tree\b', '<list'
    $text = $text -replace '</\s*tree\s*>', '</list>'

    # Replace view_mode occurrences and tree,form -> list,form
    $text = $text -replace 'view_mode\s*=\s*"(?:tree,form|form,tree|tree|list)"', 'view_mode="list,form"'
    $text = $text -replace 'tree,form','list,form'

    # Ensure file saved as UTF8 without BOM
    [System.IO.File]::WriteAllText($path, $text, [System.Text.Encoding]::UTF8)
    Write-Output "Fixed: $path"
}

Write-Output "Done. Please remove .pyc/__pycache__ if present, restart Odoo service, Update Apps List, then try installing/upgrading the module."
