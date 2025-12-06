# Конфигурация
$BASE_URL = "http://localhost:8000/api"
$HEADERS = @{
    "Content-Type" = "application/json"
}

function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }

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
        return $response.token
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

function Test-VerifyToken {
    param($Token)
    Write-Info "`n=== TEST: Verify Valid Token ==="
    if (-not $Token) { Write-Error "✗ No token provided"; return $null }

    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer $Token"

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/verify" -Method Get -Headers $authHeaders -StatusCodeVariable statusCode
        Write-Success "✓ Token verification successful"
        Show-Response $response $statusCode

        # Проверка структуры ответа
        if ($response.valid -eq $true -and $response.user.id -and $response.user.login) {
            Write-Success "✓ Response structure is correct"
        } else {
            Write-Error "✗ Response structure is incorrect"
        }

        return $response
    }
    catch {
        Write-Error "✗ Token verification failed"
        Write-Host $_.Exception.Message
        return $null
    }
}

function Test-VerifyInvalidToken {
    Write-Info "`n=== TEST: Verify Invalid Token ==="
    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer invalid_token_xyz123"

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/verify" -Method Get -Headers $authHeaders -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected invalid token"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        # Проверка структуры ошибки (401 возвращает detail с вложенным error)
        $errorCode = if ($errorDetails.detail -and $errorDetails.detail.error) {
            $errorDetails.detail.error
        } elseif ($errorDetails.error) {
            $errorDetails.error
        } else {
            $null
        }

        if ($errorCode -eq "INVALID_TOKEN") {
            Write-Success "✓ Error code is correct (INVALID_TOKEN)"
        } else {
            Write-Error "✗ Expected error code INVALID_TOKEN, got: $errorCode"
            Write-Warning "⚠ API response structure differs from contract (detail wrapper present)"
        }
    }
}

function Test-VerifyWithoutToken {
    Write-Info "`n=== TEST: Verify Without Token ==="

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/verify" -Method Get -Headers $HEADERS -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected request without token"
        Write-Host "Error: $($_.Exception.Message)"
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
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        # Проверка структуры ошибки (может быть вложенной в detail)
        $errorCode = if ($errorDetails.detail -and $errorDetails.detail.error) {
            $errorDetails.detail.error
        } elseif ($errorDetails.error) {
            $errorDetails.error
        } else {
            $null
        }

        if ($errorCode -eq "INVALID_CREDENTIALS") {
            Write-Success "✓ Error code is correct (INVALID_CREDENTIALS)"
        } else {
            Write-Error "✗ Expected error code INVALID_CREDENTIALS, got: $errorCode"
        }

        # Проверка соответствия контракту API
        if ($errorDetails.detail) {
            Write-Warning "⚠ API response structure differs from contract (detail wrapper present)"
        }
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
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        # Проверка структуры ошибки (может быть вложенной в detail)
        $errorCode = if ($errorDetails.detail -and $errorDetails.detail.error) {
            $errorDetails.detail.error
        } elseif ($errorDetails.error) {
            $errorDetails.error
        } else {
            $null
        }

        if ($errorCode -eq "USER_EXISTS") {
            Write-Success "✓ Error code is correct (USER_EXISTS)"
        } else {
            Write-Error "✗ Expected error code USER_EXISTS, got: $errorCode"
        }

        # Проверка соответствия контракту API
        if ($errorDetails.detail) {
            Write-Warning "⚠ API response structure differs from contract (detail wrapper present)"
        }
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

# ============================================
# НОВЫЕ ТЕСТЫ ВАЛИДАЦИИ
# ============================================

function Test-RegisterShortLogin {
    Write-Info "`n=== TEST: Register with Short Login (< 3 chars) ==="
    $body = @{
        login = "ab"
        password = "Password123"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected short login"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        # Для валидации (422) ответ плоский без detail
        if ($errorDetails.error -eq "VALIDATION_ERROR") {
            Write-Success "✓ Error code is correct (VALIDATION_ERROR)"
        } else {
            Write-Error "✗ Expected error code VALIDATION_ERROR, got: $($errorDetails.error)"
        }
    }
}

function Test-RegisterLongLogin {
    Write-Info "`n=== TEST: Register with Long Login (> 50 chars) ==="
    $body = @{
        login = "a" * 51
        password = "Password123"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected long login"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        if ($errorDetails.error -eq "VALIDATION_ERROR") {
            Write-Success "✓ Error code is correct (VALIDATION_ERROR)"
        } else {
            Write-Error "✗ Expected error code VALIDATION_ERROR, got: $($errorDetails.error)"
        }
    }
}

function Test-RegisterShortPassword {
    Write-Info "`n=== TEST: Register with Short Password (< 6 chars) ==="
    $body = @{
        login = "validuser@test.com"
        password = "12345"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected short password"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        if ($errorDetails.error -eq "VALIDATION_ERROR" -and $errorDetails.message -match "минимум 6 символов|at least 6 characters") {
            Write-Success "✓ Error message is correct"
        } else {
            Write-Error "✗ Expected password length error message"
        }
    }
}

function Test-RegisterEmptyLogin {
    Write-Info "`n=== TEST: Register with Empty Login ==="
    $body = @{
        login = ""
        password = "Password123"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected empty login"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        if ($errorDetails.error -eq "VALIDATION_ERROR") {
            Write-Success "✓ Error code is correct"
        }
    }
}

function Test-RegisterEmptyPassword {
    Write-Info "`n=== TEST: Register with Empty Password ==="
    $body = @{
        login = "validuser@test.com"
        password = ""
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected empty password"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        if ($errorDetails.error -eq "VALIDATION_ERROR") {
            Write-Success "✓ Error code is correct"
        }
    }
}

function Test-RegisterMissingFields {
    Write-Info "`n=== TEST: Register with Missing Fields ==="
    $body = @{
        login = "validuser@test.com"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected missing password field"
        Write-Info "Error: $($_.Exception.Message)"
    }
}

function Test-LoginNonExistentUser {
    Write-Info "`n=== TEST: Login with Non-Existent User ==="
    $body = @{
        login = "nonexistent@example.com"
        password = "Password123"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected non-existent user"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        # Проверка структуры ошибки (может быть вложенной в detail)
        $errorCode = if ($errorDetails.detail -and $errorDetails.detail.error) {
            $errorDetails.detail.error
        } elseif ($errorDetails.error) {
            $errorDetails.error
        } else {
            $null
        }

        if ($errorCode -eq "INVALID_CREDENTIALS") {
            Write-Success "✓ Error code is correct (INVALID_CREDENTIALS)"
        } else {
            Write-Error "✗ Expected error code INVALID_CREDENTIALS, got: $errorCode"
        }

        # Проверка соответствия контракту API
        if ($errorDetails.detail) {
            Write-Warning "⚠ API response structure differs from contract (detail wrapper present)"
        }
    }
}

function Test-LoginEmptyCredentials {
    Write-Info "`n=== TEST: Login with Empty Credentials ==="
    $body = @{
        login = ""
        password = ""
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected empty credentials"
        Write-Info "Error: $($_.Exception.Message)"
    }
}

function Test-LoginMissingFields {
    Write-Info "`n=== TEST: Login with Missing Password ==="
    $body = @{
        login = "test@example.com"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected missing password"
        Write-Info "Error: $($_.Exception.Message)"
    }
}

function Test-InvalidJSON {
    Write-Info "`n=== TEST: Register with Invalid JSON ==="
    $body = "{invalid json}"
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected invalid JSON"
        Write-Info "Error: $($_.Exception.Message)"
    }
}

function Test-RegisterBoundaryLogin {
    Write-Info "`n=== TEST: Register with Boundary Login (3 chars) ==="
    $body = @{
        login = "abc"
        password = "Password123"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Success "✓ Registration with 3-char login successful (boundary test)"
        Show-Response $response $statusCode
        return $response
    }
    catch {
        Write-Error "✗ Registration failed (3 chars should be valid)"
        Write-Host $_.Exception.Message
        return $null
    }
}

function Test-RegisterBoundaryPassword {
    Write-Info "`n=== TEST: Register with Boundary Password (6 chars) ==="
    $body = @{
        login = "boundary@test.com"
        password = "Pass12"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Success "✓ Registration with 6-char password successful (boundary test)"
        Show-Response $response $statusCode
        return $response
    }
    catch {
        Write-Error "✗ Registration failed (6 chars should be valid)"
        Write-Host $_.Exception.Message
        return $null
    }
}

function Run-AllTests {
    Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║   COMANASO AUTH API TESTS              ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Yellow

    # Очистка перед тестами
    Cleanup-TestUsers
    Start-Sleep -Seconds 1

    Write-Host "`n=== POSITIVE TESTS ===" -ForegroundColor Yellow
    # Основные позитивные тесты
    $user = Test-Register; Start-Sleep -Seconds 1
    $token = Test-Login; Start-Sleep -Seconds 1

    # Тесты с валидным токеном
    if ($token) {
        Test-GetMe -Token $token; Start-Sleep -Seconds 1
        Test-VerifyToken -Token $token; Start-Sleep -Seconds 1
    }

    Write-Host "`n=== VALIDATION TESTS (422) ===" -ForegroundColor Yellow
    # Тесты валидации регистрации
    Test-RegisterShortLogin; Start-Sleep -Seconds 1
    Test-RegisterLongLogin; Start-Sleep -Seconds 1
    Test-RegisterShortPassword; Start-Sleep -Seconds 1
    Test-RegisterEmptyLogin; Start-Sleep -Seconds 1
    Test-RegisterEmptyPassword; Start-Sleep -Seconds 1
    Test-RegisterMissingFields; Start-Sleep -Seconds 1

    Write-Host "`n=== AUTHENTICATION TESTS (401) ===" -ForegroundColor Yellow
    # Тесты аутентификации
    Test-InvalidLogin; Start-Sleep -Seconds 1
    Test-LoginNonExistentUser; Start-Sleep -Seconds 1
    Test-LoginEmptyCredentials; Start-Sleep -Seconds 1
    Test-LoginMissingFields; Start-Sleep -Seconds 1

    Write-Host "`n=== AUTHORIZATION TESTS (401) ===" -ForegroundColor Yellow
    # Тесты авторизации
    Test-InvalidToken; Start-Sleep -Seconds 1
    Test-VerifyInvalidToken; Start-Sleep -Seconds 1
    Test-VerifyWithoutToken; Start-Sleep -Seconds 1

    Write-Host "`n=== DUPLICATE & EDGE CASES ===" -ForegroundColor Yellow
    # Дубликаты и граничные случаи
    Test-DuplicateLogin; Start-Sleep -Seconds 1
    Test-InvalidJSON; Start-Sleep -Seconds 1

    Write-Host "`n=== BOUNDARY TESTS ===" -ForegroundColor Yellow
    # Граничные значения (должны пройти)
    Test-RegisterBoundaryLogin; Start-Sleep -Seconds 1
    Test-RegisterBoundaryPassword; Start-Sleep -Seconds 1

    Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║   TESTS COMPLETED                      ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Yellow
}

function Show-Menu {
    Write-Host "`n=== COMANASO AUTH API TESTER ===" -ForegroundColor Yellow
    Write-Host "POSITIVE TESTS:"
    Write-Host "1. Run All Tests"
    Write-Host "2. Test Register"
    Write-Host "3. Test Login"
    Write-Host "4. Test Get Me (requires token)"
    Write-Host "5. Test Verify Token (requires token)"
    Write-Host ""
    Write-Host "VALIDATION TESTS (422):"
    Write-Host "6. Test Register - Short Login"
    Write-Host "7. Test Register - Long Login"
    Write-Host "8. Test Register - Short Password"
    Write-Host "9. Test Register - Empty Login"
    Write-Host "10. Test Register - Empty Password"
    Write-Host "11. Test Register - Missing Fields"
    Write-Host ""
    Write-Host "AUTHENTICATION TESTS (401):"
    Write-Host "12. Test Invalid Login"
    Write-Host "13. Test Login Non-Existent User"
    Write-Host "14. Test Login Empty Credentials"
    Write-Host "15. Test Login Missing Fields"
    Write-Host ""
    Write-Host "AUTHORIZATION TESTS (401):"
    Write-Host "16. Test Invalid Token"
    Write-Host "17. Test Verify Invalid Token"
    Write-Host "18. Test Verify Without Token"
    Write-Host ""
    Write-Host "OTHER TESTS:"
    Write-Host "19. Test Duplicate Login (400)"
    Write-Host "20. Test Invalid JSON"
    Write-Host "21. Test Boundary Login (3 chars)"
    Write-Host "22. Test Boundary Password (6 chars)"
    Write-Host "23. Cleanup Test Users"
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
            "5" { if (-not $token) { $token = Read-Host "Enter token" }; Test-VerifyToken -Token $token }
            "6" { Test-RegisterShortLogin }
            "7" { Test-RegisterLongLogin }
            "8" { Test-RegisterShortPassword }
            "9" { Test-RegisterEmptyLogin }
            "10" { Test-RegisterEmptyPassword }
            "11" { Test-RegisterMissingFields }
            "12" { Test-InvalidLogin }
            "13" { Test-LoginNonExistentUser }
            "14" { Test-LoginEmptyCredentials }
            "15" { Test-LoginMissingFields }
            "16" { Test-InvalidToken }
            "17" { Test-VerifyInvalidToken }
            "18" { Test-VerifyWithoutToken }
            "19" { Test-DuplicateLogin }
            "20" { Test-InvalidJSON }
            "21" { Test-RegisterBoundaryLogin }
            "22" { Test-RegisterBoundaryPassword }
            "23" { Cleanup-TestUsers }
            "0" { Write-Host "Exiting..." }
            default { Write-Host "Invalid option" -ForegroundColor Red }
        }
        if ($choice -ne "0") { Read-Host "`nPress Enter to continue" }
    } while ($choice -ne "0")
}
else {
    Run-AllTests
}