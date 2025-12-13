# Простые тесты для Telegram роутов (connect, dialogs, disconnect, logout, data)
$BASE_URL = "http://localhost:8000/api"
$HEADERS = @{ "Content-Type" = "application/json" }

# Получаем реальные API credentials из переменных окружения
$envApiId = [int]$env:TELEGRAM_API_ID
$envApiHash = $env:TELEGRAM_API_HASH
$envPhone = $env:TELEGRAM_TEST_PHONE

# Проверяем наличие переменных окружения
if (-not $envApiId -or -not $envApiHash -or -not $envPhone) {
    Write-Error "Необходимо установить переменные окружения:"
    Write-Error "  TELEGRAM_API_ID - ваш API ID из https://my.telegram.org"
    Write-Error "  TELEGRAM_API_HASH - ваш API Hash из https://my.telegram.org"
    Write-Error "  TELEGRAM_TEST_PHONE - номер телефона для тестирования (формат: +79991234567)"
    Write-Error ""
    Write-Error "Пример установки в PowerShell:"
    Write-Error "  `$env:TELEGRAM_API_ID = 'ваш_api_id'"
    Write-Error "  `$env:TELEGRAM_API_HASH = 'ваш_api_hash'"
    Write-Error "  `$env:TELEGRAM_TEST_PHONE = '+79991234567'"
    exit 1
}

$script:AuthToken = $null
$script:TestAccountId = $null

function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }

function Show-Response {
    param($body, $status)
    if ($status -ge 200 -and $status -lt 300) {
        Write-Success "Status: $status"
    } else {
        Write-Error "Status: $status"
    }
    try {
        if ($body -is [string]) {
            $parsed = $null
            try { $parsed = $body | ConvertFrom-Json } catch { $parsed = $body }
            $parsed | ConvertTo-Json -Depth 10 | Write-Host
        } else {
            $body | ConvertTo-Json -Depth 10 | Write-Host
        }
    } catch {
        Write-Host $body
    }
}

# Логин/создание тестового пользователя
function Setup-TestUser {
    $login = "test@example.com"
    $password = "Password123"
    $body = @{ login = $login; password = $password } | ConvertTo-Json

    try {
        $resp = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable status
        Write-Success "Login successful (status $status)"
        $script:AuthToken = $resp.token
        return $true
    } catch {
        Write-Info "Login failed, attempting register: $($_.Exception.Message)"
        try {
            $reg = Invoke-RestMethod -Uri "$BASE_URL/auth/register" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable regStatus
            Write-Success "Register successful (status $regStatus)"
            $resp = Invoke-RestMethod -Uri "$BASE_URL/auth/login" -Method Post -Headers $HEADERS -Body $body -StatusCodeVariable status
            Write-Success "Login after register successful (status $status)"
            $script:AuthToken = $resp.token
            return $true
        } catch {
            Write-Error "Failed to setup test user: $($_.Exception.Message)"
            # Попытка показать тело ошибки если есть
            if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
                try { ($_.ErrorDetails.Message | ConvertFrom-Json) | ConvertTo-Json -Depth 10 | Write-Host } catch { Write-Host $_.ErrorDetails.Message }
            }
            return $false
        }
    }
}

function Get-AuthHeaders {
    if (-not $script:AuthToken) { Write-Error "No token"; return $null }
    $h = $HEADERS.Clone()
    $h["Authorization"] = "Bearer $script:AuthToken"
    return $h
}

function Ensure-TestAccount {
    Write-Host "Ensuring test account exists..." -ForegroundColor Cyan
    $h = Get-AuthHeaders

    # Получаем список аккаунтов
    try {
        $accounts = Invoke-RestMethod -Uri "$BASE_URL/accounts" -Method Get -Headers $h -StatusCodeVariable status
        Write-Host "List accounts returned status $status" -ForegroundColor Gray

        # Ищем аккаунт с нашим номером
        $existing = $accounts | Where-Object { $_.phoneNumber -eq $envPhone }
        if ($existing) {
            $script:TestAccountId = $existing.id
            Write-Host "✅ Found existing test account id=$($existing.id)" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Host "Failed to list accounts: $($_.Exception.Message)" -ForegroundColor Yellow
    }

    # Создаем новый аккаунт
    $body = @{
        name = "Test Telegram Account"
        phoneNumber = $envPhone
        apiId = [int64]$envApiId
        apiHash = $envApiHash
    } | ConvertTo-Json

    try {
        $account = Invoke-RestMethod -Uri "$BASE_URL/accounts" -Method Post -Headers $h -Body $body -StatusCodeVariable status
        $script:TestAccountId = $account.id
        Write-Host "✅ Created test account id=$($account.id) (status $status)" -ForegroundColor Green
        return $true
    } catch {
        # Если аккаунт уже существует - это не ошибка!
        if ($_.Exception.Response.StatusCode -eq 400) {
            try {
                $errorDetails = $_.ErrorDetails.Message | ConvertFrom-Json
                if ($errorDetails.error -eq "ACCOUNT_ALREADY_EXISTS") {
                    Write-Host "⚠️ Account already exists, fetching it..." -ForegroundColor Yellow
                    # Повторно получаем список и находим аккаунт
                    $accounts = Invoke-RestMethod -Uri "$BASE_URL/accounts" -Method Get -Headers $h
                    $existing = $accounts | Where-Object { $_.phoneNumber -eq $envPhone }
                    if ($existing) {
                        $script:TestAccountId = $existing.id
                        Write-Host "✅ Using existing account id=$($existing.id)" -ForegroundColor Green
                        return $true
                    }
                }
            } catch {
                # Игнорируем ошибки парсинга
            }
        }

        Write-Host "❌ Failed to create test account: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            $_.ErrorDetails.Message | ConvertFrom-Json | ConvertTo-Json | Write-Host
        }
        return $false
    }
}

function Test-Connect {
    if (-not $script:TestAccountId) { Write-Error "No account id"; return }
    $h = Get-AuthHeaders
    $body = @{ } | ConvertTo-Json
    Write-Host "`n--- TEST: CONNECT (account id: $script:TestAccountId) ---" -ForegroundColor Yellow
    try {
        $resp = Invoke-RestMethod -Uri "$BASE_URL/accounts/$script:TestAccountId/connect" -Method Post -Headers $h -Body $body -StatusCodeVariable status
        Show-Response $resp $status

        # Проверка обязательных полей согласно контракту
        if ($resp.status -eq "online" -or $resp.status -eq "code_required") {
            if (-not $resp.message) {
                Write-Warning "⚠️ Поле 'message' отсутствует в ответе!"
            } else {
                Write-Success "✅ Корректный ответ: status=$($resp.status), message присутствует"
            }
        }

        # Если в теле есть поле error — дать подсказку
        if ($resp -and $resp.error) {
            if ($resp.error -eq "INVALID_API_CREDENTIALS") {
                Write-Warning "Invalid API credentials detected. Проверьте apiId/apiHash для аккаунта $script:TestAccountId."
                Write-Warning "Убедитесь, что вы используете реальные API credentials из https://my.telegram.org"
            } elseif ($resp.error -eq "ALREADY_CONNECTED") {
                Write-Info "Аккаунт уже подключен (status code должен быть 409)"
            }
        }
    } catch {
        Write-Error "Connect failed: $($_.Exception.Message)"
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try {
                $err = $_.ErrorDetails.Message | ConvertFrom-Json
                Show-Response $err $_.Exception.Response.StatusCode.value__
                if ($err.error -eq "INVALID_API_CREDENTIALS") {
                    Write-Warning "Invalid API credentials detected in error response."
                } elseif ($err.error -eq "ALREADY_CONNECTED" -and $_.Exception.Response.StatusCode.value__ -ne 409) {
                    Write-Warning "⚠️ ALREADY_CONNECTED должен возвращать status code 409!"
                }
            } catch {
                Write-Host $_.ErrorDetails.Message
            }
        }
    }
}

function Test-VerifyCode {
    param([string]$code = "12345")
    if (-not $script:TestAccountId) { Write-Error "No account id"; return }
    $h = Get-AuthHeaders
    $body = @{ code = $code } | ConvertTo-Json
    Write-Host "`n--- TEST: VERIFY CODE (account id: $script:TestAccountId) ---" -ForegroundColor Yellow
    Write-Info "Отправка кода: $code"
    try {
        $resp = Invoke-RestMethod -Uri "$BASE_URL/accounts/$script:TestAccountId/verify-code" -Method Post -Headers $h -Body $body -StatusCodeVariable status
        Show-Response $resp $status

        # Проверка обязательных полей
        if ($resp.status -eq "connected") {
            if (-not $resp.message) {
                Write-Warning "⚠️ Поле 'message' отсутствует!"
            } else {
                Write-Success "✅ Успешное подключение без 2FA"
            }
        } elseif ($resp.status -eq "password_required") {
            if (-not $resp.message) {
                Write-Warning "⚠️ Поле 'message' отсутствует!"
            }
            if ($resp.PSObject.Properties.Name -contains "passwordHint") {
                Write-Info "Подсказка пароля: $($resp.passwordHint)"
            } else {
                Write-Warning "⚠️ Поле 'passwordHint' отсутствует (может быть null по контракту)"
            }
            Write-Success "✅ Требуется 2FA пароль"
        }
    } catch {
        Write-Error "Verify code failed: $($_.Exception.Message)"
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try {
                $err = $_.ErrorDetails.Message | ConvertFrom-Json
                Show-Response $err $_.Exception.Response.StatusCode.value__
                if ($err.error -eq "INVALID_CODE") {
                    Write-Info "Код неверный (ожидаемое поведение для тестового кода)"
                } elseif ($err.error -eq "EXPIRED_CODE") {
                    Write-Warning "Код истек - нужно запросить новый через /connect"
                }
            } catch {
                Write-Host $_.ErrorDetails.Message
            }
        }
    }
}

function Test-VerifyPassword {
    param([string]$password = "test_password")
    if (-not $script:TestAccountId) { Write-Error "No account id"; return }
    $h = Get-AuthHeaders
    $body = @{ password = $password } | ConvertTo-Json
    Write-Host "`n--- TEST: VERIFY PASSWORD (account id: $script:TestAccountId) ---" -ForegroundColor Yellow
    Write-Warning "Используется тестовый пароль - для реального теста передайте параметр"
    try {
        $resp = Invoke-RestMethod -Uri "$BASE_URL/accounts/$script:TestAccountId/verify-password" -Method Post -Headers $h -Body $body -StatusCodeVariable status
        Show-Response $resp $status

        # Проверка обязательных полей
        if ($resp.status -eq "online") {
            if (-not $resp.message) {
                Write-Warning "⚠️ Поле 'message' отсутствует!"
            } else {
                Write-Success "✅ Успешное подключение с 2FA"
            }
        }
    } catch {
        Write-Error "Verify password failed: $($_.Exception.Message)"
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try {
                $err = $_.ErrorDetails.Message | ConvertFrom-Json
                Show-Response $err $_.Exception.Response.StatusCode.value__
                if ($err.error -eq "INVALID_PASSWORD") {
                    Write-Info "Пароль неверный (ожидаемое поведение для тестового пароля)"
                }
            } catch {
                Write-Host $_.ErrorDetails.Message
            }
        }
    }
}

function Test-Disconnect {
    if (-not $script:TestAccountId) { Write-Error "No account id"; return }
    $h = Get-AuthHeaders
    Write-Host "`n--- TEST: DISCONNECT (account id: $script:TestAccountId) ---" -ForegroundColor Yellow
    try {
        $resp = Invoke-RestMethod -Uri "$BASE_URL/accounts/$script:TestAccountId/disconnect" -Method Post -Headers $h -Body "{}" -StatusCodeVariable status
        Show-Response $resp $status

        # Проверка обязательных полей согласно контракту
        if ($status -eq 200) {
            if ($resp.status -ne "disconnected") {
                Write-Warning "⚠️ Поле 'status' должно быть 'disconnected', получено: $($resp.status)"
            }
            if (-not $resp.message) {
                Write-Warning "⚠️ Поле 'message' отсутствует!"
            } else {
                Write-Success "✅ Аккаунт отключен: $($resp.message)"
            }
        } else {
            Write-Warning "Disconnect returned unexpected status $status"
        }
    } catch {
        Write-Error "Disconnect failed: $($_.Exception.Message)"
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try {
                $err = $_.ErrorDetails.Message | ConvertFrom-Json
                Show-Response $err $_.Exception.Response.StatusCode.value__
            } catch {
                Write-Host $_.ErrorDetails.Message
            }
        }
    }
}

function Test-Logout {
    if (-not $script:TestAccountId) { Write-Error "No account id"; return }
    $h = Get-AuthHeaders
    Write-Host "`n--- TEST: LOGOUT (account id: $script:TestAccountId) ---" -ForegroundColor Yellow
    try {
        $resp = Invoke-RestMethod -Uri "$BASE_URL/accounts/$script:TestAccountId/logout" -Method Post -Headers $h -Body "{}" -StatusCodeVariable status
        Show-Response $resp $status

        # Проверка обязательных полей согласно контракту
        if ($status -eq 200) {
            if ($resp.status -ne "logged_out") {
                Write-Warning "⚠️ Поле 'status' должно быть 'logged_out', получено: $($resp.status)"
            }
            if (-not $resp.message) {
                Write-Warning "⚠️ Поле 'message' отсутствует!"
            } else {
                Write-Success "✅ Выход выполнен: $($resp.message)"
            }
        }
    } catch {
        Write-Error "Logout failed: $($_.Exception.Message)"
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try {
                $err = $_.ErrorDetails.Message | ConvertFrom-Json
                Show-Response $err $_.Exception.Response.StatusCode.value__
                if ($err.error -eq "ACCOUNT_NOT_CONNECTED") {
                    Write-Info "Аккаунт не подключен (ожидаемая ошибка если logout вызван повторно)"
                }
            } catch {
                Write-Host $_.ErrorDetails.Message
            }
        }
    }
}

function Run-AllTests {
    Write-Host "`n=== TELEGRAM CONNECTION TESTS (базовые операции) ===" -ForegroundColor Yellow
    Write-Host "Using API ID: $envApiId" -ForegroundColor Cyan
    Write-Host "Using Phone: $envPhone" -ForegroundColor Cyan

    if (-not (Setup-TestUser)) { Write-Error "Cannot setup user"; return }
    Start-Sleep -Seconds 1
    if (-not (Ensure-TestAccount)) { Write-Error "Cannot ensure account"; return }
    Start-Sleep -Seconds 1

    # Тест 1: Подключение
    Test-Connect
    Start-Sleep -Seconds 2

    # Тест 2: Проверка кода (с заведомо неверным кодом для демонстрации ошибки)
    Write-Host "`nℹ️ Следующий тест покажет ошибку INVALID_CODE (ожидаемое поведение)" -ForegroundColor Cyan
    Test-VerifyCode -code "12345"
    Start-Sleep -Seconds 2

    # Тест 3: Проверка пароля (с заведомо неверным паролем для демонстрации ошибки)
    Write-Host "`nℹ️ Следующий тест покажет ошибку INVALID_PASSWORD (ожидаемое поведение)" -ForegroundColor Cyan
    Test-VerifyPassword -password "test_password"
    Start-Sleep -Seconds 2

    # Тест 4: Отключение
    Test-Disconnect
    Start-Sleep -Seconds 2

    # Тест 5: Выход
    Test-Logout
    Start-Sleep -Seconds 1

    Write-Host "`n=== TESTS COMPLETED ===" -ForegroundColor Green
    Write-Host "⚠️ Для полноценного теста авторизации нужно:" -ForegroundColor Yellow
    Write-Host "   1. Запустить Test-Connect" -ForegroundColor Yellow
    Write-Host "   2. Получить реальный код из Telegram" -ForegroundColor Yellow
    Write-Host "   3. Вызвать Test-VerifyCode с реальным кодом" -ForegroundColor Yellow
    Write-Host "   4. Если нужен 2FA - вызвать Test-VerifyPassword с реальным паролем" -ForegroundColor Yellow
}

# Если запущен без аргументов — выполнить все
if ($args.Count -eq 0) {
    Run-AllTests
} else {
    Run-AllTests
}