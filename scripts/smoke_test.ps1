param(
    [string]$BaseUrl = "http://127.0.0.1:8010",
    [string]$Username = "admin",
    [string]$Password = "admin123"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

Write-Step "Health check"
$health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get
Write-Host "Health: $($health.status)"

Write-Step "Authenticate"
$tokenResponse = Invoke-RestMethod `
    -Uri "$BaseUrl/auth/token" `
    -Method Post `
    -ContentType "application/x-www-form-urlencoded" `
    -Body "username=$Username&password=$Password"
$token = $tokenResponse.access_token
if (-not $token) {
    throw "Login failed: no access token returned."
}
$authHeaders = @{ Authorization = "Bearer $token" }
Write-Host "Authenticated as $Username"

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$warehouseName = "Smoke Warehouse $stamp"
$sku = "SMOKE-$stamp"

Write-Step "Create warehouse"
$warehouseBody = @{
    name = $warehouseName
    location = "Smoke Test Location"
} | ConvertTo-Json
$warehouse = Invoke-RestMethod `
    -Uri "$BaseUrl/warehouses" `
    -Method Post `
    -ContentType "application/json" `
    -Body $warehouseBody
Write-Host "Warehouse ID: $($warehouse.id)"

Write-Step "Create product"
$productBody = @{
    sku = $sku
    name = "Smoke Test Product"
    quantity_on_hand = 0
    warehouse_id = $warehouse.id
} | ConvertTo-Json
$product = Invoke-RestMethod `
    -Uri "$BaseUrl/products" `
    -Method Post `
    -ContentType "application/json" `
    -Body $productBody
Write-Host "Product ID: $($product.id)"

Write-Step "Stock IN (lot 1)"
$in1Body = @{
    product_id = $product.id
    movement_type = "IN"
    quantity = 10
    note = "Smoke lot 1"
} | ConvertTo-Json
Invoke-RestMethod `
    -Uri "$BaseUrl/stock-movements" `
    -Method Post `
    -Headers $authHeaders `
    -ContentType "application/json" `
    -Body $in1Body | Out-Null

Write-Step "Stock IN (lot 2)"
$in2Body = @{
    product_id = $product.id
    movement_type = "IN"
    quantity = 5
    note = "Smoke lot 2"
} | ConvertTo-Json
Invoke-RestMethod `
    -Uri "$BaseUrl/stock-movements" `
    -Method Post `
    -Headers $authHeaders `
    -ContentType "application/json" `
    -Body $in2Body | Out-Null

Write-Step "Stock OUT (FIFO)"
$outBody = @{
    product_id = $product.id
    movement_type = "OUT"
    quantity = 8
    note = "Smoke dispatch"
} | ConvertTo-Json
Invoke-RestMethod `
    -Uri "$BaseUrl/stock-movements" `
    -Method Post `
    -Headers $authHeaders `
    -ContentType "application/json" `
    -Body $outBody | Out-Null

Write-Step "Check lots endpoint"
$lots = Invoke-RestMethod -Uri "$BaseUrl/products/$($product.id)/lots" -Method Get
Write-Host "Lots returned: $($lots.Count)"

Write-Step "Check filtered movements endpoint"
$movements = Invoke-RestMethod `
    -Uri "$BaseUrl/stock-movements?product_id=$($product.id)" `
    -Method Get `
    -Headers $authHeaders
Write-Host "Movements returned: $($movements.Count)"

Write-Step "Smoke test completed successfully"
