Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$ErrorActionPreference = "Stop"

function New-Secret([int]$length = 48) {
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_!@#$%^&*()"
    $rng = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
    $bytes = New-Object byte[] ($length)
    $rng.GetBytes($bytes)
    $result = New-Object System.Text.StringBuilder
    for ($i = 0; $i -lt $length; $i++) {
        [void]$result.Append($chars[$bytes[$i] % $chars.Length])
    }
    return $result.ToString()
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "Zone Monitoring Installer"
$form.Size = New-Object System.Drawing.Size(560, 420)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false

$font = New-Object System.Drawing.Font("Segoe UI", 10)

$labels = @(
    @{ Text = "Postgres DB"; Y = 20; Name = "POSTGRES_DB"; Value = "zone_monitoring" },
    @{ Text = "Postgres User"; Y = 60; Name = "POSTGRES_USER"; Value = "zone_user" },
    @{ Text = "Postgres Password"; Y = 100; Name = "POSTGRES_PASSWORD"; Value = "" },
    @{ Text = "App Port"; Y = 140; Name = "APP_PORT"; Value = "8080" },
    @{ Text = "Secret Key"; Y = 180; Name = "SECRET_KEY"; Value = (New-Secret 64) }
)

$inputs = @{}
foreach ($field in $labels) {
    $lbl = New-Object System.Windows.Forms.Label
    $lbl.Text = $field.Text
    $lbl.Location = New-Object System.Drawing.Point(20, $field.Y + 5)
    $lbl.Size = New-Object System.Drawing.Size(170, 24)
    $lbl.Font = $font
    $form.Controls.Add($lbl)

    $tb = New-Object System.Windows.Forms.TextBox
    $tb.Location = New-Object System.Drawing.Point(200, $field.Y)
    $tb.Size = New-Object System.Drawing.Size(330, 24)
    $tb.Font = $font
    $tb.Text = $field.Value
    if ($field.Name -eq "POSTGRES_PASSWORD") { $tb.UseSystemPasswordChar = $true }
    $form.Controls.Add($tb)
    $inputs[$field.Name] = $tb
}

$debugCheck = New-Object System.Windows.Forms.CheckBox
$debugCheck.Text = "Enable DEBUG mode"
$debugCheck.Location = New-Object System.Drawing.Point(200, 220)
$debugCheck.Size = New-Object System.Drawing.Size(200, 24)
$debugCheck.Font = $font
$form.Controls.Add($debugCheck)

$info = New-Object System.Windows.Forms.Label
$info.Text = "This will create .env and run: docker compose up -d --build"
$info.Location = New-Object System.Drawing.Point(20, 255)
$info.Size = New-Object System.Drawing.Size(510, 40)
$info.Font = $font
$form.Controls.Add($info)

$btnInstall = New-Object System.Windows.Forms.Button
$btnInstall.Text = "Install"
$btnInstall.Location = New-Object System.Drawing.Point(320, 310)
$btnInstall.Size = New-Object System.Drawing.Size(100, 34)
$btnInstall.Font = $font
$form.Controls.Add($btnInstall)

$btnCancel = New-Object System.Windows.Forms.Button
$btnCancel.Text = "Cancel"
$btnCancel.Location = New-Object System.Drawing.Point(430, 310)
$btnCancel.Size = New-Object System.Drawing.Size(100, 34)
$btnCancel.Font = $font
$form.Controls.Add($btnCancel)

$btnCancel.Add_Click({ $form.Close() })

$btnInstall.Add_Click({
    try {
        foreach ($k in @("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "APP_PORT", "SECRET_KEY")) {
            if ([string]::IsNullOrWhiteSpace($inputs[$k].Text)) {
                [System.Windows.Forms.MessageBox]::Show("Field $k is required.", "Validation", "OK", "Warning") | Out-Null
                return
            }
        }

        $envContent = @"
POSTGRES_DB=$($inputs["POSTGRES_DB"].Text.Trim())
POSTGRES_USER=$($inputs["POSTGRES_USER"].Text.Trim())
POSTGRES_PASSWORD=$($inputs["POSTGRES_PASSWORD"].Text.Trim())
APP_PORT=$($inputs["APP_PORT"].Text.Trim())
DEBUG=$($debugCheck.Checked.ToString().ToLower())
SECRET_KEY=$($inputs["SECRET_KEY"].Text.Trim())
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ALGORITHM=HS256
"@
        Set-Content -Path ".env" -Value $envContent -Encoding UTF8

        [System.Windows.Forms.MessageBox]::Show(".env created. Starting Docker deployment...", "Success", "OK", "Information") | Out-Null

        & docker compose up -d --build
        if ($LASTEXITCODE -ne 0) {
            throw "docker compose failed with exit code $LASTEXITCODE"
        }

        [System.Windows.Forms.MessageBox]::Show("Deployment finished. Open http://<SERVER_IP>:$($inputs["APP_PORT"].Text.Trim())", "Done", "OK", "Information") | Out-Null
        $form.Close()
    }
    catch {
        [System.Windows.Forms.MessageBox]::Show("Install failed: $($_.Exception.Message)", "Error", "OK", "Error") | Out-Null
    }
})

[void]$form.ShowDialog()
