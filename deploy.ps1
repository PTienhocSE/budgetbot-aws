$ErrorActionPreference = "Stop"
$WorkingDir = "d:\Workspace\Study\AWS\xbrain-learners\W7_budgetbot"

Write-Host "1. Packaging backend..."
Set-Location "$WorkingDir"
if (Test-Path "package.zip") { Remove-Item "package.zip" -Force }

# Install dependencies into a temporary package folder
Write-Host "Installing pip requirements..."
if (Test-Path "package") { Remove-Item "package" -Recurse -Force }
New-Item -ItemType Directory -Force -Path "package" | Out-Null
python -m pip install -q --disable-pip-version-check -r requirements.txt -t package --platform manylinux2014_aarch64 --only-binary=:all: --python-version 3.11 --implementation cp

# Copy src ONLY
Copy-Item -Path "src" -Destination "package\src" -Recurse

# Zip it up
Write-Host "Creating zip archive..."
Compress-Archive -Path "package\*" -DestinationPath "package.zip" -Force

Write-Host "2. Running Terraform..."
Set-Location "$WorkingDir\terraform"
terraform init
terraform apply -auto-approve

Write-Host "3. Retrieving output variables..."
$LambdaFunctionName = terraform output -raw lambda_function_name
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($LambdaFunctionName)) {
    $LambdaFunctionName = "budgetbot-hackathon-backend"
}
$FrontendBucketName = terraform output -raw frontend_bucket_name
$ApiEndpoint = terraform output -raw api_endpoint
Write-Host "Target Lambda: $LambdaFunctionName"
Write-Host "Target Frontend Bucket: $FrontendBucketName"
Write-Host "API Endpoint: $ApiEndpoint"

Write-Host "4. Deploying backend package to AWS Lambda..."
Set-Location "$WorkingDir"
aws lambda update-function-code --function-name $LambdaFunctionName --zip-file fileb://package.zip --publish

Write-Host "5. Building and uploading Frontend to S3..."
Push-Location "$WorkingDir\frontend-react"
if (-not (Test-Path "node_modules")) { npm install }
$env:VITE_API_BASE = $ApiEndpoint
npm run build
Remove-Item env:VITE_API_BASE
Pop-Location
aws s3 sync .\frontend-react\dist s3://$FrontendBucketName --delete

Write-Host "6. Cleaning up..."
Remove-Item "package" -Recurse -Force
Remove-Item "package.zip" -Force

Write-Host "Deployment completed!"
