$ErrorActionPreference = "Stop"

$apiUrl = if ($env:API_URL) { $env:API_URL } else { "http://localhost:8000" }
$webUrl = if ($env:WEB_URL) { $env:WEB_URL } else { "http://localhost:8080" }

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Starting ShopLite End-to-End Smoke Test Suite (PowerShell)" -ForegroundColor Cyan
Write-Host " Target API: $apiUrl"
Write-Host " Target Web: $webUrl"
Write-Host "=========================================================="

# 1. Probe /readyz
Write-Host "`n[Step 1/5] Waiting for API readiness (/readyz)..." -ForegroundColor Yellow
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $res = Invoke-RestMethod -Uri "$apiUrl/readyz" -Method Get -TimeoutSec 3
        if ($res.status -eq "ready") {
            Write-Host " -> API is READY (status: ready, db: $($res.database), redis: $($res.redis))" -ForegroundColor Green
            $ready = $true
            break
        }
    } catch {
        Write-Host " -> Attempt $i/30: waiting for readyz..."
    }
    Start-Sleep -Seconds 2
}

if (-not $ready) {
    Write-Error "FAIL: API failed to report readiness within 60s"
    exit 1
}

# 2. Probe Web
Write-Host "`n[Step 2/5] Probing Web Frontend ($webUrl)..." -ForegroundColor Yellow
try {
    $webRes = Invoke-WebRequest -Uri $webUrl -Method Get -UseBasicParsing -TimeoutSec 5
    if ($webRes.StatusCode -eq 200) {
        Write-Host " -> Frontend is healthy (HTTP 200)" -ForegroundColor Green
    }
} catch {
    Write-Error "FAIL: Frontend unreachable: $_"
    exit 1
}

# 3. Check products
Write-Host "`n[Step 3/5] Verifying catalog seeding (>= 10 products)..." -ForegroundColor Yellow
$products = Invoke-RestMethod -Uri "$apiUrl/products" -Method Get
Write-Host " -> Found $($products.Count) products in database" -ForegroundColor Cyan
if ($products.Count -lt 10) {
    Write-Error "FAIL: Expected >= 10 seeded products, got $($products.Count)"
    exit 1
}
Write-Host " -> PASS: Catalog successfully seeded with $($products.Count) products." -ForegroundColor Green

# 4. Place order
Write-Host "`n[Step 4/5] Placing test order (product_id=1, quantity=2)..." -ForegroundColor Yellow
$orderBody = @{ product_id = 1; quantity = 2 } | ConvertTo-Json
$order = Invoke-RestMethod -Uri "$apiUrl/orders" -Method Post -Body $orderBody -ContentType "application/json"
$orderId = $order.id
Write-Host " -> Order successfully created with ID #$orderId (status: $($order.status))" -ForegroundColor Green

# 5. Poll order
Write-Host "`n[Step 5/5] Polling Order #$orderId for completion by order-worker..." -ForegroundColor Yellow
$completed = $false
for ($i = 1; $i -le 20; $i++) {
    Start-Sleep -Seconds 1
    $statusCheck = Invoke-RestMethod -Uri "$apiUrl/orders/$orderId" -Method Get
    Write-Host " -> Polling [$i/20]: Status is '$($statusCheck.status)'"
    if ($statusCheck.status -eq "COMPLETED") {
        $completed = $true
        break
    }
}

if (-not $completed) {
    Write-Error "FAIL: Order #$orderId did not reach COMPLETED within 20s"
    exit 1
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host " ALL SMOKE TESTS PASSED CLEANLY! Stack is 100% Verified." -ForegroundColor Green
Write-Host "=========================================================="
