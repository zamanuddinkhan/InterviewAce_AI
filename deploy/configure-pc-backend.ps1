param(
    [Parameter(Mandatory = $true)]
    [string]$FrontendOrigin,
    [Parameter(Mandatory = $true)]
    [string]$BackendOrigin,
    [string]$EnvPath = '.env'
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot

function Get-HttpsOrigin([string]$Value, [string]$Name) {
    try { $uri = [Uri]::new($Value.TrimEnd('/')) }
    catch { throw "$Name must be an HTTPS origin, for example https://project.vercel.app." }
    if (-not $uri.IsAbsoluteUri -or $uri.Scheme -ne 'https' -or $uri.UserInfo -or
        $uri.Query -or $uri.Fragment -or $uri.AbsolutePath -ne '/') {
        throw "$Name must contain only an HTTPS origin, without a path, query, fragment or credentials."
    }
    return $uri
}

$frontendUri = Get-HttpsOrigin $FrontendOrigin 'FrontendOrigin'
$backendUri = Get-HttpsOrigin $BackendOrigin 'BackendOrigin'
$path = if ([System.IO.Path]::IsPathRooted($EnvPath)) { $EnvPath } else { Join-Path $projectRoot $EnvPath }
if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    throw "Environment file not found: $path. Keep your existing private .env; do not replace it with .env.example."
}

$lines = [System.Collections.Generic.List[string]]::new()
$lines.AddRange([System.IO.File]::ReadAllLines($path))
$requiredHosts = @('127.0.0.1', 'localhost', 'testserver', $frontendUri.Host, $backendUri.Host)
$existingHosts = @()
foreach ($line in $lines) {
    if ($line -match '^\s*TRUSTED_HOSTS\s*=\s*(.*)$') {
        $existingHosts += $Matches[1].Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    }
}
$trustedHosts = @($existingHosts + $requiredHosts | Select-Object -Unique) -join ','
$values = [ordered]@{
    COOKIE_SECURE = 'true'
    PUBLIC_ORIGIN = $frontendUri.GetLeftPart([System.UriPartial]::Authority)
    TRUSTED_HOSTS = $trustedHosts
}

foreach ($key in $values.Keys) {
    $pattern = '^\s*' + [Regex]::Escape($key) + '\s*='
    $found = $false
    for ($index = 0; $index -lt $lines.Count; $index++) {
        if ($lines[$index] -match $pattern) {
            if (-not $found) { $lines[$index] = "$key=$($values[$key])"; $found = $true }
            else { $lines.RemoveAt($index); $index-- }
        }
    }
    if (-not $found) { $lines.Add("$key=$($values[$key])") }
}

[System.IO.File]::WriteAllLines($path, $lines, [System.Text.UTF8Encoding]::new($false))
Write-Output 'Updated COOKIE_SECURE, PUBLIC_ORIGIN and TRUSTED_HOSTS in the selected environment file.'
Write-Output 'Other settings, including DATABASE_URL, were preserved. Restart the local API to load the changes.'
