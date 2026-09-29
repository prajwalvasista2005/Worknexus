import os
import io
import csv
import zipfile
from pathlib import Path
from typing import List, Optional

from ml.ingestion.schema import JobRecord

# Default data directory pointing to the datasets directory in repository root or fallback
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "datasets"

def get_data_dir(custom_path: Optional[str] = None) -> Path:
    if custom_path:
        return Path(custom_path)
    if DEFAULT_DATA_DIR.exists():
        return DEFAULT_DATA_DIR
    relative_fallback = Path(__file__).resolve().parent.parent.parent / "Data"
    if relative_fallback.exists():
        return relative_fallback
    return DEFAULT_DATA_DIR


def load_linkedin_india_sample(
    limit: int = 100,
    data_dir: Optional[str] = None
) -> List[JobRecord]:
    """
    Streams and loads a sample of Indian LinkedIn job postings from archive3.zip
    WITHOUT extracting the archive to disk.
    """
    resolved_dir = get_data_dir(data_dir)
    archive_path = resolved_dir / "archive3.zip"

    if not archive_path.exists():
        raise FileNotFoundError(f"Missing dataset archive: {archive_path}")

    records: List[JobRecord] = []

    with zipfile.ZipFile(archive_path, "r") as zf:
        if "linkdin_Job_data.csv" not in zf.namelist():
            raise FileNotFoundError("linkdin_Job_data.csv not found inside archive3.zip")

        with zf.open("linkdin_Job_data.csv") as f:
            # Handle possible UTF-8 BOM encoding safely
            text_stream = io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace")
            reader = csv.DictReader(text_stream)

            for idx, row in enumerate(reader):
                if limit is not None and idx >= limit:
                    break

                job_id = row.get("job_ID", str(idx + 1)).strip()
                title = row.get("job", "").strip()
                description = row.get("job_details", "").strip()
                company = row.get("company_name", "").strip()
                location = row.get("location", "").strip()
                work_type = row.get("work_type") or row.get("full_time_remote") or None
                if work_type:
                    work_type = work_type.strip()
                posted_at = row.get("posted_day_ago", "").strip() or None

                records.append(
                    JobRecord(
                        source="linkedin_india",
                        source_record_id=job_id,
                        title=title,
                        description=description,
                        company=company,
                        location=location,
                        posted_at=posted_at,
                        work_type=work_type,
                        explicit_skills=[],
                        raw_metadata={
                            "company_id": row.get("company_id", ""),
                            "no_of_employ": row.get("no_of_employ", ""),
                            "no_of_application": row.get("no_of_application", ""),
                            "alumni": row.get("alumni", ""),
                            "hiring_person": row.get("hiring_person", "")
                        }
                    )
                )

    return records


def load_naukri_sample(
    limit: int = 100,
    data_dir: Optional[str] = None
) -> List[JobRecord]:
    """
    Streams and loads a sample of Indian Naukri data science job postings from archive1.zip
    WITHOUT extracting the archive to disk.
    """
    resolved_dir = get_data_dir(data_dir)
    archive_path = resolved_dir / "archive1.zip"

    if not archive_path.exists():
        raise FileNotFoundError(f"Missing dataset archive: {archive_path}")

    records: List[JobRecord] = []

    with zipfile.ZipFile(archive_path, "r") as zf:
        if "naukri_data_science_jobs_india.csv" not in zf.namelist():
            raise FileNotFoundError("naukri_data_science_jobs_india.csv not found inside archive1.zip")

        with zf.open("naukri_data_science_jobs_india.csv") as f:
            text_stream = io.TextIOWrapper(f, encoding="utf-8-sig", errors="replace")
            reader = csv.DictReader(text_stream)

            for idx, row in enumerate(reader):
                if limit is not None and idx >= limit:
                    break

                title = row.get("Job_Role", "").strip()
                company = row.get("Company", "").strip()
                location = row.get("Location", "").strip()
                raw_skills_desc = row.get("Skills/Description", "").strip()
                experience = row.get("Job Experience", "").strip()

                # Parse explicit skills if comma-separated tokens exist
                explicit_skills = [
                    s.strip() for s in raw_skills_desc.split(",") if s.strip()
                ] if raw_skills_desc else []

                records.append(
                    JobRecord(
                        source="naukri",
                        source_record_id=f"naukri_{idx + 1}",
                        title=title,
                        description=raw_skills_desc,
                        company=company,
                        location=location,
                        posted_at=None,
                        work_type=None,
                        explicit_skills=explicit_skills,
                        raw_metadata={
                            "experience": experience
                        }
                    )
                )

    return records


def load_parquet_sample(
    limit: int = 100,
    data_dir: Optional[str] = None
) -> List[JobRecord]:
    """
    Streams a sample batch from train-00000-of-00001.parquet using PyArrow
    without loading the entire 140MB+ file into memory.
    """
    resolved_dir = get_data_dir(data_dir)
    parquet_path = resolved_dir / "train-00000-of-00001.parquet"

    if not parquet_path.exists():
        raise FileNotFoundError(f"Missing parquet dataset: {parquet_path}")

    records: List[JobRecord] = []
    parquet_file = pq.ParquetFile(str(parquet_path))

    # Check actual column names
    available_cols = set(parquet_file.schema.names)

    def get_val(batch_map, key_candidates, index):
        for k in key_candidates:
            if k in batch_map:
                v = batch_map[k][index]
                return str(v).strip() if v is not None else ""
        return ""

    for batch in parquet_file.iter_batches(batch_size=min(limit, 500)):
        batch_dict = batch.to_pydict()
        num_rows = len(next(iter(batch_dict.values())))

        for i in range(num_rows):
            if len(records) >= limit:
                break

            title = get_val(batch_dict, ["Position", "position", "title"], i)
            description = get_val(batch_dict, ["Long Description", "Long_Description", "description"], i)
            company = get_val(batch_dict, ["Company Name", "Company_Name", "company"], i)
            keyword = get_val(batch_dict, ["Primary Keyword", "Primary_Keyword", "keyword"], i)
            published = get_val(batch_dict, ["Published", "published", "date"], i) or None
            record_id = get_val(batch_dict, ["id", "ID"], i) or f"parquet_{len(records) + 1}"

            explicit_skills = [keyword] if keyword else []

            records.append(
                JobRecord(
                    source="parquet",
                    source_record_id=record_id,
                    title=title,
                    description=description,
                    company=company,
                    location="",  # Parquet source does not have location column
                    posted_at=published,
                    work_type=None,
                    explicit_skills=explicit_skills,
                    raw_metadata={
                        "exp_years": get_val(batch_dict, ["Exp Years", "Exp_Years"], i),
                        "english_level": get_val(batch_dict, ["English Level", "English_Level"], i),
                        "lang": get_val(batch_dict, ["Long Description_lang", "Description_lang"], i)
                    }
                )
            )

        if len(records) >= limit:
            break

    return records
