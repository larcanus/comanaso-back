# Конфигурация
$BASE_URL = "http://localhost:8000/api"
$HEADERS = @{
    "Content-Type" = "application/json"
}

function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Info { Write-Host $args -ForegroundColor Cyan }

function Show-Response {
    param($Response, $StatusCode)
    Write-Info "`nStatus Code: $StatusCode"
    Write-Info "Response:"
    $Response | ConvertTo-Json -Depth 10 | Write-Host
}

function Cleanup-TestUsers {
    Write-Info "`n=== CLEANUP: Removing test users ==="
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/dev/cleanup/test-users" -Method Delete -Headers $HEADERS -StatusCodeVariable statusCode
        Write-Success "✓ Cleanup successful"
        Show-Response $response $statusCode
    }
    catch {
        Write-Error "✗ Cleanup failed (this is OK if no test users exist)"
        Write-Host $_.Exception.Message
    }
}

function Test-Register {
    Write-Info "`n=== TEST: Register User ==="
    $body = @{
        login = "test@example.com"
        password = "Password123"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Success "✓ Registration successful"
        Show-Response $response $statusCode
        return $response
    }
    catch {
        Write-Error "✗ Registration failed"
        Write-Host $_.Exception.Message
        return $null
    }
}

function Test-Login {
    Write-Info "`n=== TEST: Login User ==="
    $body = @{
        login = "test@example.com"
        password = "Password123"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Success "✓ Login successful"
        Show-Response $response $statusCode
        return $response.access_token
    }
    catch {
        Write-Error "✗ Login failed"
        Write-Host $_.Exception.Message
        return $null
    }
}

function Test-GetMe {
    param($Token)
    Write-Info "`n=== TEST: Get Current User ==="
    if (-not $Token) { Write-Error "✗ No token provided"; return }
    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer $Token"
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/me" -Method Get -Headers $authHeaders -StatusCodeVariable statusCode
        Write-Success "✓ Get user info successful"
        Show-Response $response $statusCode
        return $response
    }
    catch {
        Write-Error "✗ Get user info failed"
        Write-Host $_.Exception.Message
        return $null
    }
}

function Test-InvalidLogin {
    Write-Info "`n=== TEST: Invalid Login ==="
    $body = @{
        login = "test@example.com"
        password = "wrongpassword"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected invalid credentials"
        Write-Host "Error: $($_.Exception.Message)"
    }
}

function Test-DuplicateLogin {
    Write-Info "`n=== TEST: Duplicate Login ==="
    $body = @{
        login = "test@example.com"
        password = "Password123"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected duplicate login"
        Write-Host "Error: $($_.Exception.Message)"
    }
}

function Test-InvalidToken {
    Write-Info "`n=== TEST: Invalid Token ==="
    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer invalid_token_12345"
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/me" -Method Get -Headers $authHeaders -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected invalid token"
        Write-Host "Error: $($_.Exception.Message)"
    }
}

function Run-AllTests {
    Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║   COMANASO AUTH API TESTS              ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Yellow

    # Очистка перед тестами
    Cleanup-TestUsers
    Start-Sleep -Seconds 1

    # Основные тесты
    $user = Test-Register; Start-Sleep -Seconds 1
    $token = Test-Login; Start-Sleep -Seconds 1
    if ($token) { Test-GetMe -Token $token; Start-Sleep -Seconds 1 }
    Test-InvalidLogin; Start-Sleep -Seconds 1
    Test-DuplicateLogin; Start-Sleep -Seconds 1
    Test-InvalidToken

    Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║   TESTS COMPLETED                      ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Yellow
}

function Show-Menu {
    Write-Host "`n=== COMANASO AUTH API TESTER ===" -ForegroundColor Yellow
    Write-Host "1. Run All Tests"
    Write-Host "2. Test Register"
    Write-Host "3. Test Login"
    Write-Host "4. Test Get Me (requires token)"
    Write-Host "5. Test Invalid Login"
    Write-Host "6. Test Duplicate Login"
    Write-Host "7. Test Invalid Token"
    Write-Host "8. Cleanup Test Users"
    Write-Host "0. Exit"
    Write-Host ""
}

if ($args.Count -eq 0) {
    $token = $null
    do {
        Show-Menu
        $choice = Read-Host "Select option"
        switch ($choice) {
            "1" { Run-AllTests }
            "2" { Test-Register }
            "3" { $token = Test-Login }
            "4" { if (-not $token) { $token = Read-Host "Enter token" }; Test-GetMe -Token $token }
            "5" { Test-InvalidLogin }
            "6" { Test-DuplicateLogin }
            "7" { Test-InvalidToken }
            "8" { Cleanup-TestUsers }
            "0" { Write-Host "Exiting..." }
            default { Write-Host "Invalid option" -ForegroundColor Red }
        }
        if ($choice -ne "0") { Read-Host "`nPress Enter to continue" }
    } while ($choice -ne "0")
}
else {
    Run-AllTests
}
