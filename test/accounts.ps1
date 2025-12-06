# Конфигурация
$BASE_URL = "http://localhost:8000/api"
$HEADERS = @{
    "Content-Type" = "application/json"
}

# Глобальная переменная для хранения токена
$script:AuthToken = $null
$script:TestAccountId = $null

# Функция для настройки тестового пользователя
function Setup-TestUser {
    Write-Info "`n=== SETUP: Ensure test user exists ==="

    $login = "test@example.com"
    $password = "Password123"

    # Пытаемся залогиниться
    $loginBody = @{
        login = $login
        password = $password
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/auth/login" `
            -Method Post `
            -Headers $HEADERS `
            -Body $loginBody

        $script:AuthToken = $response.token
        Write-Success "✓ Test user exists, logged in successfully"
        return $true
    }
    catch {
        # Пользователь не существует, создаем
        Write-Info "Test user doesn't exist, creating..."

        $registerBody = @{
            login = $login
            password = $password
        } | ConvertTo-Json

        try {
            $registerResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/register" `
                -Method Post `
                -Headers $HEADERS `
                -Body $registerBody

            Write-Success "✓ Test user created successfully"

            # Теперь логинимся
            $loginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login" `
                -Method Post `
                -Headers $HEADERS `
                -Body $loginBody

            $script:AuthToken = $loginResponse.token
            Write-Success "✓ Logged in with new test user"
            return $true
        }
        catch {
            Write-Error "✗ Failed to create test user: $($_.Exception.Message)"
            return $false
        }
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

function Cleanup-TestAccounts {
    Write-Info "`n=== CLEANUP: Removing test accounts ==="
    $authHeaders = Get-AuthHeaders
    if (-not $authHeaders) {
        Write-Error "✗ Cannot cleanup without auth token"
        return
    }

    try {
        # Получаем список всех аккаунтов
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts" -Method Get -Headers $authHeaders

        if ($response.accounts -and $response.accounts.Count -gt 0) {
            Write-Info "Found $($response.accounts.Count) account(s) to delete"

            foreach ($account in $response.accounts) {
                # Удаляем тестовые аккаунты (с номером +79991234567 или именем содержащим "Test")
                if ($account.phoneNumber -eq "+79991234567" -or $account.name -like "*Test*") {
                    try {
                        Invoke-RestMethod -Uri "$BASE_URL/accounts/$($account.id)" -Method Delete -Headers $authHeaders | Out-Null
                        Write-Success "✓ Deleted account: $($account.name) ($($account.phoneNumber))"
                    }
                    catch {
                        Write-Error "✗ Failed to delete account $($account.id): $($_.Exception.Message)"
                    }
                }
            }
            Write-Success "✓ Cleanup completed"
        }
        else {
            Write-Info "No accounts found to cleanup"
        }
    }
    catch {
        Write-Error "✗ Cleanup failed: $($_.Exception.Message)"
    }
}

function Cleanup-TestUsers {
    Write-Info "`n=== CLEANUP: Removing test users ==="
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/dev/cleanup/test-users" -Method Delete -Headers $HEADERS -StatusCodeVariable statusCode
        Write-Success "✓ Test users cleanup successful"
        Show-Response $response $statusCode
    }
    catch {
        Write-Error "✗ Test users cleanup failed (dev endpoint might be disabled)"
        Write-Host $_.Exception.Message
    }
}

function Test-Login {
    Write-Info "`n=== TEST: Login to get token ==="

    if (-not (Setup-TestUser)) {
        Write-Error "✗ Failed to setup test user"
        return $null
    }

    Write-Success "✓ Login successful"
    Write-Info "Token: $script:AuthToken"
    return $script:AuthToken
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
        if ($response.accounts -is [Array]) {
            Write-Success "✓ Response contains accounts array"
            if ($response.accounts.Count -gt 0) {
                $account = $response.accounts[0]
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
        apiId = 12345678
        apiHash = "abcdef1234567890abcdef1234567890"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts" -Method Post -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Success "✓ Create account successful"
        Show-Response $response $statusCode

        # Сохраняем ID для последующих тестов
        $script:TestAccountId = $response.id

        # Проверка структуры ответа
        if ($response.id -and
            $response.name -eq "Test Account" -and
            $response.phoneNumber -eq "+79991234567" -and
            $response.status -eq "offline") {
            Write-Success "✓ Account created with correct data"
        } else {
            Write-Error "✗ Account data is incorrect"
            Write-Info "Expected: id exists, name='Test Account', phoneNumber='+79991234567', status='offline'"
            Write-Info "Got: id=$($response.id), name='$($response.name)', phoneNumber='$($response.phoneNumber)', status='$($response.status)'"
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
        apiId = 12345678
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

            if ($errorDetails.detail -like "*уже существует*") {
                Write-Success "✓ Error message is correct"
            } else {
                Write-Error "✗ Error message is incorrect"
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
        apiId = 12345678
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

            # Проверяем новый формат ответа
            if ($errorDetails.error -eq "VALIDATION_ERROR") {
                Write-Success "✓ Error code is correct (VALIDATION_ERROR)"

                # Проверяем что сообщение содержит информацию о формате телефона
                if ($errorDetails.message -like "*формат*" -or $errorDetails.message -like "*телефон*") {
                    Write-Success "✓ Error message is correct"
                } else {
                    Write-Error "✗ Error message is incorrect"
                    Write-Info "Expected message about phone format"
                    Write-Info "Got: $($errorDetails.message)"
                }
            } else {
                Write-Error "✗ Error code is incorrect"
                Write-Info "Expected: VALIDATION_ERROR"
                Write-Info "Got: $($errorDetails.error)"
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
        apiId = 87654321
        apiHash = "new_hash_1234567890abcdef1234567890ab"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts/$script:TestAccountId" -Method Patch -Headers $authHeaders -Body $body -StatusCodeVariable statusCode
        Write-Success "✓ Update account successful"
        Show-Response $response $statusCode

        # Проверка обновленных данных
        if ($response.name -eq "Updated Test Account" -and $response.apiId -eq 87654321) {
            Write-Success "✓ Account updated with correct data"
        } else {
            Write-Error "✗ Account data is incorrect"
            Write-Info "Expected: name='Updated Test Account', apiId=87654321"
            Write-Info "Got: name='$($response.name)', apiId=$($response.apiId)"
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

            if ($errorDetails.detail -like "*не найден*") {
                Write-Success "✓ Error message is correct"
            } else {
                Write-Error "✗ Error message is incorrect"
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

            if ($errorDetails.detail -like "*не найден*") {
                Write-Success "✓ Error message is correct"
            } else {
                Write-Error "✗ Error message is incorrect"
            }
        }
    }
}

function Run-AllTests {
    Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║   COMANASO ACCOUNTS API TESTS          ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Yellow

    # Убедимся что тестовый пользователь существует
    if (-not (Setup-TestUser)) {
        Write-Error "✗ Cannot run tests without test user"
        return
    }

    Write-Host "`n=== CLEANUP BEFORE TESTS ===" -ForegroundColor Yellow
    Cleanup-TestAccounts
    Start-Sleep -Seconds 1

    Write-Host "`n=== POSITIVE TESTS ===" -ForegroundColor Yellow
    Test-GetAccounts; Start-Sleep -Seconds 1
    Test-CreateAccount; Start-Sleep -Seconds 1
    Test-GetAccounts; Start-Sleep -Seconds 1

    Write-Host "`n=== NEGATIVE TESTS ===" -ForegroundColor Yellow
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

    Write-Host "`n=== CLEANUP AFTER TESTS ===" -ForegroundColor Yellow
    Cleanup-TestUsers

    Write-Host "`n╔════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║   TESTS COMPLETED                      ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════╝`n" -ForegroundColor Yellow
}

function Show-Menu {
    Write-Host "`n=== COMANASO ACCOUNTS API TESTER ===" -ForegroundColor Yellow
    Write-Host "Auth Status: $(if ($script:AuthToken) { 'Logged in' } else { 'Not logged in' })" -ForegroundColor $(if ($script:AuthToken) { 'Green' } else { 'Red' })
    Write-Host ""
    Write-Host "1. Login (get auth token)"
    Write-Host "2. Cleanup Test Accounts"
    Write-Host "3. Get Accounts List"
    Write-Host "4. Create Account"
    Write-Host "5. Create Duplicate Account (negative test)"
    Write-Host "6. Create Account with Invalid Phone (negative test)"
    Write-Host "7. Update Account"
    Write-Host "8. Update Non-Existent Account (negative test)"
    Write-Host "9. Delete Account"
    Write-Host "10. Delete Non-Existent Account (negative test)"
    Write-Host "11. Run All Tests"
    Write-Host "12. Cleanup Test Users"
    Write-Host "0. Exit"
    Write-Host ""
}

if ($args.Count -eq 0) {
    do {
        Show-Menu
        $choice = Read-Host "Select option"
        switch ($choice) {
            "1" { Test-Login }
            "2" { Cleanup-TestAccounts }
            "3" { Test-GetAccounts }
            "4" { Test-CreateAccount }
            "5" { Test-CreateDuplicateAccount }
            "6" { Test-CreateAccountInvalidPhone }
            "7" { Test-UpdateAccount }
            "8" { Test-UpdateNonExistentAccount }
            "9" { Test-DeleteAccount }
            "10" { Test-DeleteNonExistentAccount }
            "11" { Run-AllTests }
            "12" { Cleanup-TestUsers }
            "0" { Write-Host "Exiting..." }
            default { Write-Host "Invalid option" -ForegroundColor Red }
        }
        if ($choice -ne "0") { Read-Host "`nPress Enter to continue" }
    } while ($choice -ne "0")
}
else {
    Run-AllTests
}
