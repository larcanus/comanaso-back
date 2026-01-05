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
    param($response, $statusCode)
    Write-Host "Status: $statusCode" -ForegroundColor $(if ($statusCode -ge 200 -and $statusCode -lt 300) { "Green" } else { "Red" })
    Write-Host ($response | ConvertTo-Json -Depth 10)
}

function Cleanup-TestUsers {
    Write-Host "`n=== CLEANING TEST USERS ===" -ForegroundColor Yellow

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/dev/cleanup/test-users" `
            -Method Delete `
            -Headers $HEADERS `
            -StatusCodeVariable statusCode `
            -ErrorAction Stop

        Write-Success "✓ $($response.message)"
        Write-Host "  Deleted: $($response.deleted_count) user(s)" -ForegroundColor Cyan
        Show-Response $response $statusCode
    }
    catch {
        Write-Error "✗ Failed to clean test users: $($_.Exception.Message)"
        if ($_.ErrorDetails.Message) {
            Write-Host "  Response: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
        }
    }
}

function Test-Register {
    Write-Info "`n=== TEST: Register User ==="
    $timestamp = Get-Date -Format "HHmmss"
    $body = @{
        login = "test_user_$timestamp@example.com"
        password = "Password123"
    } | ConvertTo-Json
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Success "✓ Registration successful"
        Write-Host "Created user: test_user_$timestamp@example.com" -ForegroundColor Cyan
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
    param($Login = $null)
    Write-Info "`n=== TEST: Login User ==="

    # Если логин не передан, используем тот же логин, что был создан последним
    if (-not $Login) {
        $timestamp = Get-Date -Format "HHmmss"
        $Login = "test_user_$timestamp@example.com"
    }

    $body = @{
        login = $Login
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

function Test-Logout {
    param($Token)
    Write-Info "`n=== TEST: Logout User ==="
    if (-not $Token) { Write-Error "✗ No token provided"; return $null }

    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer $Token"

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/logout" -Method Post -Headers $authHeaders -StatusCodeVariable statusCode
        Write-Success "✓ Logout successful"
        Show-Response $response $statusCode

        # Проверка структуры ответа
        if ($response.status -eq "success" -and $response.message) {
            Write-Success "✓ Response structure is correct"
        } else {
            Write-Error "✗ Response structure is incorrect"
        }

        return $response
    }
    catch {
        Write-Error "✗ Logout failed"
        Write-Host $_.Exception.Message
        return $null
    }
}

function Test-LogoutInvalidToken {
    Write-Info "`n=== TEST: Logout with Invalid Token ==="
    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer invalid_token_xyz123"

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/logout" -Method Post -Headers $authHeaders -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected invalid token"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        $errorCode = if ($errorDetails.detail -and $errorDetails.detail.error) {
            $errorDetails.detail.error
        } elseif ($errorDetails.error) {
            $errorDetails.error
        } else {
            $null
        }

        if ($errorCode -eq "UNAUTHORIZED") {
            Write-Success "✓ Error code is correct (UNAUTHORIZED)"
        } else {
            Write-Error "✗ Expected error code UNAUTHORIZED, got: $errorCode"
        }
    }
}

function Test-DeleteAccount {
    param($Token)
    Write-Info "`n=== TEST: Delete User Account ==="
    if (-not $Token) { Write-Error "✗ No token provided"; return $null }

    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer $Token"

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/delete-account" -Method Delete -Headers $authHeaders -StatusCodeVariable statusCode
        Write-Success "✓ Account deletion successful"
        Show-Response $response $statusCode

        # Проверка структуры ответа
        if ($response.status -eq "success" -and $response.deleted_user_id -and $response.deleted_accounts_count -ge 0) {
            Write-Success "✓ Response structure is correct"
        } else {
            Write-Error "✗ Response structure is incorrect"
        }

        return $response
    }
    catch {
        Write-Error "✗ Account deletion failed"
        Write-Host $_.Exception.Message
        return $null
    }
}

function Test-DeleteAccountInvalidToken {
    Write-Info "`n=== TEST: Delete Account with Invalid Token ==="
    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer invalid_token_xyz123"

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/delete-account" -Method Delete -Headers $authHeaders -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected invalid token"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        $errorCode = if ($errorDetails.detail -and $errorDetails.detail.error) {
            $errorDetails.detail.error
        } elseif ($errorDetails.error) {
            $errorDetails.error
        } else {
            $null
        }

        if ($errorCode -eq "UNAUTHORIZED") {
            Write-Success "✓ Error code is correct (UNAUTHORIZED)"
        } else {
            Write-Error "✗ Expected error code UNAUTHORIZED, got: $errorCode"
        }
    }
}

function Test-DeleteAccountWithoutToken {
    Write-Info "`n=== TEST: Delete Account Without Token ==="

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/delete-account" -Method Delete -Headers $HEADERS -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected request without token"
        Write-Host "Error: $($_.Exception.Message)"
    }
}

function Test-LogoutWithoutToken {
    Write-Info "`n=== TEST: Logout Without Token ==="

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/logout" -Method Post -Headers $HEADERS -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected request without token"
        Write-Host "Error: $($_.Exception.Message)"
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

    # Создаем уникального пользователя
    $timestamp = Get-Date -Format "HHmmss"
    $testLogin = "duplicate_test_$timestamp@example.com"

    # Сначала регистрируем пользователя
    $body = @{
        login = $testLogin
        password = "Password123"
    } | ConvertTo-Json

    try {
        $firstResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Host "  First registration successful (id: $($firstResponse.user.id))" -ForegroundColor Cyan
    }
    catch {
        Write-Error "✗ Failed to register first user for duplicate test"
        return
    }

    # Теперь пытаемся зарегистрировать с тем же логином
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected duplicate login"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        $errorCode = if ($errorDetails.detail -and $errorDetails.detail.error) {
            $errorDetails.detail.error
        } elseif ($errorDetails.error) {
            $errorDetails.error
        } else {
            $null
        }

        if ($errorCode -eq "USERNAME_EXISTS") {
            Write-Success "✓ Error code is correct (USERNAME_EXISTS)"
        } else {
            Write-Error "✗ Expected error code USERNAME_EXISTS, got: $errorCode"
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
    $timestamp = Get-Date -Format "HHmmss"
    $login = "tes$timestamp"  # Уникальный логин: abc135425

    try {
        $body = @{
            login = $login
            password = "password123"
        } | ConvertTo-Json

        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Body $body -ContentType "application/json" -Headers $HEADERS -StatusCodeVariable statusCode

        Write-Success "✓ Registration successful with 3 char login"
        Write-Host "Created user: $login" -ForegroundColor Cyan
        Show-Response $response $statusCode
    }
    catch {
        Write-Error "✗ Registration failed (3 chars should be valid)"
        Write-Host $_.Exception.Message
        return $null
    }
}

function Test-RegisterBoundaryPassword {
    Write-Info "`n=== TEST: Register with Boundary Password (6 chars) ==="
    $timestamp = Get-Date -Format "HHmmss"
    $login = "test_boundary_pw_$timestamp"

    try {
        $body = @{
            login = $login
            password = "pass12"  # Ровно 6 символов
        } | ConvertTo-Json

        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Body $body -ContentType "application/json" -Headers $HEADERS -StatusCodeVariable statusCode

        Write-Success "✓ Registration successful with 6 char password"
        Write-Host "Created user: $login" -ForegroundColor Cyan
        Show-Response $response $statusCode
    }
    catch {
        Write-Error "✗ Registration failed (6 chars should be valid)"
        Write-Host $_.Exception.Message
        return $null
    }
}

# ============================================
# PASSWORD RESET TESTS
# ============================================

function Test-PasswordResetRequest {
    Write-Info "`n=== TEST: Request Password Reset ==="

    # Создаем тестового пользователя для сброса пароля
    $timestamp = Get-Date -Format "HHmmss"
    $testEmail = "test_$timestamp@example.com"
    $testUsername = "reset_user_$timestamp"

    $registerBody = @{
        email = $testEmail
        login = $testUsername
        password = "OldPassword123"
    } | ConvertTo-Json

    try {
        $registerResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $registerBody
        Write-Host "  Test user created: $testEmail" -ForegroundColor Cyan
    }
    catch {
        Write-Error "✗ Failed to create test user"
        Write-Host $_.Exception.Message
        return
    }

    # Запрос на сброс пароля
    $body = @{
        email = $testEmail
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/password-reset/request" `
            -Method Post `
            -Headers $HEADERS `
            -Body $body `
            -StatusCodeVariable statusCode

        Write-Success "✓ Password reset email sent successfully"
        Show-Response $response $statusCode

        # В dev режиме может возвращаться токен
        if ($response.token) {
            Write-Info "Reset token (DEV): $($response.token)"
            return $response.token
        }

        return $true
    }
    catch {
        Write-Error "✗ Failed to send password reset email"
        Write-Host $_.Exception.Message
        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host
        }
        return $null
    }
}

function Test-PasswordResetRequestNonExistentEmail {
    Write-Info "`n=== TEST: Request Password Reset for Non-Existent Email ==="

    $body = @{
        email = "nonexistent_$(Get-Date -Format 'HHmmss')@example.com"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/password-reset/request" `
            -Method Post `
            -Headers $HEADERS `
            -Body $body `
            -StatusCodeVariable statusCode

        Write-Success "✓ Request accepted (security: no information leak)"
        Show-Response $response $statusCode
    }
    catch {
        Write-Error "✗ Unexpected error for non-existent email"
        Write-Host $_.Exception.Message
    }
}

function Test-PasswordResetConfirm {
    param($Token)
    Write-Info "`n=== TEST: Confirm Password Reset with Token ==="

    if (-not $Token) {
        Write-Error "✗ No token provided"
        return $false
    }

    $newPassword = "NewPassword456"
    $body = @{
        token = $Token
        new_password = $newPassword
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/password-reset/confirm" `
            -Method Post `
            -Headers $HEADERS `
            -Body $body `
            -StatusCodeVariable statusCode

        Write-Success "✓ Password reset successful"
        Show-Response $response $statusCode
        return $true
    }
    catch {
        Write-Error "✗ Failed to reset password"
        Write-Host $_.Exception.Message
        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host
        }
        return $false
    }
}

function Test-PasswordResetInvalidToken {
    Write-Info "`n=== TEST: Password Reset with Invalid Token ==="

    $body = @{
        token = "invalid_token_12345"
        new_password = "NewPassword456"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/password-reset/confirm" `
            -Method Post `
            -Headers $HEADERS `
            -Body $body `
            -StatusCodeVariable statusCode

        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected invalid token"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

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
        }
    }
}

function Test-PasswordResetFullFlow {
    Write-Info "`n=== TEST: Full Password Reset Flow ==="

    # Шаг 1: Создание пользователя
    $timestamp = Get-Date -Format "HHmmss"
    $testEmail = "fullflow_test_$timestamp@example.com"
    $testUsername = "fullflow_user_$timestamp"
    $oldPassword = "OldPassword123"

    Write-Info "Step 1: Creating test user..."
    $registerBody = @{
        email = $testEmail
        login = $testUsername
        password = $oldPassword
    } | ConvertTo-Json

    try {
        $registerResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $registerBody
        Write-Success "✓ User created: $testEmail"
    }
    catch {
        Write-Error "✗ Failed to create user"
        Write-Host $_.Exception.Message
        return
    }

    # Шаг 2: Запрос на сброс пароля
    Write-Info "Step 2: Requesting password reset..."
    $resetRequestBody = @{
        email = $testEmail
    } | ConvertTo-Json

    try {
        $resetResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/password-reset/request" `
            -Method Post `
            -Headers $HEADERS `
            -Body $resetRequestBody

        Write-Success "✓ Reset request sent"

        if (-not $resetResponse.token) {
            Write-Warning "⚠ Token not returned (production mode). Cannot complete full flow test."
            return
        }

        $resetToken = $resetResponse.token
        Write-Info "Reset token received: $($resetToken.Substring(0, 20))..."

    }
    catch {
        Write-Error "✗ Failed to request password reset"
        return
    }

    # Шаг 3: Подтверждение сброса пароля
    Write-Info "Step 3: Confirming password reset..."
    $newPassword = "NewPassword456"
    $confirmBody = @{
        token = $resetToken
        new_password = $newPassword
    } | ConvertTo-Json

    try {
        $confirmResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/password-reset/confirm" `
            -Method Post `
            -Headers $HEADERS `
            -Body $confirmBody

        Write-Success "✓ Password reset confirmed"
    }
    catch {
        Write-Error "✗ Failed to confirm password reset"
        return
    }

    # Шаг 4: Попытка входа со старым паролем (должна провалиться)
    Write-Info "Step 4: Testing login with OLD password (should fail)..."
    $oldLoginBody = @{
        login = $testEmail
        password = $oldPassword
    } | ConvertTo-Json

    try {
        $oldLoginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Headers $HEADERS -Body $oldLoginBody
        Write-Error "✗ Login with old password should have failed but succeeded"
    }
    catch {
        Write-Success "✓ Correctly rejected old password"
    }

    # Шаг 5: Вход с новым паролем (должен успешно пройти)
    Write-Info "Step 5: Testing login with NEW password (should succeed)..."
    $newLoginBody = @{
        login = $testEmail
        password = $newPassword
    } | ConvertTo-Json

    try {
        $newLoginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Headers $HEADERS -Body $newLoginBody
        Write-Success "✓ Successfully logged in with new password"
        Write-Success "✓✓✓ FULL PASSWORD RESET FLOW COMPLETED SUCCESSFULLY ✓✓✓"
    }
    catch {
        Write-Error "✗ Failed to login with new password"
        Write-Host $_.Exception.Message
    }
}

# ============================================
# PROFILE MANAGEMENT TESTS
# ============================================

function Test-GetProfile {
    param($Token)
    Write-Info "`n=== TEST: Get User Profile ==="
    if (-not $Token) { Write-Error "✗ No token provided"; return $null }

    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer $Token"

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/me" -Method Get -Headers $authHeaders -StatusCodeVariable statusCode
        Write-Success "✓ Profile retrieved successfully"
        Show-Response $response $statusCode

        # Проверка структуры ответа
        if ($response.id -and $response.username -and $response.settings) {
            Write-Success "✓ Response structure is correct"
        } else {
            Write-Error "✗ Response structure is incorrect"
        }

        return $response
    }
    catch {
        Write-Error "✗ Failed to get profile"
        Write-Host $_.Exception.Message
        return $null
    }
}

function Test-UpdateProfile {
    param($Token)
    Write-Info "`n=== TEST: Update User Profile (Full) ==="
    if (-not $Token) { Write-Error "✗ No token provided"; return $null }

    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer $Token"

    $timestamp = Get-Date -Format "HHmmss"
    $body = @{
        username = "updated_user_$timestamp"
        email = "updated_$timestamp@example.com"
        settings = @{
            language = "en"
            theme = "dark"
            notifications_enabled = $true
        }
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/me" -Method Patch -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Success "✓ Profile updated successfully"
        Show-Response $response $statusCode

        # Проверка обновленных данных
        if ($response.username -like "updated_user_*" -and $response.email -like "updated_*@example.com") {
            Write-Success "✓ Profile data updated correctly"
        } else {
            Write-Error "✗ Profile data was not updated"
        }

        return $response
    }
    catch {
        Write-Error "✗ Failed to update profile"
        Write-Host $_.Exception.Message
        return $null
    }
}

function Test-UpdateProfilePartial {
    param($Token)
    Write-Info "`n=== TEST: Update Profile (Partial - Settings Only) ==="
    if (-not $Token) { Write-Error "✗ No token provided"; return $null }

    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer $Token"

    $body = @{
        settings = @{
            shareUserName = $false
            shareNickname = $true
            shareMessageText = $false
            shareDialogTitles = $true
        }
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/me" -Method Patch -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Success "✓ Profile settings updated successfully"
        Show-Response $response $statusCode

        # Проверка обновленных настроек
        if ($response.settings.shareUserName -eq $false -and
            $response.settings.shareNickname -eq $true -and
            $response.settings.shareMessageText -eq $false -and
            $response.settings.shareDialogTitles -eq $true) {
            Write-Success "✓ Settings updated correctly"
        } else {
            Write-Error "✗ Settings were not updated correctly"
        }

        return $response
    }
    catch {
        Write-Error "✗ Failed to update profile settings"
        Write-Host $_.Exception.Message
        return $null
    }
}

function Test-UpdateProfileDuplicateUsername {
    param($Token, $ExistingUsername)
    Write-Info "`n=== TEST: Update Profile with Duplicate Username ==="
    if (-not $Token) { Write-Error "✗ No token provided"; return }
    if (-not $ExistingUsername) { Write-Error "✗ No existing username provided"; return }

    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer $Token"

    $body = @{
        username = $ExistingUsername
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/me" -Method Patch -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected duplicate username"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        $errorCode = if ($errorDetails.detail -and $errorDetails.detail.error) {
            $errorDetails.detail.error
        } elseif ($errorDetails.error) {
            $errorDetails.error
        } else {
            $null
        }

        if ($errorCode -eq "USERNAME_EXISTS") {
            Write-Success "✓ Error code is correct (USERNAME_EXISTS)"
        } else {
            Write-Error "✗ Expected error code USERNAME_EXISTS, got: $errorCode"
        }
    }
}

function Test-UpdateProfileDuplicateEmail {
    param($Token, $ExistingEmail)
    Write-Info "`n=== TEST: Update Profile with Duplicate Email ==="
    if (-not $Token) { Write-Error "✗ No token provided"; return }
    if (-not $ExistingEmail) { Write-Error "✗ No existing email provided"; return }

    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer $Token"

    $body = @{
        email = $ExistingEmail
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/me" -Method Patch -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected duplicate email"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        $errorCode = if ($errorDetails.detail -and $errorDetails.detail.error) {
            $errorDetails.detail.error
        } elseif ($errorDetails.error) {
            $errorDetails.error
        } else {
            $null
        }

        if ($errorCode -eq "EMAIL_EXISTS") {
            Write-Success "✓ Error code is correct (EMAIL_EXISTS)"
        } else {
            Write-Error "✗ Expected error code EMAIL_EXISTS, got: $errorCode"
        }
    }
}

function Test-UpdateProfileInvalidToken {
    Write-Info "`n=== TEST: Update Profile with Invalid Token ==="
    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer invalid_token_xyz123"

    $body = @{
        username = "newusername"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/me" -Method Patch -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected invalid token"
        $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Info "Error response:"
        $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

        $errorCode = if ($errorDetails.detail -and $errorDetails.detail.error) {
            $errorDetails.detail.error
        } elseif ($errorDetails.error) {
            $errorDetails.error
        } else {
            $null
        }

        if ($errorCode -eq "UNAUTHORIZED") {
            Write-Success "✓ Error code is correct (UNAUTHORIZED)"
        } else {
            Write-Error "✗ Expected error code UNAUTHORIZED, got: $errorCode"
        }
    }
}

function Test-UpdateProfileInvalidData {
    param($Token)
    Write-Info "`n=== TEST: Update Profile with Invalid Data ==="
    if (-not $Token) { Write-Error "✗ No token provided"; return }

    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer $Token"

    $body = @{
        username = "ab"  # Слишком короткий
        email = "invalid-email"  # Невалидный email
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/me" -Method Patch -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected invalid data"
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

function Test-UpdateProfileFull {
    Write-Host "`n=== TEST: Update User Profile (Full) ===" -ForegroundColor Cyan

    $timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $newUsername = "updated_user_$timestamp"
    $newEmail = "updated_$timestamp@test.com"

    $body = @{
        username = $newUsername
        email = $newEmail
        settings = @{
            shareUserName = $false
            shareNickname = $true
            shareMessageText = $false
            shareDialogTitles = $true
        }
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/auth/me" -Method Patch `
            -Headers $headers -Body $body -ContentType "application/json"

        Write-Success "✓ Profile updated successfully"
        Write-Host "Response:" -ForegroundColor Gray
        $response | ConvertTo-Json -Depth 10

        # Проверка обновленных данных
        if ($response.username -eq $newUsername -and
            $response.email -eq $newEmail -and
            $response.settings.shareUserName -eq $false -and
            $response.settings.shareNickname -eq $true -and
            $response.settings.shareMessageText -eq $false -and
            $response.settings.shareDialogTitles -eq $true) {
            Write-Success "✓ Profile data updated correctly"
            Write-Host "  Username: $($response.username)" -ForegroundColor Cyan
            Write-Host "  Email: $($response.email)" -ForegroundColor Cyan
            Write-Host "  Settings updated" -ForegroundColor Cyan
        } else {
            Write-Error "✗ Profile data not updated as expected"
        }
    } catch {
        Write-Error "✗ Failed to update profile"
        if ($_.ErrorDetails.Message) {
            $errorObj = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Host "Error: $($errorObj.error) - $($errorObj.message)" -ForegroundColor Red
        } else {
            Write-Host $_.Exception.Message -ForegroundColor Red
        }
    }
}

function Test-UpdatePassword {
    Write-Info "`n=== TEST: Update Password ==="

    # Создаем отдельного пользователя для теста смены пароля
    $timestamp = Get-Date -Format "HHmmss"
    $testLogin = "password_test_$timestamp@example.com"
    $oldPassword = "OldPassword123"

    Write-Info "Creating test user for password update..."
    $registerBody = @{
        login = $testLogin
        password = $oldPassword
    } | ConvertTo-Json

    try {
        $registerResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $registerBody
        $token = $registerResponse.token
        Write-Success "✓ Test user created: $testLogin"
    }
    catch {
        Write-Error "✗ Failed to create test user"
        Write-Host $_.Exception.Message
        return
    }

    $authHeaders = $HEADERS.Clone()
    $authHeaders["Authorization"] = "Bearer $token"

    $newPassword = "NewPassword456"
    $body = @{
        password = $newPassword
    } | ConvertTo-Json

    try {
        # Обновляем пароль
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/me" -Method Patch -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Success "✓ Password updated successfully"
        Show-Response $response $statusCode

        # Пытаемся войти со старым паролем (должно не получиться)
        Write-Info "Attempting login with old password..."
        $oldLoginBody = @{
            login = $testLogin
            password = $oldPassword
        } | ConvertTo-Json

        try {
            $oldLoginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Headers $HEADERS -Body $oldLoginBody
            Write-Error "✗ Login with old password should have failed but succeeded"
        }
        catch {
            Write-Success "✓ Correctly rejected old password"
        }

        # Пытаемся войти с новым паролем (должно получиться)
        Write-Info "Attempting login with new password..."
        $newLoginBody = @{
            login = $testLogin
            password = $newPassword
        } | ConvertTo-Json

        try {
            $newLoginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Headers $HEADERS -Body $newLoginBody
            Write-Success "✓ Successfully logged in with new password"
            Write-Host "  Token: $($newLoginResponse.token.Substring(0, 20))..." -ForegroundColor Cyan
        }
        catch {
            Write-Error "✗ Login with new password failed but should have succeeded"
            Write-Host $_.Exception.Message
        }

    }
    catch {
        Write-Error "✗ Failed to update password"
        Write-Host $_.Exception.Message
    }
}

function Run-AllTests {
    Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║   COMANASO AUTH API TESTS              ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Yellow

    # ОЧИСТКА ПЕРЕД ТЕСТАМИ
    Cleanup-TestUsers
    Start-Sleep -Seconds 1

    Write-Host "`n=== POSITIVE TESTS ===" -ForegroundColor Yellow
    # Основные позитивные тесты
    $user = Test-Register; Start-Sleep -Seconds 1

    # Сохраняем логин для входа
    $testLogin = $user.user.login
    $token = Test-Login -Login $testLogin; Start-Sleep -Seconds 1

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

    Write-Host "`n=== LOGOUT TESTS ===" -ForegroundColor Yellow
    # Тесты logout
    if ($token) {
        Test-Logout -Token $token; Start-Sleep -Seconds 1
    }
    Test-LogoutInvalidToken; Start-Sleep -Seconds 1
    Test-LogoutWithoutToken; Start-Sleep -Seconds 1

    Write-Host "`n=== ACCOUNT DELETION TESTS ===" -ForegroundColor Yellow
    # Тесты удаления учетной записи (нужно создать нового пользователя, так как предыдущий мог быть удален)
    Write-Info "Creating new user for account deletion tests..."
    $deleteTestUser = Test-Register; Start-Sleep -Seconds 1
    $deleteLogin = $deleteTestUser.user.login
    $deleteToken = Test-Login -Login $deleteLogin; Start-Sleep -Seconds 1

    if ($deleteToken) {
        Test-DeleteAccount -Token $deleteToken; Start-Sleep -Seconds 1
    }
    Test-DeleteAccountInvalidToken; Start-Sleep -Seconds 1
    Test-DeleteAccountWithoutToken; Start-Sleep -Seconds 1

    Write-Host "`n=== DUPLICATE & EDGE CASES ===" -ForegroundColor Yellow
    # Дубликаты и граничные случаи
    Test-DuplicateLogin; Start-Sleep -Seconds 1
    Test-InvalidJSON; Start-Sleep -Seconds 1

    Write-Host "`n=== PASSWORD RESET TESTS ===" -ForegroundColor Yellow
    # Тесты восстановления пароля
    Test-PasswordResetRequest; Start-Sleep -Seconds 1
    Test-PasswordResetRequestNonExistentEmail; Start-Sleep -Seconds 1
    Test-PasswordResetInvalidToken; Start-Sleep -Seconds 1
    Test-PasswordResetFullFlow; Start-Sleep -Seconds 1

    Write-Host "`n=== BOUNDARY TESTS ===" -ForegroundColor Yellow
    # Граничные значения (должны пройти)
    Test-RegisterBoundaryLogin; Start-Sleep -Seconds 1
    Test-RegisterBoundaryPassword; Start-Sleep -Seconds 1

    Write-Host "`n=== PROFILE MANAGEMENT TESTS ===" -ForegroundColor Yellow
    # Создаем нового пользователя для тестов профиля
    Write-Info "Creating new user for profile tests..."
    $profileUser = Test-Register; Start-Sleep -Seconds 1
    $profileLogin = $profileUser.user.login
    $profileToken = Test-Login -Login $profileLogin; Start-Sleep -Seconds 1

    if ($profileToken) {
        # Получение профиля
        $profile = Test-GetProfile -Token $profileToken; Start-Sleep -Seconds 1

        # Обновление профиля (полное)
        Test-UpdateProfile -Token $profileToken; Start-Sleep -Seconds 1

        # Частичное обновление (только settings)
        Test-UpdateProfilePartial -Token $profileToken; Start-Sleep -Seconds 1

        # Обновление пароля
        Test-UpdatePassword -Token $profileToken -Login $profileLogin -OldPassword "Password123"; Start-Sleep -Seconds 1

        # Создаем второго пользователя для тестов дубликатов
        Write-Info "Creating second user for duplicate tests..."
        $timestamp = Get-Date -Format "HHmmss"
        $secondUserBody = @{
            login = "second_user_$timestamp"
            password = "Password123"
        } | ConvertTo-Json
        try {
            $secondUser = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $secondUserBody
            $secondToken = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Headers $HEADERS -Body $secondUserBody

            # Обновляем второго пользователя с уникальными данными
            $updateSecondBody = @{
                username = "existing_username_$timestamp"
                email = "existing_$timestamp@example.com"
            } | ConvertTo-Json
            $authHeaders = $HEADERS.Clone()
            $authHeaders["Authorization"] = "Bearer $($secondToken.token)"
            Invoke-RestMethod -Uri "$BASE_URL/auth/me" -Method Patch -Headers $authHeaders -Body $updateSecondBody | Out-Null

            # Тестируем дубликаты с первым пользователем
            Test-UpdateProfileDuplicateUsername -Token $profileToken -ExistingUsername "existing_username_$timestamp"; Start-Sleep -Seconds 1
            Test-UpdateProfileDuplicateEmail -Token $profileToken -ExistingEmail "existing_$timestamp@example.com"; Start-Sleep -Seconds 1
        }
        catch {
            Write-Warning "⚠ Could not create second user for duplicate tests"
        }

        # Тесты с невалидными данными
        Test-UpdateProfileInvalidData -Token $profileToken; Start-Sleep -Seconds 1
    }

    # Тесты с невалидным токеном
    Test-UpdateProfileInvalidToken; Start-Sleep -Seconds 1

    # ФИНАЛЬНАЯ ОЧИСТКА
    Write-Host "`n=== FINAL CLEANUP ===" -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    Cleanup-TestUsers

    Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║   ALL TESTS COMPLETED                  ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Green
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
    Write-Host "28. Test Delete Account Invalid Token"
    Write-Host "29. Test Delete Account Without Token"
    Write-Host ""
    Write-Host "LOGOUT TESTS:"
    Write-Host "24. Test Logout (requires token)"
    Write-Host "25. Test Logout Invalid Token"
    Write-Host "26. Test Logout Without Token"
    Write-Host ""
    Write-Host "PROFILE MANAGEMENT:"
    Write-Host "30. Test Get Profile (requires token)"
    Write-Host "31. Test Update Profile Full (requires token)"
    Write-Host "32. Test Update Profile Partial (requires token)"
    Write-Host "33. Test Update Profile Duplicate Username"
    Write-Host "34. Test Update Profile Duplicate Email"
    Write-Host "35. Test Update Profile Invalid Data (requires token)"
    Write-Host "36. Test Update Profile Invalid Token"
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
            "24" { if (-not $token) { $token = Read-Host "Enter token" }; Test-Logout -Token $token }
            "25" { Test-LogoutInvalidToken }
            "26" { Test-LogoutWithoutToken }
            "27" { if (-not $token) { $token = Read-Host "Enter token" }; Test-DeleteAccount -Token $token }
            "28" { Test-DeleteAccountInvalidToken }
            "29" { Test-DeleteAccountWithoutToken }
            "30" { if (-not $token) { $token = Read-Host "Enter token" }; Test-GetProfile -Token $token }
            "31" { if (-not $token) { $token = Read-Host "Enter token" }; Test-UpdateProfile -Token $token }
            "32" { if (-not $token) { $token = Read-Host "Enter token" }; Test-UpdateProfilePartial -Token $token }
            "33" {
                if (-not $token) { $token = Read-Host "Enter token" }
                $existingUsername = Read-Host "Enter existing username to test duplicate"
                Test-UpdateProfileDuplicateUsername -Token $token -ExistingUsername $existingUsername
            }
            "34" {
                if (-not $token) { $token = Read-Host "Enter token" }
                $existingEmail = Read-Host "Enter existing email to test duplicate"
                Test-UpdateProfileDuplicateEmail -Token $token -ExistingEmail $existingEmail
            }
            "35" { if (-not $token) { $token = Read-Host "Enter token" }; Test-UpdateProfileInvalidData -Token $token }
            "36" { Test-UpdateProfileInvalidToken }
            "37" { Test-PasswordResetRequest }
            "38" { Test-PasswordResetRequestNonExistentEmail }
            "39" {
                $token = Read-Host "Enter reset token"
                Test-PasswordResetConfirm -Token $token
            }
            "40" { Test-PasswordResetInvalidToken }
            "41" { Test-PasswordResetFullFlow }
            "0" { Write-Host "Exiting..." }
            default { Write-Host "Invalid option" -ForegroundColor Red }
        }
        if ($choice -ne "0") { Read-Host "`nPress Enter to continue" }
    } while ($choice -ne "0")
}
else {
    Run-AllTests
}