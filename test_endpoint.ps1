$region_id = "6e9be0a9-07e4-4150-a0e6-befb15b09618"
$url = "http://localhost:8000/api/maps/ru/region/$region_id/boundary.geojson"

Write-Host "Testing URL: $url"
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing
    Write-Host "Status: $($response.StatusCode)"
    Write-Host "Content-Type: $($response.Headers['Content-Type'])"
    Write-Host "Content Length: $($response.Content.Length)"
    
    $json = $response.Content | ConvertFrom-Json
    Write-Host "Type: $($json.type)"
    Write-Host "Features: $($json.features.Count)"
    
    if ($json.features.Count -gt 0) {
        $feature = $json.features[0]
        Write-Host "Feature type: $($feature.type)"
        Write-Host "Geometry type: $($feature.geometry.type)"
        Write-Host "Properties: $($feature.properties | ConvertTo-Json -Compress)"
    }
} catch {
    Write-Host "Error: $_"
}
