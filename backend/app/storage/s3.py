"""Amazon S3 storage. Credentials come from the Lambda execution role (IAM);
nothing is configured in code. Downloads use presigned GET URLs."""
from urllib.parse import quote

from app.storage.base import Disposition


class S3Storage:
    def __init__(self, bucket: str, region: str | None, url_expires_seconds: int):
        import boto3  # provided by the Lambda runtime
        from botocore.config import Config

        self.bucket = bucket
        self.url_expires_seconds = url_expires_seconds
        # Presign against the regional endpoint with SigV4: URLs for the global endpoint
        # get a 307 redirect for new buckets, after which the signature no longer matches.
        self._client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=f"https://s3.{region}.amazonaws.com" if region else None,
            config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
        )

    def save(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, ServerSideEncryption="AES256"
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)

    def download_url(self, key: str, file_name: str, content_type: str, disposition: Disposition) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ResponseContentType": content_type,
                "ResponseContentDisposition": f"{disposition}; filename*=UTF-8''{quote(file_name)}",
            },
            ExpiresIn=self.url_expires_seconds,
        )
