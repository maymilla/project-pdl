$CouchUser = $env:COUCH_USER
$CouchPass = $env:COUCH_PASSWORD
$CouchHost = "http://localhost:5984"
$Db = "gayang"

$pair = "$($CouchUser):$($CouchPass)"
$bytes = [System.Text.Encoding]::ASCII.GetBytes($pair)
$base64 = [System.Convert]::ToBase64String($bytes)
$Headers = @{ Authorization = "Basic $base64" }

$ErrorActionPreference = "Stop"

Write-Host "Waiting for CouchDB..."
do {
    try {
        Invoke-RestMethod -Uri "$CouchHost/" -Method Get -Headers $Headers | Out-Null
        $ready = $true
    } catch {
        Start-Sleep -Seconds 1
        $ready = $false
    }
} until ($ready)

Write-Host "Creating database..."
try {
    Invoke-RestMethod -Uri "$CouchHost/$Db" -Method Put -Headers $Headers
    Write-Host "DB created or already exists"
} catch {
    Write-Host "DB creation error: $($_.Exception.Message)"
}

Write-Host "Creating Mango indexes..."
$indexes = Get-Content "indexes.json" | ConvertFrom-Json
foreach ($idx in $indexes) {
    $body = $idx | ConvertTo-Json -Depth 5
    Invoke-RestMethod -Uri "$CouchHost/$Db/_index" -Method Post -Body $body -ContentType "application/json" -Headers $Headers
}

Write-Host "Creating views design doc..."
$viewsBody = Get-Content "views.json" -Raw
try {
    Invoke-RestMethod -Uri "$CouchHost/$Db/_design/views" -Method Put -Body $viewsBody -ContentType "application/json" -Headers $Headers
} catch {
    $existing = Invoke-RestMethod -Uri "$CouchHost/$Db/_design/views" -Method Get -Headers $Headers
    $rev = $existing._rev
    Invoke-RestMethod -Uri "$CouchHost/$Db/_design/views?rev=$rev" -Method Put -Body $viewsBody -ContentType "application/json" -Headers $Headers
}

Write-Host "Done."