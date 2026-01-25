import os
import io
import json
import boto3
import hashlib
import logging
import mimetypes
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, Any, Optional


logger = logging.getLogger(__name__)


class S3Service:
    """Service for uploading files to S3 with project-based bucket isolation"""

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None
    ):
        """
        Initialize S3Service.

        Args:
            tenant_id: Optional tenant ID. If not provided, uses TENANT_ID env var.
            project_id: Optional project ID. If not provided, uses PROJECT_ID env var.
        """
        self.is_lambda = os.getenv("AWS_EXECUTION_ENV") is not None
        self.region = os.getenv("AWS_REGION", "eu-central-1")
        self.cdn_domain = os.getenv("CDN_DOMAIN")  # Optional CloudFront domain
        self.use_signed_urls = os.getenv("USE_SIGNED_URLS", "true").lower() == "true"

        # Store tenant/project IDs (use provided values or fall back to env vars)
        self._tenant_id = tenant_id or os.getenv('TENANT_ID', 'default')
        self._project_id = project_id or os.getenv('PROJECT_ID', 'default')

        # Check for local S3 endpoint (MinIO)
        self.local_endpoint = os.getenv("S3_LOCAL_ENDPOINT")

        # Build S3 client config
        s3_config = {"region_name": self.region}

        if self.local_endpoint:
            # MinIO / local S3-compatible storage
            s3_config["endpoint_url"] = self.local_endpoint
            s3_config["aws_access_key_id"] = os.getenv("S3_ACCESS_KEY", "minioadmin")
            s3_config["aws_secret_access_key"] = os.getenv("S3_SECRET_KEY", "minioadmin")
            logger.info(f"Using local S3 endpoint: {self.local_endpoint}")
        elif self.is_lambda:
            # In Lambda, use IAM role (no explicit credentials needed)
            pass
        else:
            # Local development with AWS
            s3_config["aws_access_key_id"] = os.getenv("AWS_ACCESS_KEY_ID")
            s3_config["aws_secret_access_key"] = os.getenv("AWS_SECRET_ACCESS_KEY")

        self.s3_client = boto3.client("s3", **s3_config)

    def get_bucket_name(self) -> str:
        """Get bucket name based on tenant and project ID"""
        tenant_id = self._tenant_id
        project_id = self._project_id

        # For long tenant/project IDs (UUIDs), create shortened versions using hash
        # This ensures bucket names stay within S3 limits (63 chars) and remain unique
        if len(tenant_id) > 8:
            tenant_short = hashlib.md5(tenant_id.encode()).hexdigest()[:8]
        else:
            tenant_short = tenant_id

        if len(project_id) > 8:
            project_short = hashlib.md5(project_id.encode()).hexdigest()[:8]
        else:
            project_short = project_id

        # Bucket naming pattern: polysynergy-{tenant_hash}-{project_hash}-media
        # This keeps bucket names under 63 characters while maintaining uniqueness
        bucket_name = f"polysynergy-{tenant_short}-{project_short}-media".lower()

        # Ensure bucket name is valid (lowercase, no underscores)
        bucket_name = bucket_name.replace('_', '-')

        # Final safety check - should never exceed 63 chars with our hash approach
        if len(bucket_name) > 63:
            # Emergency fallback: use shorter hashes
            tenant_short = hashlib.md5(tenant_id.encode()).hexdigest()[:6]
            project_short = hashlib.md5(project_id.encode()).hexdigest()[:6]
            bucket_name = f"poly-{tenant_short}-{project_short}-media".lower()

        return bucket_name

    def ensure_bucket_exists(self, bucket_name: str) -> bool:
        """Ensure the bucket exists, create if it doesn't"""
        logger.info(f"Checking if bucket exists: {bucket_name}, endpoint: {self.local_endpoint}")
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"Bucket {bucket_name} exists")
            # Bucket exists - set public policy if signed URLs are disabled OR using local endpoint
            # (MinIO uses direct URLs, not signed URLs, so needs public access)
            if not self.use_signed_urls or self.local_endpoint:
                self._set_bucket_public_read_policy(bucket_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.info(f"Bucket check error: {error_code} for {bucket_name}")
            if error_code == '404':
                # Bucket doesn't exist, try to create it
                logger.info(f"Bucket {bucket_name} does not exist, creating...")
                return self._create_bucket(bucket_name)
            else:
                logger.error(f"Error checking bucket {bucket_name}: {e}")
                return False

    def _create_bucket(self, bucket_name: str) -> bool:
        """Create a new bucket with proper configuration"""
        try:
            if self.local_endpoint:
                # MinIO doesn't need LocationConstraint
                self.s3_client.create_bucket(Bucket=bucket_name)
            elif self.region == 'us-east-1':
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )

            logger.info(f"Bucket created: {bucket_name}")

            # Set CORS for all buckets
            self._set_bucket_cors(bucket_name)

            # Set public access policy if signed URLs are disabled OR using local endpoint
            # (MinIO uses direct URLs, not signed URLs, so needs public access)
            if not self.use_signed_urls or self.local_endpoint:
                self._set_bucket_public_read_policy(bucket_name)

            return True
        except ClientError as create_error:
            logger.error(f"Failed to create bucket {bucket_name}: {create_error}")
            return False

    def _set_bucket_cors(self, bucket_name: str):
        """Set CORS configuration for the bucket"""
        cors_configuration = {
            'CORSRules': [{
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'HEAD', 'POST', 'PUT'],
                'AllowedOrigins': ['*'],
                'ExposeHeaders': ['ETag'],
                'MaxAgeSeconds': 3000
            }]
        }

        try:
            self.s3_client.put_bucket_cors(
                Bucket=bucket_name,
                CORSConfiguration=cors_configuration
            )
        except ClientError as e:
            logger.warning(f"Failed to set CORS for bucket {bucket_name}: {e}")

    def _set_bucket_public_read_policy(self, bucket_name: str):
        """Set bucket policy to allow public read access"""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }

        try:
            self.s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(policy)
            )
            logger.info(f"Successfully set public read policy for bucket {bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            # Don't fail the entire operation if public access is blocked
            if error_code == 'AccessDenied' and 'BlockPublicPolicy' in str(e):
                logger.info(f"Note: Public bucket policy blocked for {bucket_name} - using signed URLs instead")
            else:
                logger.warning(f"Failed to set public read policy for bucket {bucket_name}: {e}")
            # Continue execution - signed URLs will be used as fallback

    def upload_file(
        self,
        file_data: bytes,
        key: str,
        content_type: str = 'application/octet-stream',
        metadata: Optional[Dict[str, str]] = None,
        cache_control: str = 'public, max-age=31536000'  # 1 year cache
    ) -> Dict[str, Any]:
        """Upload file to S3 and return the URL"""

        bucket_name = self.get_bucket_name()
        logger.info(f"Uploading file to bucket: {bucket_name}, key: {key}")

        # Ensure bucket exists
        if not self.ensure_bucket_exists(bucket_name):
            logger.error(f"Failed to ensure bucket {bucket_name} exists")
            return {
                'success': False,
                'error': f'Failed to ensure bucket {bucket_name} exists'
            }

        try:
            # Prepare upload parameters
            upload_params = {
                'Bucket': bucket_name,
                'Key': key,
                'Body': file_data,
                'ContentType': content_type,
                'CacheControl': cache_control
            }

            # Add metadata if provided
            if metadata:
                upload_params['Metadata'] = metadata

            # Upload the file
            response = self.s3_client.put_object(**upload_params)

            # Generate URL based on configuration
            url = self._generate_url(bucket_name, key)

            return {
                'success': True,
                'url': url,
                'bucket': bucket_name,
                'key': key,
                'etag': response.get('ETag', '').strip('"'),
                'version_id': response.get('VersionId')
            }

        except ClientError as e:
            logger.error(f"Failed to upload {key}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_url(self, bucket_name: str, key: str) -> str:
        """Generate the appropriate URL for accessing a file"""
        if self.cdn_domain:
            # Use CloudFront CDN if available
            return f"https://{self.cdn_domain}/{key}"
        elif self.local_endpoint:
            # MinIO URL - use public endpoint if configured, otherwise replace docker hostname
            public_endpoint = os.getenv("S3_PUBLIC_ENDPOINT") or self.local_endpoint.replace("minio:", "localhost:")
            logger.info(f"Using public endpoint: {public_endpoint} (S3_PUBLIC_ENDPOINT env: {os.getenv('S3_PUBLIC_ENDPOINT')})")
            return f"{public_endpoint}/{bucket_name}/{key}"
        elif self.use_signed_urls:
            # Generate pre-signed URL for private bucket access
            url = self.get_signed_url(key, expiration=86400)  # 24 hours
            if url:
                return url
            # Fallback to direct URL
            return f"https://{bucket_name}.s3.{self.region}.amazonaws.com/{key}"
        else:
            # Use direct S3 URL (requires public bucket)
            return f"https://{bucket_name}.s3.{self.region}.amazonaws.com/{key}"

    def delete_file(self, key: str) -> bool:
        """Delete a file from S3"""
        bucket_name = self.get_bucket_name()

        try:
            self.s3_client.delete_object(Bucket=bucket_name, Key=key)
            return True
        except ClientError as e:
            logger.error(f"Failed to delete {key} from {bucket_name}: {e}")
            return False

    def get_signed_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """Generate a pre-signed URL for temporary access"""
        bucket_name = self.get_bucket_name()

        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate signed URL for {key}: {e}")
            return None

    def refresh_signed_url(self, key: str, expiration: int = 86400) -> Optional[str]:
        """Generate a fresh pre-signed URL for an existing file"""
        return self.get_signed_url(key, expiration)

    def get_file_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata for a file from S3"""
        bucket_name = self.get_bucket_name()

        try:
            response = self.s3_client.head_object(Bucket=bucket_name, Key=key)
            return {
                'success': True,
                'metadata': response.get('Metadata', {}),
                'size': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"'),
                'content_type': response.get('ContentType', 'unknown')
            }
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return {'success': False, 'error': 'File not found'}
            else:
                return {'success': False, 'error': str(e)}

    def get_file_url(self, key: str) -> str:
        """Get the URL for a file"""
        bucket_name = self.get_bucket_name()
        return self._generate_url(bucket_name, key)

    def list_files(self, prefix: str = "") -> list[str]:
        """List files in the bucket with optional prefix filter"""
        bucket_name = self.get_bucket_name()

        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
            return [item['Key'] for item in response.get('Contents', [])]
        except ClientError as e:
            logger.error(f"Error listing files: {e}")
            return []


    def upload_file_simple(self, file_data: bytes, key: str) -> Optional[str]:
        """
        Simple upload that returns just the URL (for backwards compatibility).

        Args:
            file_data: File content as bytes
            key: S3 key/path for the file

        Returns:
            URL string on success, None on failure
        """
        import traceback
        try:
            logger.info(f"upload_file_simple called for key: {key}, data size: {len(file_data)} bytes")
            content_type, _ = mimetypes.guess_type(key)
            logger.info(f"Detected content type: {content_type}")
            result = self.upload_file(
                file_data=file_data,
                key=key,
                content_type=content_type or 'application/octet-stream'
            )
            logger.info(f"upload_file result: {result}")
            if result.get('success'):
                return result.get('url')
            logger.error(f"Upload failed: {result.get('error')}")
            return None
        except Exception as e:
            logger.error(f"Exception in upload_file_simple: {e}")
            logger.error(traceback.format_exc())
            raise

    # Backwards compatibility alias for upload_image
    def upload_image(
        self,
        image_data: bytes,
        key: str,
        content_type: str = 'image/png',
        metadata: Optional[Dict[str, str]] = None,
        cache_control: str = 'public, max-age=31536000'
    ) -> Dict[str, Any]:
        """Alias for upload_file - backwards compatibility with S3ImageService"""
        return self.upload_file(
            file_data=image_data,
            key=key,
            content_type=content_type,
            metadata=metadata,
            cache_control=cache_control
        )


# Backwards compatibility aliases
S3ImageService = S3Service


def get_s3_service() -> S3Service:
    """Get an S3Service instance"""
    return S3Service()
