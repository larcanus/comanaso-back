# Конфигурация
$BASE_URL = "http://localhost:8000/api"
$HEADERS = @{
    "Content-Type" = "application/json"
}

# Глобальная переменная для хранения токена
$script:AuthToken = $null
$script:TestAccountId = $null
$script:SecondUserToken = $null

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

# Функция для настройки второго тестового пользователя
function Setup-SecondTestUser {
    Write-Info "`n=== SETUP: Ensure second test user exists ==="

    $login = "test2@example.com"
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

        $script:SecondUserToken = $response.token
        Write-Success "✓ Second test user exists, logged in successfully"
        return $true
    }
    catch {
        # Пользователь не существует, создаем
        Write-Info "Second test user doesn't exist, creating..."

        $registerBody = @{
            login = $login
            password = $password
        } | ConvertTo-Json

        try {
            $registerResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/register" `
                -Method Post `
                -Headers $HEADERS `
                -Body $registerBody

            Write-Success "✓ Second test user created successfully"

            # Теперь логинимся
            $loginResponse = Invoke-RestMethod -Uri "$BASE_URL/auth/login" `
                -Method Post `
                -Headers $HEADERS `
                -Body $loginBody

            $script:SecondUserToken = $loginResponse.token
            Write-Success "✓ Logged in with second test user"
            return $true
        }
        catch {
            Write-Error "✗ Failed to create second test user: $($_.Exception.Message)"
            return $false
        }
    }
}

function Get-SecondUserAuthHeaders {
    if (-not $script:SecondUserToken) {
        Write-Error "✗ No second user auth token. Setup second user first"
        return $null
    }
    $headers = $HEADERS.Clone()
    $headers["Authorization"] = "Bearer $script:SecondUserToken"
    return $headers
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

            if ($errorDetails.error -eq "ACCOUNT_ALREADY_EXISTS") {
                Write-Success "✓ Error code is correct (ACCOUNT_ALREADY_EXISTS)"

                if ($errorDetails.message -like "*уже существует*") {
                    Write-Success "✓ Error message is correct"
                } else {
                    Write-Error "✗ Error message is incorrect"
                    Write-Info "Expected message about account already exists"
                    Write-Info "Got: $($errorDetails.message)"
                }
            } else {
                Write-Error "✗ Error code is incorrect"
                Write-Info "Expected: ACCOUNT_ALREADY_EXISTS"
                Write-Info "Got: $($errorDetails.error)"
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

            if ($errorDetails.error -eq "ACCOUNT_NOT_FOUND") {
                Write-Success "✓ Error code is correct (ACCOUNT_NOT_FOUND)"

                if ($errorDetails.message -like "*не найден*") {
                    Write-Success "✓ Error message is correct"
                } else {
                    Write-Error "✗ Error message is incorrect"
                    Write-Info "Expected message about account not found"
                    Write-Info "Got: $($errorDetails.message)"
                }
            } else {
                Write-Error "✗ Error code is incorrect"
                Write-Info "Expected: ACCOUNT_NOT_FOUND"
                Write-Info "Got: $($errorDetails.error)"
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

            if ($errorDetails.error -eq "ACCOUNT_NOT_FOUND") {
                Write-Success "✓ Error code is correct (ACCOUNT_NOT_FOUND)"

                if ($errorDetails.message -like "*не найден*") {
                    Write-Success "✓ Error message is correct"
                } else {
                    Write-Error "✗ Error message is incorrect"
                    Write-Info "Expected message about account not found"
                    Write-Info "Got: $($errorDetails.message)"
                }
            } else {
                Write-Error "✗ Error code is incorrect"
                Write-Info "Expected: ACCOUNT_NOT_FOUND"
                Write-Info "Got: $($errorDetails.error)"
            }
        }
    }
}

function Test-DeleteOtherUserAccount {
    Write-Info "`n=== TEST: Delete Other User's Account ==="

    # Создаем второго пользователя
    if (-not (Setup-SecondTestUser)) {
        Write-Error "✗ Failed to setup second test user"
        return
    }

    # Убедимся что первый пользователь залогинен и имеет аккаунт
    if (-not $script:TestAccountId) {
        Write-Info "Creating account for first user..."
        Test-CreateAccount | Out-Null
        if (-not $script:TestAccountId) {
            Write-Error "✗ Failed to create account for first user"
            return
        }
    }

    # Получаем заголовки второго пользователя
    $secondUserHeaders = Get-SecondUserAuthHeaders
    if (-not $secondUserHeaders) { return }

    # Пытаемся удалить аккаунт первого пользователя от имени второго
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts/$script:TestAccountId" -Method Delete -Headers $secondUserHeaders -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Write-Info "Status Code: $statusCode"
    }
    catch {
        Write-Success "✓ Correctly rejected delete of other user's account"
        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Info "Error response:"
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

            if ($errorDetails.error -eq "ACCOUNT_NOT_FOUND") {
                Write-Success "✓ Error code is correct (ACCOUNT_NOT_FOUND)"
                Write-Success "✓ Second user cannot see first user's account (good isolation)"

                if ($errorDetails.message -like "*не найден*") {
                    Write-Success "✓ Error message is correct"
                } else {
                    Write-Error "✗ Error message is incorrect"
                    Write-Info "Expected message about account not found"
                    Write-Info "Got: $($errorDetails.message)"
                }
            } else {
                Write-Error "✗ Error code is incorrect"
                Write-Info "Expected: ACCOUNT_NOT_FOUND"
                Write-Info "Got: $($errorDetails.error)"
            }
        }
    }
}

# ===== AUTHORIZATION TESTS (401) =====

function Test-GetAccountsWithoutAuth {
    Write-Info "`n=== TEST: Get Accounts Without Authorization ==="
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts" -Method Get -Headers $HEADERS -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected request without authorization"
        if ($_.Exception.Response.StatusCode -eq 401) {
            Write-Success "✓ Correct status code (401)"
        } else {
            Write-Error "✗ Incorrect status code (expected 401)"
            Write-Info "Got: $($_.Exception.Response.StatusCode)"
        }

        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Info "Error response:"
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

            if ($errorDetails.error -eq "UNAUTHORIZED") {
                Write-Success "✓ Error code is correct (UNAUTHORIZED)"
            } else {
                Write-Error "✗ Error code is incorrect"
                Write-Info "Expected: UNAUTHORIZED"
                Write-Info "Got: $($errorDetails.error)"
            }
        }
    }
}

function Test-CreateAccountWithoutAuth {
    Write-Info "`n=== TEST: Create Account Without Authorization ==="
    $body = @{
        name = "Test Account"
        phoneNumber = "+79991234567"
        apiId = 12345678
        apiHash = "abcdef1234567890abcdef1234567890"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected request without authorization"
        if ($_.Exception.Response.StatusCode -eq 401) {
            Write-Success "✓ Correct status code (401)"
        } else {
            Write-Error "✗ Incorrect status code (expected 401)"
            Write-Info "Got: $($_.Exception.Response.StatusCode)"
        }

        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Info "Error response:"
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

            if ($errorDetails.error -eq "UNAUTHORIZED") {
                Write-Success "✓ Error code is correct (UNAUTHORIZED)"
            } else {
                Write-Error "✗ Error code is incorrect"
                Write-Info "Expected: UNAUTHORIZED"
                Write-Info "Got: $($errorDetails.error)"
            }
        }
    }
}

function Test-UpdateAccountWithoutAuth {
    Write-Info "`n=== TEST: Update Account Without Authorization ==="
    $body = @{
        name = "Should Not Work"
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts/1" -Method Patch -Headers $HEADERS -Body $body -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Show-Response $response $statusCode
    }
    catch {
        Write-Success "✓ Correctly rejected request without authorization"
        if ($_.Exception.Response.StatusCode -eq 401) {
            Write-Success "✓ Correct status code (401)"
        } else {
            Write-Error "✗ Incorrect status code (expected 401)"
            Write-Info "Got: $($_.Exception.Response.StatusCode)"
        }

        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Info "Error response:"
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host
        }
    }
}

function Test-DeleteAccountWithoutAuth {
    Write-Info "`n=== TEST: Delete Account Without Authorization ==="
    try {
        $response = Invoke-RestMethod -Uri "$BASE_URL/accounts/1" -Method Delete -Headers $HEADERS -StatusCodeVariable statusCode
        Write-Error "✗ Should have failed but succeeded"
        Write-Info "Status Code: $statusCode"
    }
    catch {
        Write-Success "✓ Correctly rejected request without authorization"
        if ($_.Exception.Response.StatusCode -eq 401) {
            Write-Success "✓ Correct status code (401)"
        } else {
            Write-Error "✗ Incorrect status code (expected 401)"
            Write-Info "Got: $($_.Exception.Response.StatusCode)"
        }

        if ($_.ErrorDetails.Message) {
            $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Info "Error response:"
            $errorDetails | ConvertTo-Json -Depth 10 | Write-Host

            if ($errorDetails.error -eq "UNAUTHORIZED") {
                Write-Success "✓ Error code is correct (UNAUTHORIZED)"
            } else {
                Write-Error "✗ Error code is incorrect"
                Write-Info "Expected: UNAUTHORIZED"
                Write-Info "Got: $($errorDetails.error)"
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

    Write-Host "`n=== AUTHORIZATION TESTS (401) ===" -ForegroundColor Yellow
    Test-GetAccountsWithoutAuth; Start-Sleep -Seconds 1
    Test-CreateAccountWithoutAuth; Start-Sleep -Seconds 1
    Test-UpdateAccountWithoutAuth; Start-Sleep -Seconds 1
    Test-DeleteAccountWithoutAuth; Start-Sleep -Seconds 1

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
    Write-Host "`n=== DELETE TESTS ===" -ForegroundColor Yellow
    Test-DeleteOtherUserAccount; Start-Sleep -Seconds 1
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
    Write-Host "1. Run All Tests"
    Write-Host "2. Login (get auth token)"
    Write-Host "3. Cleanup Test Accounts"
    Write-Host "4. Get Accounts List"
    Write-Host "5. Create Account"
    Write-Host "6. Create Duplicate Account (negative test)"
    Write-Host "7. Create Account with Invalid Phone (negative test)"
    Write-Host "8. Update Account"
    Write-Host "9. Update Non-Existent Account (negative test)"
    Write-Host "10. Delete Account"
    Write-Host "11. Delete Non-Existent Account (negative test)"
    Write-Host "12. Get Accounts Without Auth (401 test)"
    Write-Host "13. Create Account Without Auth (401 test)"
    Write-Host "14. Update Account Without Auth (401 test)"
    Write-Host "15. Delete Account Without Auth (401 test)"
    Write-Host "16. Cleanup Test Users"
    Write-Host "0. Exit"
    Write-Host ""
}

if ($args.Count -eq 0) {
    do {
        Show-Menu
        $choice = Read-Host "Select option"
        switch ($choice) {
            "1" { Run-AllTests }
            "2" { Test-Login }
            "3" { Cleanup-TestAccounts }
            "4" { Test-GetAccounts }
            "5" { Test-CreateAccount }
            "6" { Test-CreateDuplicateAccount }
            "7" { Test-CreateAccountInvalidPhone }
            "8" { Test-UpdateAccount }
            "9" { Test-UpdateNonExistentAccount }
            "10" { Test-DeleteAccount }
            "11" { Test-DeleteNonExistentAccount }
            "12" { Test-GetAccountsWithoutAuth }
            "13" { Test-CreateAccountWithoutAuth }
            "14" { Test-UpdateAccountWithoutAuth }
            "15" { Test-DeleteAccountWithoutAuth }
            "16" { Cleanup-TestUsers }
            "0" { Write-Host "Exiting..." }
            default { Write-Host "Invalid option" -ForegroundColor Red }
        }
        if ($choice -ne "0") { Read-Host "`nPress Enter to continue" }
    } while ($choice -ne "0")
}
else {
    Run-AllTests
}