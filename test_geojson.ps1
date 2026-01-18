$response = Invoke-WebRequest -Uri "http://localhost:8000/maps/ru/region/6e9be0a9-07e4-4150-a0e6-befb15b09618/districts.geojson" -Method GET -TimeoutSec 5
$json = $response.Content | ConvertFrom-Json
Write-Host "Features count: $($json.features.Count)"
Write-Host "First 5 districts:"
$json.features | Select-Object -First 5 | ForEach-Object { Write-Host "  - $($_.properties.name)" }
