param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$')]
    [string]$Bucket,

    [string]$MediaRoot = "data/media",

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$resolvedRoot = (Resolve-Path -LiteralPath $MediaRoot).Path
$files = Get-ChildItem -LiteralPath $resolvedRoot -Recurse -File

if (-not $files) {
    throw "No media found in $resolvedRoot. Run the media publisher first."
}

function Get-MediaType([string]$extension) {
    switch ($extension.ToLowerInvariant()) {
        ".avif" { "image/avif" }
        ".gif"  { "image/gif" }
        ".jpg"  { "image/jpeg" }
        ".jpeg" { "image/jpeg" }
        ".png"  { "image/png" }
        ".svg"  { "image/svg+xml" }
        ".webp" { "image/webp" }
        ".mp4"  { "video/mp4" }
        ".pdf"  { "application/pdf" }
        default { "application/octet-stream" }
    }
}

foreach ($file in $files) {
    $relative = $file.FullName.Substring($resolvedRoot.Length).TrimStart([char[]]@("\", "/")).Replace("\", "/")
    $objectPath = "$Bucket/$relative"
    $contentType = Get-MediaType $file.Extension
    Write-Host "Uploading $relative ($contentType)"
    if (-not $DryRun) {
        & npx.cmd wrangler r2 object put $objectPath `
            --file $file.FullName `
            --content-type $contentType `
            --cache-control "public, max-age=3600, stale-while-revalidate=86400" `
            --remote
        if ($LASTEXITCODE -ne 0) {
            throw "Upload failed: $relative"
        }
    }
}

Write-Host "Processed $($files.Count) media objects for R2 bucket '$Bucket'."
