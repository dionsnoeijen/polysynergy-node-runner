import os
import io
import json
import boto3
import logging
import mimetypes
from botocore.exceptions import NoCredentialsError, ClientError

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(
        self,
        tenant_id: str,
        public: bool = False,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str | None = None
    ):
        self.tenant_id = tenant_id
        self.public = public
        self.region = region or os.getenv("AWS_REGION", "eu-central-1")

        # Check for local S3 endpoint (MinIO)
        local_endpoint = os.getenv("S3_LOCAL_ENDPOINT")
        self.local_endpoint = local_endpoint

        execution_env = os.getenv("AWS_EXECUTION_ENV", "")
        is_lambda = execution_env.lower().startswith("aws_lambda")
        is_explicit = bool(access_key and secret_key and not is_lambda)

        # Build S3 client config
        s3_config = {"region_name": self.region}

        # Use local endpoint if configured (MinIO)
        if local_endpoint:
            s3_config["endpoint_url"] = local_endpoint
            s3_config["aws_access_key_id"] = os.getenv("S3_ACCESS_KEY", "minioadmin")
            s3_config["aws_secret_access_key"] = os.getenv("S3_SECRET_KEY", "minioadmin")
            logger.info(f"Using local S3 endpoint: {local_endpoint}")
        elif is_explicit:
            s3_config["aws_access_key_id"] = access_key
            s3_config["aws_secret_access_key"] = secret_key
            s3_config["aws_session_token"] = os.getenv("AWS_SESSION_TOKEN")

        self.s3_client = boto3.client("s3", **s3_config)

        scope = "public" if public else "private"
        self.bucket_name = f"ps-{scope}-files-{tenant_id}".lower()

        if not self._bucket_exists(self.bucket_name):
            self._create_bucket(self.bucket_name)

    def _bucket_exists(self, bucket_name):
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError:
            return False

    def _create_bucket(self, bucket_name):
        logger.info(f"Creating bucket: {bucket_name}")
        try:
            # Check if using local endpoint (MinIO)
            local_endpoint = os.getenv("S3_LOCAL_ENDPOINT")

            if local_endpoint:
                # MinIO doesn't need LocationConstraint
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                # AWS S3 requires LocationConstraint for non-us-east-1 regions
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": self.region}
                )

            logger.info(f"Bucket created: {bucket_name}")

            if self.public:
                # Enable ACLs for public buckets so we can set public-read ACL on objects
                if not local_endpoint:
                    # AWS-specific ACL configuration
                    self._enable_bucket_acls(bucket_name)
                self._set_public_bucket_policy(bucket_name)

        except Exception as e:
            logger.error(f"Failed to create bucket {bucket_name}: {e}")
            raise

    def _enable_bucket_acls(self, bucket_name):
        """Enable ACLs for the bucket so we can set public-read ACL on objects"""
        try:
            # Set bucket ownership to allow ACLs
            self.s3_client.put_bucket_ownership_controls(
                Bucket=bucket_name,
                OwnershipControls={
                    'Rules': [
                        {
                            'ObjectOwnership': 'BucketOwnerPreferred'
                        }
                    ]
                }
            )
            logger.info(f"Bucket ownership configured for ACLs: {bucket_name}")
        except Exception as e:
            logger.error(f"Failed to configure bucket ownership for {bucket_name}: {e}")
            # Don't raise - try to continue with bucket policy approach

    def _set_public_bucket_policy(self, bucket_name):
        try:
            # First, disable Block Public Access for this bucket
            try:
                self.s3_client.put_public_access_block(
                    Bucket=bucket_name,
                    PublicAccessBlockConfiguration={
                        'BlockPublicAcls': False,
                        'IgnorePublicAcls': False,
                        'BlockPublicPolicy': False,
                        'RestrictPublicBuckets': False
                    }
                )
                logger.info(f"Disabled Block Public Access for: {bucket_name}")
            except Exception as block_error:
                logger.error(f"Failed to disable Block Public Access for {bucket_name}: {block_error}")

            # Set the bucket policy for public read access
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowPublicReadAccess",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{bucket_name}/*"
                    }
                ]
            }
            self.s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(policy)
            )
            logger.info(f"Public bucket policy set for: {bucket_name}")
        except Exception as e:
            logger.error(f"Failed to set public bucket policy: {e}")
            raise  # This is critical for public buckets

    def upload_file(self, file_obj: bytes, file_key: str) -> str | None:
        try:
            content_type, _ = mimetypes.guess_type(file_key)
            extra_args = {'ContentType': content_type or 'application/octet-stream'}

            # Debug logging
            logger.info(f"Uploading {file_key}: {len(file_obj)} bytes, content_type={content_type}")

            # Don't use ACLs - rely on bucket policy for public access
            # This avoids the "AccessControlListNotSupported" error

            file_buffer = io.BytesIO(file_obj)
            logger.info(f"Created BytesIO buffer, size: {file_buffer.getbuffer().nbytes}")

            self.s3_client.upload_fileobj(
                file_buffer,
                self.bucket_name,
                file_key,
                ExtraArgs=extra_args
            )
            logger.info(f"Uploaded: {file_key}")
            if self.public:
                # Use local endpoint URL for MinIO, AWS URL for production
                if self.local_endpoint:
                    # MinIO URL format: http://localhost:9000/bucket-name/file-key
                    # Replace internal docker hostname with localhost for browser access
                    public_endpoint = self.local_endpoint.replace("minio:", "localhost:")
                    return f"{public_endpoint}/{self.bucket_name}/{file_key}"
                else:
                    # AWS S3 URL format
                    return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_key}"
            else:
                return self.get_file_url(file_key)
        except NoCredentialsError:
            logger.error("No valid AWS credentials found.")
            return None
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return None

    def get_file_url(self, file_key: str) -> str | None:
        try:
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=3600
            )
        except Exception as e:
            logger.error(f"URL generation error: {e}")
            return None

    def list_files(self, prefix: str = "") -> list[str]:
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            return [item['Key'] for item in response.get('Contents', [])]
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

def get_s3_service(tenant_id: str, public: bool = False) -> S3Service:
    return S3Service(tenant_id, public=public)

def get_s3_service_from_env(tenant_id: str, access_key: str, secret_key: str, region: str, public: bool = False) -> S3Service:
    return S3Service(tenant_id, public=public, access_key=access_key, secret_key=secret_key, region=region)