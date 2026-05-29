import shutil
import os
import subprocess

def main():
    print("1. Cleaning up old zip...")
    if os.path.exists("package.zip"):
        os.remove("package.zip")
    
    print("2. Packaging src directory...")
    # Create a temporary directory
    if os.path.exists("package"):
        shutil.rmtree("package")
    os.makedirs("package")
    
    print("3. Installing requirements...")
    # Use pip to install to package dir
    subprocess.run(
        "pip install -r requirements.txt -t package --platform manylinux2014_aarch64 --only-binary=:all: --python-version 3.11 --implementation cp", 
        shell=True, 
        check=True
    )
    
    print("4. Copying source code...")
    shutil.copytree("src", "package/src")
    
    print("5. Zipping with POSIX permissions...")
    import zipfile
    with zipfile.ZipFile("package.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk("package"):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, "package")
                zinfo = zipfile.ZipInfo.from_file(file_path, arcname)
                # Set permissions to 0o755 (rwxr-xr-x) for Linux compatibility
                zinfo.external_attr = 0o755 << 16
                with open(file_path, "rb") as f:
                    zf.writestr(zinfo, f.read())
    
    print("6. Deploying backend to AWS Lambda...")
    result = subprocess.run(
        "aws lambda update-function-code --function-name budgetbot-hackathon-backend --zip-file fileb://package.zip --publish",
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("Success! Backend deployed.")
    else:
        print("Error deploying backend:")
        print(result.stderr)

    print("6.5. Deploying file-processor to AWS Lambda...")
    result2 = subprocess.run(
        "aws lambda update-function-code --function-name budgetbot-hackathon-file-processor --zip-file fileb://package.zip --publish",
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result2.returncode == 0:
        print("Success! File processor deployed.")
    else:
        print("Error deploying file processor:")
        print(result2.stderr)

    print("7. Building frontend...")
    subprocess.run("cd frontend-react && npm install && npm run build", shell=True, check=True)

    print("8. Uploading frontend to S3...")
    # Bucket name is provided by Terraform output at deploy time.
    bucket_name = os.environ.get("FRONTEND_BUCKET_NAME")
    if bucket_name:
        subprocess.run(f"aws s3 sync frontend-react/dist s3://{bucket_name} --delete", shell=True, check=True)
    else:
        print("Skipping frontend sync: FRONTEND_BUCKET_NAME not set")

    print("9. Cleaning up package dir...")
    shutil.rmtree("package")

if __name__ == "__main__":
    main()
