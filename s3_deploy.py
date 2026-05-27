import shutil
import os
import subprocess
import zipfile

def main():
    print("1. Cleaning up old zip...")
    if os.path.exists("package.zip"):
        os.remove("package.zip")
    
    print("2. Packaging src directory...")
    if os.path.exists("package"):
        shutil.rmtree("package")
    os.makedirs("package")
    
    print("3. Installing requirements...")
    subprocess.run(
        "pip install -r requirements.txt -t package --platform manylinux2014_aarch64 --only-binary=:all: --python-version 3.11 --implementation cp", 
        shell=True, 
        check=True
    )
    
    print("4. Copying source code...")
    shutil.copytree("src", "package/src")
    
    print("5. Zipping with POSIX permissions...")
    with zipfile.ZipFile("package.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk("package"):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, "package")
                zinfo = zipfile.ZipInfo.from_file(file_path, arcname)
                zinfo.external_attr = 0o755 << 16
                with open(file_path, "rb") as f:
                    zf.writestr(zinfo, f.read())
                    
    print("5.5. Running Terraform apply...")
    subprocess.run("terraform apply -auto-approve", cwd="terraform", shell=True, check=True)
    
    bucket_name = "budgetbot-hackathon-uploads-873fca3d"
    print(f"6. Uploading package.zip to S3 bucket: {bucket_name}...")
    result_s3 = subprocess.run(
        f"aws s3 cp package.zip s3://{bucket_name}/package.zip",
        shell=True,
        capture_output=True,
        text=True
    )
    if result_s3.returncode != 0:
        print("Error uploading to S3:")
        print(result_s3.stderr)
        return
        
    print("7. Updating Lambda function code from S3...")
    result_lambda = subprocess.run(
        f"aws lambda update-function-code --function-name budgetbot-hackathon-backend --s3-bucket {bucket_name} --s3-key package.zip --publish",
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result_lambda.returncode == 0:
        print("Success! Backend deployed from S3.")
    else:
        print("Error updating Lambda function:")
        print(result_lambda.stderr)

    print("8. Cleaning up package dir...")
    shutil.rmtree("package")
    if os.path.exists("package.zip"):
        os.remove("package.zip")

if __name__ == "__main__":
    main()
