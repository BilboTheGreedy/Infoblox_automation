$basePath = "./infoblox_mock_web_ui"

$folders = @(
    "mock_server",
    "web_ui",
    "static/css",
    "static/js",
    "templates"
)

$files = @(
    "app.py",
    "mock_server/__init__.py",
    "mock_server/server.py",
    "mock_server/initialize_db.py",
    "mock_server/helpers.py",
    "web_ui/__init__.py",
    "web_ui/routes.py",
    "web_ui/api.py",
    "static/css/styles.css",
    "static/js/app.js",
    "templates/base.html",
    "templates/index.html",
    "templates/login.html",
    "templates/networks.html",
    "templates/hosts.html",
    "templates/records.html",
    "templates/fixed.html",
    "templates/config.html",
    "templates/tools.html"
)

# Create base directory if it doesn't exist
if (!(Test-Path -Path $basePath)) {
    New-Item -ItemType Directory -Path $basePath | Out-Null
}

# Create folders
foreach ($folder in $folders) {
    $folderPath = "$basePath/$folder"
    if (!(Test-Path -Path $folderPath)) {
        New-Item -ItemType Directory -Path $folderPath | Out-Null
    }
}

# Create files
foreach ($file in $files) {
    $filePath = "$basePath/$file"
    if (!(Test-Path -Path $filePath)) {
        New-Item -ItemType File -Path $filePath | Out-Null
    }
}

Write-Host "Directory structure created successfully at $basePath"
