# Конфигурация
$BASE_URL = "http://localhost:8000/api"
$HEADERS = @{
    "Content-Type" = "application/json"
}

# Глобальная переменная для хранения токена
$script:AuthToken = $null
$script:TestAccountId = $null

# Функция для логина и получения токена
function Get-AuthToken {
    Write-TestHeader "Login to get token"

    $loginData = @{
        login = "test@example.com"
        password = "test123"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL$AUTH_ENDPOINT/login" `
            -Method Post `
            -Body $loginData `
            -ContentType "application/json"

        $Global:AuthToken = $response.token
        Write-Success "Login successful"
        Write-Host "Token saved for subsequent requests`n"

        # Отладочная информация
        Write-Host "Status Code: 200"
        Write-Host "Response:"
        $response | ConvertTo-Json -Depth 10
        Write-Host $Global:AuthToken

        return $true
    }
    catch {
        Write-Error "Login failed: $_"

        # Попытка показать детали ошибки
        if ($_.Exception.Response) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            Write-Host "Error details:" -ForegroundColor $ErrorColor
            $responseBody | ConvertFrom-Json | ConvertTo-Json -Depth 10
        }

        return $false
    }
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

function Get-AuthHeaders {
    if (-not $script:AuthToken) {
        Write-Error "✗ No auth token. Please login first (option 1)"
        return $null
    }
    $headers = $HEADERS.Clone()
    $headers["Authorization"] = "Bearer $script:AuthToken"
    return $headers
}

function Test-Login {
    Write-Info "`n=== TEST: Login to get token ==="
    $body = @{
        login = "test@example.com"
        password = "Password123"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Success "✓ Login successful"
        $script:AuthToken = $response.token
        Write-Info "Token saved for subsequent requests"
        Show-Response $response $statusCode
        return $response.token
    }
    catch {
        Write-Error "✗ Login failed"
        Write-Host $_.Exception.Message
        Write-Info "Make sure test user exists (run auth.ps1 tests first)"
        return $null
    }
}

function Test-GetAccounts {
    Write-Info "`n=== TEST: Get Accounts List ==="
    $authHeaders = Get-AuthHeaders
    if (-not $authHeaders) { return $null }

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts" -Method Get -Headers $authHeaders -StatusCodeVariable statusCode
        Write-Success "✓ Get accounts successful"
        Show-Response $response $statusCode

        # Проверка структуры ответа
        if ($response -is [Array]) {
            Write-Success "✓ Response is an array"
            if ($response.Count -gt 0) {
                $account = $response[0]
                if ($account.id -and $account.name -and $account.phoneNumber -and $account.status) {
                    Write-Success "✓ Account structure is correct"
                } else {
                    Write-Error "✗ Account structure is incorrect"
                }
            }
        } else {
            Write-Success "✓ Empty accounts list"
        }

        return $response
    }
    catch {
        Write-Error "✗ Get accounts failed"
        Write-Host $_.Exception.Message
        return $null
    }
}

function Test-CreateAccount {
    Write-Info "`n=== TEST: Create Account ==="
    $authHeaders = Get-AuthHeaders
    if (-not $authHeaders) { return $null }

    $body = @{
        name = "Test Account"
        phoneNumber = "+79991234567"
        apiId = "12345678"
        apiHash = "abcdef1234567890abcdef1234567890"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts" -Method Post -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Success "✓ Create account successful"
        Show-Response $response $statusCode

        # Сохраняем ID для последующих тестов
        $script:TestAccountId = $response.id

        # Проверка структуры ответа
        if ($response.id -and $response.name -eq "Test Account" -and $response.phoneNumber -eq "+79991234567" -and $response.status -eq "offline") {
            Write-Success "✓ Account created with correct data"
        } else {
            Write-Error "✗ Account data is incorrect"
        }

        return $response
    }
    catch {
        Write-Error "✗ Create account failed"
        Write-Host $_.Exception.Message
        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Info "Error details:"
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host
        }
        return $null
    }
}

function Test-CreateDuplicateAccount {
    Write-Info "`n=== TEST: Create Duplicate Account ==="
    $authHeaders = Get-AuthHeaders
    if (-not $authHeaders) { return }

    $body = @{
        name = "Duplicate Account"
        phoneNumber = "+79991234567"
        apiId = "12345678"
        apiHash = "abcdef1234567890abcdef1234567890"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts" -Method Post -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected duplicate account"
        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Info "Error response:"
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

            if ($errorDetails.detail.error -eq "ACCOUNT_EXISTS") {
                Write-Success "✓ Error code is correct (ACCOUNT_EXISTS)"
            } else {
                Write-Error "✗ Error code is incorrect"
            }
        }
    }
}

function Test-CreateAccountInvalidPhone {
    Write-Info "`n=== TEST: Create Account with Invalid Phone ==="
    $authHeaders = Get-AuthHeaders
    if (-not $authHeaders) { return }

    $body = @{
        name = "Invalid Phone Account"
        phoneNumber = "invalid_phone"
        apiId = "12345678"
        apiHash = "abcdef1234567890abcdef1234567890"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts" -Method Post -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected invalid phone number"
        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Info "Error response:"
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

            if ($errorDetails.detail.error -eq "VALIDATION_ERROR") {
                Write-Success "✓ Error code is correct (VALIDATION_ERROR)"
            } else {
                Write-Error "✗ Error code is incorrect"
            }
        }
    }
}

function Test-UpdateAccount {
    Write-Info "`n=== TEST: Update Account ==="
    $authHeaders = Get-AuthHeaders
    if (-not $authHeaders) { return $null }

    if (-not $script:TestAccountId) {
        Write-Error "✗ No test account ID. Create account first"
        return $null
    }

    $body = @{
        name = "Updated Test Account"
        apiId = "87654321"
        apiHash = "new_hash_1234567890abcdef1234567890ab"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts/$script:TestAccountId" -Method Patch -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Success "✓ Update account successful"
        Show-Response $response $statusCode

        # Проверка обновленных данных
        if ($response.name -eq "Updated Test Account" -and $response.apiId -eq "87654321") {
            Write-Success "✓ Account updated with correct data"
        } else {
            Write-Error "✗ Account data is incorrect"
        }

        return $response
    }
    catch {
        Write-Error "✗ Update account failed"
        Write-Host $_.Exception.Message
        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Info "Error details:"
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host
        }
        return $null
    }
}

function Test-UpdateNonExistentAccount {
    Write-Info "`n=== TEST: Update Non-Existent Account ==="
    $authHeaders = Get-AuthHeaders
    if (-not $authHeaders) { return }

    $body = @{
        name = "Should Not Work"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts/99999" -Method Patch -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected update of non-existent account"
        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Info "Error response:"
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

            if ($errorDetails.detail.error -eq "ACCOUNT_NOT_FOUND") {
                Write-Success "✓ Error code is correct (ACCOUNT_NOT_FOUND)"
            } else {
                Write-Error "✗ Error code is incorrect"
            }
        }
    }
}

function Test-DeleteAccount {
    Write-Info "`n=== TEST: Delete Account ==="
    $authHeaders = Get-AuthHeaders
    if (-not $authHeaders) { return }

    if (-not $script:TestAccountId) {
        Write-Error "✗ No test account ID. Create account first"
        return
    }

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts/$script:TestAccountId" -Method Delete -Headers $authHeaders -StatusCodeVariable statusCode
        Write-Success "✓ Delete account successful"
        Write-Info "Status Code: $statusCode"

        if ($statusCode -eq 204) {
            Write-Success "✓ Correct status code (204 No Content)"
        } else {
            Write-Error "✗ Incorrect status code (expected 204)"
        }

        $script:TestAccountId = $null
    }
    catch {
        Write-Error "✗ Delete account failed"
        Write-Host $_.Exception.Message
        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Info "Error details:"
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host
        }
    }
}

function Test-DeleteNonExistentAccount {
    Write-Info "`n=== TEST: Delete Non-Existent Account ==="
    $authHeaders = Get-AuthHeaders
    if (-not $authHeaders) { return }

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts/99999" -Method Delete -Headers $authHeaders -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Write-Info "Status Code: $statusCode"
    }
    catch {
        Write-Success "✓ Correctly rejected delete of non-existent account"
        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Info "Error response:"
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

            if ($errorDetails.detail.error -eq "ACCOUNT_NOT_FOUND") {
                Write-Success "✓ Error code is correct (ACCOUNT_NOT_FOUND)"
            } else {
                Write-Error "✗ Error code is incorrect"
            }
        }
    }
}

function Run-AllTests {
    Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║   COMANASO ACCOUNTS API TESTS          ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Yellow

    # Логин для получения токена
    Test-Login; Start-Sleep -Seconds 1

    if (-not $script:AuthToken) {
        Write-Error "Cannot proceed without auth token"
        return
    }

    # Основные тесты
    Test-GetAccounts; Start-Sleep -Seconds 1
    Test-CreateAccount; Start-Sleep -Seconds 1
    Test-GetAccounts; Start-Sleep -Seconds 1

    # Негативные тесты создания
    Test-CreateDuplicateAccount; Start-Sleep -Seconds 1
    Test-CreateAccountInvalidPhone; Start-Sleep -Seconds 1

    # Тесты обновления
    Test-UpdateAccount; Start-Sleep -Seconds 1
    Test-UpdateNonExistentAccount; Start-Sleep -Seconds 1

    # Тесты удаления
    Test-DeleteAccount; Start-Sleep -Seconds 1
    Test-DeleteNonExistentAccount; Start-Sleep -Seconds 1

    # Проверка что аккаунт удален
    Test-GetAccounts

    Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║   TESTS COMPLETED                      ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Yellow
}

function Show-Menu {
    Write-Host "`n=== COMANASO ACCOUNTS API TESTER ===" -ForegroundColor Yellow
    Write-Host "Auth Status: $(if ($script:AuthToken) { 'Logged in' } else { 'Not logged in' })" -ForegroundColor $(if ($script:AuthToken) { 'Green' } else { 'Red' })
    Write-Host ""
    Write-Host "1. Login (get auth token)"
    Write-Host "2. Get Accounts List"
    Write-Host "3. Create Account"
    Write-Host "4. Create Duplicate Account (negative test)"
    Write-Host "5. Create Account with Invalid Phone (negative test)"
    Write-Host "6. Update Account"
    Write-Host "7. Update Non-Existent Account (negative test)"
    Write-Host "8. Delete Account"
    Write-Host "9. Delete Non-Existent Account (negative test)"
    Write-Host "10. Run All Tests"
    Write-Host "0. Exit"
    Write-Host ""
}

if ($args.Count -eq 0) {
    do {
        Show-Menu
        $choice = Read-Host "Select option"
        switch ($choice) {
            "1" { Test-Login }
            "2" { Test-GetAccounts }
            "3" { Test-CreateAccount }
            "4" { Test-CreateDuplicateAccount }
            "5" { Test-CreateAccountInvalidPhone }
            "6" { Test-UpdateAccount }
            "7" { Test-UpdateNonExistentAccount }
            "8" { Test-DeleteAccount }
            "9" { Test-DeleteNonExistentAccount }
            "10" { Run-AllTests }
            "0" { Write-Host "Exiting..." }
            default { Write-Host "Invalid option" -ForegroundColor Red }
        }
        if ($choice -ne "0") { Read-Host "`nPress Enter to continue" }
    } while ($choice -ne "0")
}
else {
    Run-AllTests
}
