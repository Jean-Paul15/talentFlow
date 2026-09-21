"""
Lake API
Expose des endpoints FastAPI pour interroger la couche Bronze dans MinIO.
"""

import json
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from minio import Minio
from minio.error import S3Error
from pydantic import BaseModel


class BronzeObject(BaseModel):
    object_name: str
    last_modified: Optional[str] = None
    data: Dict[str, Any]


class LakeStats(BaseModel):
    bucket: str
    total_objects: int
    per_site: Dict[str, int]


class BronzeSource(BaseModel):
    source: str
    total_objects: int
    latest_object: Optional[str] = None
    latest_modified: Optional[str] = None
    sample_titles: List[str] = []


class LakeRepository:
    def __init__(self):
        endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "")
        secret_key = os.getenv("MINIO_SECRET_KEY", "")
        secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

        self.bucket = os.getenv("MINIO_BUCKET_RAW", "talentflow-bronze")
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def stats(self) -> LakeStats:
        total = 0
        per_site: Dict[str, int] = {}
        for obj in self.client.list_objects(self.bucket, recursive=True):
            total += 1
            site = obj.object_name.split("/", 1)[0]
            per_site[site] = per_site.get(site, 0) + 1

        return LakeStats(
            bucket=self.bucket,
            total_objects=total,
            per_site=dict(sorted(per_site.items(), key=lambda item: item[0])),
        )

    def list_objects(
        self,
        site: Optional[str] = None,
        date_prefix: Optional[str] = None,
        limit: Optional[int] = 50,
    ) -> List[BronzeObject]:
        prefix_parts = []
        if site:
            prefix_parts.append(site)
        if date_prefix:
            prefix_parts.append(date_prefix)

        prefix = "/".join(prefix_parts)
        if prefix:
            prefix = f"{prefix}/"

        results: List[BronzeObject] = []
        for obj in self.client.list_objects(
            self.bucket,
            prefix=prefix,
            recursive=True,
        ):
            data = self._read_object(obj.object_name)
            results.append(
                BronzeObject(
                    object_name=obj.object_name,
                    last_modified=obj.last_modified.isoformat()
                    if obj.last_modified
                    else None,
                    data=data,
                )
            )
            if limit is not None and len(results) >= limit:
                break

        return results

    def list_all_objects(
        self,
        site: Optional[str] = None,
        date_prefix: Optional[str] = None,
    ) -> List[BronzeObject]:
        """Retourne tout le contenu Bronze sans limitation."""
        return self.list_objects(site=site, date_prefix=date_prefix, limit=None)

    def get_object(self, object_name: str) -> BronzeObject:
        data = self._read_object(object_name)
        return BronzeObject(object_name=object_name, data=data)

    def search(
        self,
        text: str,
        site: Optional[str] = None,
        limit: int = 20,
    ) -> List[BronzeObject]:
        query = text.strip().lower()
        if not query:
            return []

        prefix = f"{site}/" if site else ""
        results: List[BronzeObject] = []

        for obj in self.client.list_objects(
            self.bucket,
            prefix=prefix,
            recursive=True,
        ):
            payload = self._read_object(obj.object_name)
            haystack = " ".join(
                [
                    str(payload.get("title", "")),
                    str(payload.get("company", "")),
                    str(payload.get("description", "")),
                    str(payload.get("location", "")),
                ]
            ).lower()

            if query in haystack:
                results.append(
                    BronzeObject(
                        object_name=obj.object_name,
                        last_modified=obj.last_modified.isoformat()
                        if obj.last_modified
                        else None,
                        data=payload,
                    )
                )
                if len(results) >= limit:
                    break

        return results

    def list_sources(self, sample_limit: int = 2) -> List[BronzeSource]:
        stats: Dict[str, Dict[str, Any]] = {}

        for obj in self.client.list_objects(self.bucket, recursive=True):
            source = obj.object_name.split("/", 1)[0]
            if source not in stats:
                stats[source] = {
                    "count": 0,
                    "latest_object": None,
                    "latest_modified": None,
                    "samples": [],
                }

            entry = stats[source]
            entry["count"] += 1

            if (
                entry["latest_modified"] is None
                or (obj.last_modified and obj.last_modified > entry["latest_modified"])
            ):
                entry["latest_modified"] = obj.last_modified
                entry["latest_object"] = obj.object_name

            if sample_limit > 0 and len(entry["samples"]) < sample_limit:
                entry["samples"].append(obj.object_name)

        results: List[BronzeSource] = []
        for source, entry in stats.items():
            sample_titles: List[str] = []
            for object_name in entry["samples"]:
                try:
                    payload = self._read_object(object_name)
                    title = str(payload.get("title", "")).strip()
                    if title:
                        sample_titles.append(title)
                except Exception:
                    continue

            latest_modified = entry["latest_modified"]
            results.append(
                BronzeSource(
                    source=source,
                    total_objects=entry["count"],
                    latest_object=entry["latest_object"],
                    latest_modified=latest_modified.isoformat()
                    if latest_modified
                    else None,
                    sample_titles=sample_titles,
                )
            )

        results.sort(key=lambda row: (-row.total_objects, row.source))
        return results

    def list_source_examples(self, site: str, limit: int = 20) -> List[BronzeObject]:
        return self.list_objects(site=site, limit=limit)

    def _read_object(self, object_name: str) -> Dict[str, Any]:
        response = None
        try:
            response = self.client.get_object(self.bucket, object_name)
            raw = response.read().decode("utf-8")
            return json.loads(raw)
        except S3Error as err:
            raise HTTPException(status_code=404, detail=str(err)) from err
        except json.JSONDecodeError as err:
            raise HTTPException(
                status_code=500,
                detail=f"JSON invalide pour {object_name}: {err}",
            ) from err
        finally:
            try:
                if response is not None:
                    response.close()
                    response.release_conn()
            except Exception:
                pass


app = FastAPI(
    title="TalentFlow Lake API",
    description="API FastAPI pour interroger la couche Bronze (MinIO)",
    version="1.0.0",
)

repo = LakeRepository()


@app.get("/health")
def health() -> Dict[str, Any]:
    try:
        stats = repo.stats()
        return {"status": "healthy", "bucket": stats.bucket}
    except Exception as err:
        return {"status": "unhealthy", "error": str(err)}


@app.get("/api/bronze/stats", response_model=LakeStats)
def bronze_stats() -> LakeStats:
    return repo.stats()


@app.get("/api/bronze/jobs", response_model=List[BronzeObject])
def bronze_jobs(
    site: Optional[str] = Query(default=None),
    date_prefix: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
    limit: int = Query(default=50, ge=1, le=500),
) -> List[BronzeObject]:
    return repo.list_objects(site=site, date_prefix=date_prefix, limit=limit)


@app.get("/api/bronze/jobs/all", response_model=List[BronzeObject])
def bronze_jobs_all(
    site: Optional[str] = Query(default=None),
    date_prefix: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
) -> List[BronzeObject]:
    """
    Retourne toutes les offres presentes dans Bronze.
    Utile pour export complet ou audit.
    """
    return repo.list_all_objects(site=site, date_prefix=date_prefix)


@app.get("/api/bronze/jobs/object/{object_name:path}", response_model=BronzeObject)
def bronze_job_by_object(object_name: str) -> BronzeObject:
    return repo.get_object(object_name)


@app.get("/api/bronze/search", response_model=List[BronzeObject])
def bronze_search(
    q: str = Query(..., min_length=2),
    site: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> List[BronzeObject]:
    return repo.search(text=q, site=site, limit=limit)


@app.get("/api/bronze/sources", response_model=List[BronzeSource])
def bronze_sources(
    sample_limit: int = Query(default=2, ge=0, le=5),
) -> List[BronzeSource]:
    return repo.list_sources(sample_limit=sample_limit)


@app.get("/api/bronze/sources/{site}/examples", response_model=List[BronzeObject])
def bronze_source_examples(
    site: str,
    limit: int = Query(default=20, ge=1, le=200),
) -> List[BronzeObject]:
    return repo.list_source_examples(site=site, limit=limit)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=False)
