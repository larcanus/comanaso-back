# Простые тесты для Telegram роутов (connect, dialogs, disconnect, logout, data)
$BASE_URL = "http://localhost:8000/api"
$HEADERS = @{ "Content-Type" = "application/json" }

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
    param($phone = "+79991234567", $name = "Test Telegram Account")
    $h = Get-AuthHeaders
    if (-not $h) { return $null }

    # Попробуем найти существующий тест-аккаунт
    try {
        $list = Invoke-RestMethod -Uri "$BASE_URL/accounts" -Method Get -Headers $h -StatusCodeVariable status
        Write-Info "List accounts returned status $status"
        if ($list -and $list.accounts) {
            foreach ($a in $list.accounts) {
                if ($a.phoneNumber -eq $phone) {
                    $script:TestAccountId = $a.id
                    Write-Success "Found existing test account id=$script:TestAccountId"
                    return $script:TestAccountId
                }
            }
        }
    } catch {
        Write-Warning "Could not list accounts: $($_.Exception.Message)"
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try { ($_.ErrorDetails.Message | ConvertFrom-Json) | ConvertTo-Json -Depth 10 | Write-Host } catch { Write-Host $_.ErrorDetails.Message }
        }
    }

    # Создать новый
    $body = @{
        name = $name
        phoneNumber = $phone
        apiId = 12345678
        apiHash = "abcdef1234567890abcdef1234567890"
    } | ConvertTo-Json

    try {
        $resp = Invoke-RestMethod -Uri "$BASE_URL/accounts" -Method Post -Headers $h -Body $body -StatusCodeVariable status
        Write-Success "Created test account id=$($resp.id) (status $status)"
        $script:TestAccountId = $resp.id
        return $script:TestAccountId
    } catch {
        Write-Error "Failed to create test account: $($_.Exception.Message)"
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try { ($_.ErrorDetails.Message | ConvertFrom-Json) | ConvertTo-Json -Depth 10 | Write-Host } catch { Write-Host $_.ErrorDetails.Message }
        }
        return $null
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
        # Если в теле есть поле error — дать подсказку
        if ($resp -and ($resp.error -or $resp.status)) {
            if ($resp.error -eq "INVALID_API_CREDENTIALS") {
                Write-Warning "Invalid API credentials detected. Проверьте apiId/apiHash для аккаунта $script:TestAccountId."
            } elseif ($resp.error -eq "TELETHON_ERROR" -and $resp.message -match "api_id\/api_hash") {
                Write-Warning "Telethon returned api_id/api_hash error. Проверьте apiId/apiHash в настройках аккаунта."
            }
        }
    } catch {
        Write-Error "Connect failed: $($_.Exception.Message)"
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try {
                $err = $_.ErrorDetails.Message | ConvertFrom-Json
                Show-Response $err $_.StatusCode
                if ($err.error -eq "INVALID_API_CREDENTIALS" -or ($err.error -eq "TELETHON_ERROR" -and $err.message -match "api_id\/api_hash")) {
                    Write-Warning "Invalid API credentials detected in error response. Проверьте apiId/apiHash для аккаунта $script:TestAccountId."
                }
            } catch {
                Write-Host $_.ErrorDetails.Message
            }
        }
    }
}

function Test-GetDialogs {
    if (-not $script:TestAccountId) { Write-Error "No account id"; return }
    $h = Get-AuthHeaders
    Write-Host "`n--- TEST: GET DIALOGS (account id: $script:TestAccountId) ---" -ForegroundColor Yellow
    try {
        $resp = Invoke-RestMethod -Uri "$BASE_URL/accounts/$script:TestAccountId/dialogs?limit=10" -Method Get -Headers $h -StatusCodeVariable status
        Show-Response $resp $status
    } catch {
        Write-Error "Get dialogs failed: $($_.Exception.Message)"
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try { ($_.ErrorDetails.Message | ConvertFrom-Json) | ConvertTo-Json -Depth 10 | Write-Host } catch { Write-Host $_.ErrorDetails.Message }
        }
    }
}

function Test-GetData {
    if (-not $script:TestAccountId) { Write-Error "No account id"; return }
    $h = Get-AuthHeaders
    Write-Host "`n--- TEST: GET DATA (account id: $script:TestAccountId) ---" -ForegroundColor Yellow
    try {
        $resp = Invoke-RestMethod -Uri "$BASE_URL/accounts/$script:TestAccountId/data" -Method Get -Headers $h -StatusCodeVariable status
        Show-Response $resp $status
    } catch {
        Write-Error "Get data failed: $($_.Exception.Message)"
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try { ($_.ErrorDetails.Message | ConvertFrom-Json) | ConvertTo-Json -Depth 10 | Write-Host } catch { Write-Host $_.ErrorDetails.Message }
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
        if ($status -eq 200) { Write-Success "Disconnected OK" } else { Write-Warning "Disconnect returned $status" }
    } catch {
        Write-Error "Disconnect failed: $($_.Exception.Message)"
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try { ($_.ErrorDetails.Message | ConvertFrom-Json) | ConvertTo-Json -Depth 10 | Write-Host } catch { Write-Host $_.ErrorDetails.Message }
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
    } catch {
        Write-Error "Logout failed: $($_.Exception.Message)"
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
            try { ($_.ErrorDetails.Message | ConvertFrom-Json) | ConvertTo-Json -Depth 10 | Write-Host } catch { Write-Host $_.ErrorDetails.Message }
        }
    }
}

function Run-AllTests {
    Write-Host "`n=== TELEGRAM ROUTES DETAILED SMOKE TESTS ===" -ForegroundColor Yellow
    if (-not (Setup-TestUser)) { Write-Error "Cannot setup user"; return }
    Start-Sleep -Seconds 1
    if (-not (Ensure-TestAccount)) { Write-Error "Cannot ensure account"; return }
    Start-Sleep -Seconds 1

    Test-Connect; Start-Sleep -Seconds 1
    Test-GetDialogs; Start-Sleep -Seconds 1
    Test-GetData; Start-Sleep -Seconds 1
    Test-Disconnect; Start-Sleep -Seconds 1
    Test-Logout; Start-Sleep -Seconds 1

    Write-Host "`n=== TESTS COMPLETED ===" -ForegroundColor Green
}

# Если запущен без аргументов — выполнить все
if ($args.Count -eq 0) {
    Run-AllTests
} else {
    Run-AllTests
}
