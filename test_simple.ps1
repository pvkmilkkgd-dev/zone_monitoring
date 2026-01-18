try {
    Write-Host "Test 1: /maps/ru/region/.../boundary.geojson"
    $r1 = Invoke-WebRequest -Uri "http://localhost:8000/maps/ru/region/6e9be0a9-07e4-4150-a0e6-befb15b09618/boundary.geojson" -UseBasicParsing
    Write-Host "Status: $($r1.StatusCode), Length: $($r1.Content.Length)"
} catch {
    Write-Host "Error: $_"
}

Write-Host ""

try {
    Write-Host "Test 2: /api/maps/ru/region/.../boundary.geojson"
    $r2 = Invoke-WebRequest -Uri "http://localhost:8000/api/maps/ru/region/6e9be0a9-07e4-4150-a0e6-befb15b09618/boundary.geojson" -UseBasicParsing
    Write-Host "Status: $($r2.StatusCode), Length: $($r2.Content.Length)"
} catch {
    Write-Host "Error: $_"
}
