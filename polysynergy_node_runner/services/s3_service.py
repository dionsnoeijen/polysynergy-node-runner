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

        execution_env = os.getenv("AWS_EXECUTION_ENV", "")
        is_lambda = execution_env.lower().startswith("aws_lambda")
        is_explicit = bool(access_key and secret_key and not is_lambda)

        if is_explicit:
            self.s3_client = boto3.client(
                "s3",
                region_name=self.region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=os.getenv("AWS_SESSION_TOKEN")
            )
        else:
            self.s3_client = boto3.client("s3", region_name=self.region)

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
            self.s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": self.region}
            )
            logger.info(f"Bucket created: {bucket_name}")

            if self.public:
                # Enable ACLs for public buckets so we can set public-read ACL on objects
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

    def upload_file(self, file_obj: bytes, file_key: str) -> str | None:
        try:
            content_type, _ = mimetypes.guess_type(file_key)
            extra_args = {'ContentType': content_type or 'application/octet-stream'}

            # Add public-read ACL for public buckets to make objects publicly accessible
            if self.public:
                extra_args['ACL'] = 'public-read'

            self.s3_client.upload_fileobj(
                io.BytesIO(file_obj),
                self.bucket_name,
                file_key,
                ExtraArgs=extra_args
            )
            logger.info(f"Uploaded: {file_key}")
            if self.public:
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