# Execution des spiders Scrapy avec gestion du reactor Twisted
# Supporte les appels multiples via subprocess
# Mode PARALLELE : ThreadPoolExecutor pour lancer N sites simultanement
# Mode dedie : uniquement spiders avec dossier logique propre
# API spider : collecte depuis APIs gratuites (JSearch, Adzuna)

import os
import sys
import json
import re
import ast
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger

from scrapy_project.spiders.anpe_togo import AnpeTogoSpider
from scrapy_project.spiders.emploi_tg import EmploiTgSpider
from scrapy_project.spiders.emploitogo_com import EmploiTogoComSpider
from scrapy_project.spiders.miabejob import MiabeJobSpider
from scrapy_project.spiders.emploitogo_info import EmploiTogoInfoSpider
from scrapy_project.spiders.wiijob import WiijobSpider
from scrapy_project.spiders.lucreatif import LucreatifSpider
from scrapy_project.spiders.indeed import IndeedSpider
from scrapy_project.spiders.glassdoor import GlassdoorSpider
from scrapy_project.spiders.monster import MonsterSpider
from core.sites_registry import get_spider_sites
from core.sourcing_reports import append_scrape_report


# Nombre de workers paralleles (configurable via .env)
MAX_WORKERS = int(os.getenv("SCRAPING_PARALLEL_WORKERS", "5"))
DEFAULT_SPIDER_TIMEOUT = int(os.getenv("SCRAPING_SPIDER_TIMEOUT", "600"))


def _env_flag(name: str, default: bool = False) -> bool:
    return str(os.getenv(name, "true" if default else "false")).strip().lower() in {
        "1", "true", "yes", "on",
    }

# Timeouts adaptes par type de spider
SPIDER_TIMEOUTS = {
    "anpe_togo": DEFAULT_SPIDER_TIMEOUT,
    "emploi_tg": DEFAULT_SPIDER_TIMEOUT,
    "emploitogo_com": DEFAULT_SPIDER_TIMEOUT,
    "miabejob": DEFAULT_SPIDER_TIMEOUT,
    "emploitogo_info": max(DEFAULT_SPIDER_TIMEOUT, 1200),
    "wiijob": DEFAULT_SPIDER_TIMEOUT,
    "lucreatif": max(DEFAULT_SPIDER_TIMEOUT, 900),
    "indeed": max(DEFAULT_SPIDER_TIMEOUT, 900),
    "glassdoor": max(DEFAULT_SPIDER_TIMEOUT, 900),
    "monster": max(DEFAULT_SPIDER_TIMEOUT, 900),
    "api_aggregator": 120,     # APIs sont rapides
}

# Mode JS/Playwright augmente naturellement la duree d'execution de certains spiders.
if _env_flag("WIIJOB_USE_PLAYWRIGHT", False) or _env_flag("SCRAPY_ENABLE_PLAYWRIGHT", False):
    SPIDER_TIMEOUTS["wiijob"] = max(SPIDER_TIMEOUTS.get("wiijob", DEFAULT_SPIDER_TIMEOUT), DEFAULT_SPIDER_TIMEOUT + 300)
if _env_flag("MONSTER_USE_PLAYWRIGHT", False) or (
    _env_flag("MONSTER_DETAIL_USE_PLAYWRIGHT", False)
    and _env_flag("SCRAPY_ENABLE_PLAYWRIGHT", False)
):
    SPIDER_TIMEOUTS["monster"] = max(
        SPIDER_TIMEOUTS.get("monster", DEFAULT_SPIDER_TIMEOUT),
        DEFAULT_SPIDER_TIMEOUT + 300,
    )

SPIDER_CLASSES = {
    "anpe_togo": AnpeTogoSpider,
    "emploi_tg": EmploiTgSpider,
    "emploitogo_com": EmploiTogoComSpider,
    "miabejob": MiabeJobSpider,
    "emploitogo_info": EmploiTogoInfoSpider,
    "wiijob": WiijobSpider,
    "lucreatif": LucreatifSpider,
    "indeed": IndeedSpider,
    "glassdoor": GlassdoorSpider,
    "monster": MonsterSpider,
}


def _get_active_spiders() -> Dict[str, type]:
    """
    Retourne uniquement les spiders actifs dans le registre.
    Permet de desactiver proprement un site sans modifier le runner.
    """
    active_spider_names = {
        info["spider"]
        for info in get_spider_sites().values()
        if info.get("spider")
    }
    return {
        name: spider_cls
        for name, spider_cls in SPIDER_CLASSES.items()
        if name in active_spider_names
    }


SPIDERS = _get_active_spiders()


def run_spider(spider_name: str, extra_args: List[str] = None) -> Dict[str, Any]:
    """
    Execute un spider dans un sous-processus.
    Contourne la limitation du reactor Twisted (un seul start par process).

    Args:
        spider_name: Nom du spider a executer
        extra_args: Arguments supplementaires (-a sites=..., etc.)

    Returns:
        {"items": n, "errors": m}
    """
    if spider_name == "api_aggregator":
        return _run_api_aggregator()

    if spider_name not in SPIDERS:
        logger.error(f"Spider inconnu: {spider_name}")
        return {"items": 0, "errors": 1}

    timeout = SPIDER_TIMEOUTS.get(spider_name, 300)
    run_stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    started_ts = time.time()
    run_id = f"{spider_name}_{run_stamp}"
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    run_log_file = log_dir / f"{spider_name}_{run_stamp}.log"

    cmd = [
        sys.executable, "-m", "scrapy", "crawl", spider_name,
        "-s", f"LOG_FILE={run_log_file}",
        "-s", "LOG_FILE_APPEND=False",
    ]
    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(Path(__file__).parent),
        )

        output = result.stderr + result.stdout
        if run_log_file.exists():
            output += "\n" + run_log_file.read_text(
                encoding="utf-8", errors="ignore",
            )
            run_log_file.unlink(missing_ok=True)

        items = _parse_scrapy_stats(output)
        errors = _parse_scrapy_errors(output)
        qa = _parse_data_quality_metrics(output, spider_name)
        fingerprint_stats = _parse_fingerprint_stats(output)
        duration_seconds = round(time.time() - started_ts, 3)
        status = "success"
        if result.returncode != 0 and errors > 0:
            status = "partial"
        elif result.returncode != 0:
            status = "error"
        elif errors > 0:
            status = "partial"

        report = {
            "run_id": run_id,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "spider": spider_name,
            "source_type": "scrapy",
            "status": status,
            "items": items,
            "errors": errors,
            "duration_seconds": duration_seconds,
            "timeout_seconds": timeout,
            "exit_code": result.returncode,
            "qa": qa or {},
            "fingerprint": fingerprint_stats or {},
            "extra_args": list(extra_args or []),
        }
        _safe_append_scrape_report(report)
        logger.info(f"Spider {spider_name}: {items} items, {errors} erreurs")
        return {
            "items": items,
            "errors": errors,
            "status": status,
            "duration_seconds": duration_seconds,
            "exit_code": result.returncode,
            "qa": qa or {},
            "fingerprint": fingerprint_stats or {},
            "run_id": run_id,
        }

    except subprocess.TimeoutExpired:
        logger.error(f"Spider {spider_name}: timeout {timeout}s")
        duration_seconds = round(time.time() - started_ts, 3)
        _safe_append_scrape_report({
            "run_id": run_id,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "spider": spider_name,
            "source_type": "scrapy",
            "status": "timeout",
            "items": 0,
            "errors": 1,
            "duration_seconds": duration_seconds,
            "timeout_seconds": timeout,
            "exit_code": None,
            "qa": {},
            "fingerprint": {},
            "extra_args": list(extra_args or []),
        })
        return {
            "items": 0,
            "errors": 1,
            "status": "timeout",
            "duration_seconds": duration_seconds,
            "run_id": run_id,
        }
    except Exception as err:
        logger.error(f"Spider {spider_name}: {err}")
        duration_seconds = round(time.time() - started_ts, 3)
        _safe_append_scrape_report({
            "run_id": run_id,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "spider": spider_name,
            "source_type": "scrapy",
            "status": "error",
            "items": 0,
            "errors": 1,
            "duration_seconds": duration_seconds,
            "timeout_seconds": timeout,
            "exit_code": None,
            "qa": {},
            "fingerprint": {},
            "extra_args": list(extra_args or []),
            "exception": str(err),
        })
        return {
            "items": 0,
            "errors": 1,
            "status": "error",
            "duration_seconds": duration_seconds,
            "run_id": run_id,
        }


def _run_api_aggregator() -> Dict[str, Any]:
    """Execute la collecte via APIs gratuites (JSearch, Adzuna)."""
    started_ts = time.time()
    run_id = f"api_aggregator_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
    try:
        from api_sourcing.collector import run_api_collection
        items = run_api_collection()
        duration_seconds = round(time.time() - started_ts, 3)
        _safe_append_scrape_report({
            "run_id": run_id,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "spider": "api_aggregator",
            "source_type": "api",
            "status": "success",
            "items": items,
            "errors": 0,
            "duration_seconds": duration_seconds,
            "timeout_seconds": SPIDER_TIMEOUTS.get("api_aggregator", 120),
            "qa": {},
            "fingerprint": {},
        })
        logger.info(f"API Aggregator: {items} items collectes")
        return {
            "items": items,
            "errors": 0,
            "status": "success",
            "duration_seconds": duration_seconds,
            "run_id": run_id,
        }
    except ImportError:
        logger.warning("Module api_sourcing non disponible")
        duration_seconds = round(time.time() - started_ts, 3)
        _safe_append_scrape_report({
            "run_id": run_id,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "spider": "api_aggregator",
            "source_type": "api",
            "status": "skipped",
            "items": 0,
            "errors": 0,
            "duration_seconds": duration_seconds,
            "timeout_seconds": SPIDER_TIMEOUTS.get("api_aggregator", 120),
            "qa": {},
            "fingerprint": {},
            "note": "module_unavailable",
        })
        return {
            "items": 0,
            "errors": 0,
            "status": "skipped",
            "duration_seconds": duration_seconds,
            "run_id": run_id,
        }
    except Exception as err:
        logger.error(f"API Aggregator: {err}")
        duration_seconds = round(time.time() - started_ts, 3)
        _safe_append_scrape_report({
            "run_id": run_id,
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "spider": "api_aggregator",
            "source_type": "api",
            "status": "error",
            "items": 0,
            "errors": 1,
            "duration_seconds": duration_seconds,
            "timeout_seconds": SPIDER_TIMEOUTS.get("api_aggregator", 120),
            "qa": {},
            "fingerprint": {},
            "exception": str(err),
        })
        return {
            "items": 0,
            "errors": 1,
            "status": "error",
            "duration_seconds": duration_seconds,
            "run_id": run_id,
        }


def run_all() -> Dict[str, Dict[str, int]]:
    """
    Execute TOUS les spiders en PARALLELE :
    - Spiders dedies : lances en parallele entre eux
    - API aggregator : lance en parallele avec le reste

    Returns:
        {"spider_name": {"items": n, "errors": m}, ...}
    """
    results = {}
    spider_names = list(SPIDERS.keys())

    logger.info(
        f"Lancement PARALLELE: {len(spider_names)} spiders "
        f"(dossier dedie) + API"
    )

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}

        # 1. Soumettre tous les spiders dedies en parallele
        for name in spider_names:
            futures[executor.submit(run_spider, name)] = name

        # 2. Soumettre l'API aggregator en parallele
        futures[executor.submit(_run_api_aggregator)] = "api_aggregator"

        # Collecter les resultats au fur et a mesure
        for future in as_completed(futures):
            task_name = futures[future]
            try:
                result = future.result()
                results[task_name] = result
                logger.info(
                    f"{task_name} termine: "
                    f"{result.get('items', 0)} items"
                )
            except Exception as err:
                logger.error(f"Erreur {task_name}: {err}")
                results[task_name] = {"items": 0, "errors": 1}

    total_items = sum(r.get("items", 0) for r in results.values())
    logger.info(
        f"Scraping PARALLELE termine: {total_items} items total "
        f"depuis {len(results)} sources"
    )
    return results


def _parse_scrapy_stats(output: str) -> int:
    """Extrait le nombre d'items depuis la sortie Scrapy."""
    for line in output.split("\n"):
        if "item_scraped_count" in line:
            parts = line.strip().rstrip(",").split(":")
            if len(parts) >= 2:
                try:
                    return int(parts[-1].strip().rstrip(","))
                except ValueError:
                    pass
    return 0


def _parse_scrapy_errors(output: str) -> int:
    """Extrait le nombre d'erreurs depuis la sortie Scrapy."""
    for line in output.split("\n"):
        if "log_count/ERROR" in line:
            parts = line.strip().rstrip(",").split(":")
            if len(parts) >= 2:
                try:
                    return int(parts[-1].strip().rstrip(","))
                except ValueError:
                    pass
    return 0


def _parse_data_quality_metrics(output: str, spider_name: str) -> Dict[str, Any]:
    """
    Parse the custom pipeline summary line:
    DataQuality[spider]: total=... date_iso=... apply_method=...
    """
    matches = []
    for line in output.split("\n"):
        if f"DataQuality[{spider_name}]" in line:
            matches.append(line)
    if not matches:
        return {}

    line = matches[-1]
    metrics: Dict[str, Any] = {}
    for key, raw in re.findall(r"([a-zA-Z_]+)=([0-9]+(?:\.[0-9]+)?)", line):
        if "." in raw:
            try:
                metrics[key] = float(raw)
            except ValueError:
                metrics[key] = raw
        else:
            try:
                metrics[key] = int(raw)
            except ValueError:
                metrics[key] = raw
    return metrics


def _parse_fingerprint_stats(output: str) -> Dict[str, Any]:
    """Parse 'Fingerprint: { ... }' log line if present."""
    matches = []
    for line in output.split("\n"):
        if "Fingerprint:" in line:
            matches.append(line)
    if not matches:
        return {}

    line = matches[-1]
    _, _, payload = line.partition("Fingerprint:")
    payload = payload.strip()
    try:
        parsed = ast.literal_eval(payload)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return {}
    return {}


def _safe_append_scrape_report(report: Dict[str, Any]) -> None:
    try:
        append_scrape_report(report)
    except Exception as err:
        logger.warning(f"Impossible d'enregistrer le rapport de scraping: {err}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python run_spider.py <spider_name|all>")
        print(f"Spiders: {', '.join(SPIDERS.keys())}, api_aggregator")
        print(f"Workers paralleles: {MAX_WORKERS} (SCRAPING_PARALLEL_WORKERS)")
        sys.exit(1)

    spider = sys.argv[1]
    if spider == "all":
        results = run_all()
        print(json.dumps(results, indent=2, default=str))
    else:
        result = run_spider(spider)
        print(json.dumps(result, indent=2, default=str))
