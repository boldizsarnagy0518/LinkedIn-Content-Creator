<#
.SYNOPSIS
Deploys the combined ContentOps backend (API at /api, MCP at /mcp) to Google Cloud Run.

.DESCRIPTION
Reads deploy/backend.env.local and deploy/frontend.env.local, runs the offline preflight check,
then deploys backend/ from source with gcloud. Secret values are passed through a temporary
env-vars file that is deleted afterwards; they are never printed.

Run from the repository root:
  ./deploy/deploy-backend-cloudrun.ps1 -Project my-gcp-project -DryRun
  ./deploy/deploy-backend-cloudrun.ps1 -Project my-gcp-project
#>
param(
    [Parameter(Mandatory = $true)][string]$Project,
    [string]$Region = "europe-west1",
    [string]$Service = "contentops-api",
    [string]$BackendEnv = "deploy/backend.env.local",
    [string]$FrontendEnv = "deploy/frontend.env.local",
    [switch]$SkipPreflight,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Read-EnvFile([string]$Path) {
    $values = [ordered]@{}
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
        $index = $trimmed.IndexOf("=")
        if ($index -lt 1) { throw "Invalid line in ${Path}: expected NAME=value." }
        $value = $trimmed.Substring($index + 1).Trim()
        # Match python-dotenv, which the preflight uses: surrounding quotes are not part of the value.
        if ($value.Length -ge 2 -and $value[0] -eq $value[-1] -and ($value[0] -eq '"' -or $value[0] -eq "'")) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $values[$trimmed.Substring(0, $index).Trim()] = $value
    }
    return $values
}

function Resolve-RepoPath([string]$Path) {
    if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }
    return Join-Path $root $Path
}

$backendPath = Resolve-RepoPath $BackendEnv
$frontendPath = Resolve-RepoPath $FrontendEnv
foreach ($path in @($backendPath, $frontendPath)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing $path. Copy the matching .example file and fill it in." }
}

if (-not $SkipPreflight) {
    & uv run --quiet --directory (Join-Path $root "backend") python -m app.preflight `
        --backend-env $backendPath --frontend-env $frontendPath
    if ($LASTEXITCODE -ne 0) { throw "Preflight failed. Fix the reported settings first." }
}

$values = Read-EnvFile $backendPath
# Cloud Run sets PORT itself; the image already defaults APP_ENV and MCP_HOST.
$values.Remove("PORT")

$temporary = Join-Path ([System.IO.Path]::GetTempPath()) ("contentops-env-" + [guid]::NewGuid() + ".yaml")
try {
    $yaml = foreach ($name in $values.Keys) {
        # Single-quoted YAML scalars keep every character literal; a quote is escaped by doubling it.
        "${name}: '" + ($values[$name] -replace "'", "''") + "'"
    }
    Set-Content -LiteralPath $temporary -Value $yaml -Encoding UTF8

    $arguments = @(
        "run", "deploy", $Service,
        "--project", $Project,
        "--region", $Region,
        "--source", (Join-Path $root "backend"),
        "--env-vars-file", $temporary,
        # The API and MCP enforce their own Supabase authentication, so the service itself is public.
        "--allow-unauthenticated",
        "--min-instances", "0",
        "--max-instances", "2",
        "--memory", "512Mi",
        "--cpu", "1",
        "--timeout", "300",
        "--quiet"
    )

    Write-Host "Environment variables passed (values hidden): $($values.Keys -join ', ')"
    if ($DryRun) {
        Write-Host "Dry run. Would execute: gcloud $($arguments -join ' ')"
        return
    }
    if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
        throw "gcloud CLI not found. Install the Google Cloud CLI and run 'gcloud auth login' first."
    }
    & gcloud @arguments
    if ($LASTEXITCODE -ne 0) { throw "gcloud run deploy failed." }

    $url = & gcloud run services describe $Service --project $Project --region $Region --format "value(status.url)"
    Write-Host ""
    Write-Host "Deployed: $url"
    Write-Host "Check readiness: $url/api/ready"
    Write-Host "MCP_PUBLIC_URL must be exactly: $url/mcp (or your custom domain)."
}
finally {
    Remove-Item -LiteralPath $temporary -ErrorAction SilentlyContinue
}
