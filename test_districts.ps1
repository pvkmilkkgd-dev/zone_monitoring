$region_id = "6e9be0a9-07e4-4150-a0e6-befb15b09618"
$url = "http://localhost:8000/maps/ru/region/$region_id/districts.geojson"

Write-Host "Testing URL: $url"
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Content-Type: $($response.Headers['Content-Type'])"
    Write-Host "Content Length: $($response.Content.Length)"
    
    $json = $response.Content | ConvertFrom-Json
    Write-Host "Type: $($json.type)"
    Write-Host "Features count: $($json.features.Count)"
    Write-Host ""
    
    if ($json.features.Count -gt 0) {
        Write-Host "First 5 districts:"
        for ($i = 0; $i -lt [Math]::Min(5, $json.features.Count); $i++) {
            $feature = $json.features[$i]
            Write-Host "  - $($feature.properties.name) ($($feature.geometry.type))"
        }
    }
} catch {
    Write-Host "Error: $_"
}
