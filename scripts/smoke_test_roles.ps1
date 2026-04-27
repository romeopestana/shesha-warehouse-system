param(
    [string]$BaseUrl = "http://127.0.0.1:8010",
    [string]$AdminUsername = "admin",
    [string]$AdminPassword = "admin123",
    [string]$ClerkUsername = "clerk",
    [string]$ClerkPassword = "clerk123"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Get-Token {
    param(
        [string]$Username,
        [string]$Password
    )
    $response = Invoke-RestMethod `
        -Uri "$BaseUrl/auth/token" `
        -Method Post `
        -ContentType "application/x-www-form-urlencoded" `
        -Body "username=$Username&password=$Password"
    if (-not $response.access_token) {
        throw "No token returned for user '$Username'."
    }
    return $response.access_token
}

function Assert-HttpStatus {
    param(
        [scriptblock]$Request,
        [int]$ExpectedStatus,
        [string]$Description
    )

    try {
        & $Request | Out-Null
        if ($ExpectedStatus -ne 200) {
            throw "$Description expected HTTP $ExpectedStatus but request succeeded."
        }
        Write-Host "$Description => HTTP 200 (as expected)"
    }
    catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($null -eq $statusCode) {
            throw
        }
        if ($statusCode -ne $ExpectedStatus) {
            throw "$Description expected HTTP $ExpectedStatus but got HTTP $statusCode"
        }
        Write-Host "$Description => HTTP $statusCode (as expected)"
    }
}

Write-Step "Get admin and clerk tokens"
$adminToken = Get-Token -Username $AdminUsername -Password $AdminPassword
$clerkToken = Get-Token -Username $ClerkUsername -Password $ClerkPassword
$adminHeaders = @{ Authorization = "Bearer $adminToken" }
$clerkHeaders = @{ Authorization = "Bearer $clerkToken" }

$stamp = Get-Date -Format "yyyyMMddHHmmss"
$warehouseName = "Roles Warehouse $stamp"
$sku = "ROLES-$stamp"

Write-Step "Create test warehouse and product as admin"
$warehouse = Invoke-RestMethod `
    -Uri "$BaseUrl/warehouses" `
    -Method Post `
    -ContentType "application/json" `
    -Body (@{ name = $warehouseName; location = "Roles Test" } | ConvertTo-Json)
$product = Invoke-RestMethod `
    -Uri "$BaseUrl/products" `
    -Method Post `
    -ContentType "application/json" `
    -Body (@{
        sku = $sku
        name = "Roles Test Product"
        quantity_on_hand = 0
        warehouse_id = $warehouse.id
    } | ConvertTo-Json)

Write-Step "Admin stocks product IN (setup for clerk read)"
Invoke-RestMethod `
    -Uri "$BaseUrl/stock-movements" `
    -Method Post `
    -Headers $adminHeaders `
    -ContentType "application/json" `
    -Body (@{
        product_id = $product.id
        movement_type = "IN"
        quantity = 10
        note = "Role test setup"
    } | ConvertTo-Json) | Out-Null

Write-Step "Verify clerk can GET stock movements (HTTP 200)"
Assert-HttpStatus `
    -ExpectedStatus 200 `
    -Description "Clerk GET /stock-movements" `
    -Request {
        Invoke-RestMethod `
            -Uri "$BaseUrl/stock-movements?product_id=$($product.id)" `
            -Method Get `
            -Headers $clerkHeaders
    }

Write-Step "Verify clerk cannot POST stock movements (HTTP 403)"
Assert-HttpStatus `
    -ExpectedStatus 403 `
    -Description "Clerk POST /stock-movements" `
    -Request {
        Invoke-RestMethod `
            -Uri "$BaseUrl/stock-movements" `
            -Method Post `
            -Headers $clerkHeaders `
            -ContentType "application/json" `
            -Body (@{
                product_id = $product.id
                movement_type = "OUT"
                quantity = 1
                note = "Forbidden clerk attempt"
            } | ConvertTo-Json)
    }

Write-Step "Role guard smoke test completed successfully"
