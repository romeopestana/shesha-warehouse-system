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

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$warehouse = Invoke-RestMethod `
    -Uri "$BaseUrl/warehouses" `
    -Method Post `
    -ContentType "application/json" `
    -Body (@{ name = "Alerts Warehouse $stamp"; location = "Vienna" } | ConvertTo-Json)

Write-Step "Create low-stock product"
$product = Invoke-RestMethod `
    -Uri "$BaseUrl/products" `
    -Method Post `
    -Headers $authHeaders `
    -ContentType "application/json" `
    -Body (@{
        sku = "ALERT-$stamp"
        name = "Alerts Smoke Product"
        warehouse_id = $warehouse.id
        quantity_on_hand = 1
        reorder_level = 5
        reorder_quantity = 10
    } | ConvertTo-Json)

Write-Step "Check low-stock alerts"
$alerts = Invoke-RestMethod `
    -Uri "$BaseUrl/alerts/low-stock?warehouse_id=$($warehouse.id)" `
    -Method Get `
    -Headers $authHeaders
if (-not ($alerts | Where-Object { $_.product_id -eq $product.id })) {
    throw "Expected low-stock product not found in /alerts/low-stock."
}

Write-Step "Check summary endpoint"
$summary = Invoke-RestMethod `
    -Uri "$BaseUrl/alerts/summary" `
    -Method Get `
    -Headers $authHeaders
if ($summary.total_low_stock_items -lt 1) {
    throw "Expected at least one low-stock item in /alerts/summary."
}

Write-Step "Alerts smoke test completed successfully"
