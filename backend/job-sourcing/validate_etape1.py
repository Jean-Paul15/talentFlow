# Script de validation end-to-end Etape 1
# Verifie : Docker services, Redis, MinIO, Spiders, Airflow

import time
import sys
from pathlib import Path

import requests
from loguru import logger

# Ajout chemin projet
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.redis_client import RedisFingerprint
from core.minio_client import MinioStorageClient


class ValidationEtape1:
    """
    Validateur pour l'Etape 1 du pipeline TalentFlow.
    """

    def __init__(self):
        """
        Initialise le validateur.
        """
        self.results = {
            "docker_services": False,
            "redis_connectivity": False,
            "minio_connectivity": False,
            "spider_execution": False,
            "no_duplicates": False,
            "airflow_connectivity": False
        }

    def validate_docker_services(self) -> bool:
        """
        Verifie que les services Docker sont up.
        """
        logger.info("Validation services Docker...")
        
        try:
            # Verification MinIO API
            response = requests.get("http://localhost:9000/minio/health/live", timeout=5)
            minio_ok = response.status_code == 200
            
            # Verification Redis
            redis_client = RedisFingerprint()
            redis_ok = redis_client.redis.ping()
            
            self.results["docker_services"] = minio_ok and redis_ok
            logger.success(f"Services Docker: {'OK' if self.results['docker_services'] else 'KO'}")
            return self.results["docker_services"]
            
        except Exception as err:
            logger.error(f"Erreur validation Docker: {err}")
            return False

    def validate_redis_connectivity(self) -> bool:
        """
        Teste Redis fingerprinting.
        """
        logger.info("Validation Redis fingerprinting...")
        
        try:
            redis_client = RedisFingerprint()
            test_hash = "test_validation_hash"
            
            # Ajout
            redis_client.add(test_hash, {"test": "validation"})
            
            # Verification existence
            exists = redis_client.exists(test_hash)
            
            # Nettoyage
            redis_client.remove(test_hash)
            
            self.results["redis_connectivity"] = exists
            logger.success(f"Redis: {'OK' if exists else 'KO'}")
            return exists
            
        except Exception as err:
            logger.error(f"Erreur Redis: {err}")
            return False

    def validate_minio_connectivity(self) -> bool:
        """
        Teste MinIO storage.
        """
        logger.info("Validation MinIO storage...")
        
        try:
            minio_client = MinioStorageClient()
            
            # Test upload
            test_data = {
                "title": "Test Job",
                "source_url": "http://test.com",
                "description": "Test validation"
            }
            
            success = minio_client.upload_job("test_site", test_data, "test_hash")
            
            self.results["minio_connectivity"] = success
            logger.success(f"MinIO: {'OK' if success else 'KO'}")
            return success
            
        except Exception as err:
            logger.error(f"Erreur MinIO: {err}")
            return False

    def validate_airflow_connectivity(self) -> bool:
        """
        Verifie acces Airflow webserver.
        """
        logger.info("Validation Airflow...")
        
        try:
            response = requests.get("http://localhost:8080/health", timeout=10)
            is_ok = response.status_code == 200
            
            self.results["airflow_connectivity"] = is_ok
            logger.success(f"Airflow: {'OK' if is_ok else 'KO'}")
            return is_ok
            
        except Exception as err:
            logger.warning(f"Airflow non accessible (demarrage en cours?): {err}")
            self.results["airflow_connectivity"] = False
            return False

    def generate_report(self) -> None:
        """
        Genere le rapport de validation.
        """
        logger.info("\n" + "="*60)
        logger.info("RAPPORT VALIDATION ETAPE 1 - SOURCING & INGESTION")
        logger.info("="*60)
        
        total = len(self.results)
        passed = sum(self.results.values())
        
        for test, result in self.results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            logger.info(f"{status} - {test}")
        
        logger.info("="*60)
        logger.info(f"SCORE: {passed}/{total} tests valides")
        
        if passed == total:
            logger.success("✓ VALIDATION COMPLETE - ETAPE 1 FONCTIONNELLE")
        else:
            logger.error("✗ VALIDATION PARTIELLE - Corriger les erreurs")
        
        logger.info("="*60)

    def run_full_validation(self) -> bool:
        """
        Execute toutes les validations.
        """
        logger.info("Demarrage validation complete Etape 1...")
        
        self.validate_docker_services()
        time.sleep(1)
        
        self.validate_redis_connectivity()
        time.sleep(1)
        
        self.validate_minio_connectivity()
        time.sleep(1)
        
        self.validate_airflow_connectivity()
        
        self.generate_report()
        
        return all(self.results.values())


if __name__ == "__main__":
    validator = ValidationEtape1()
    success = validator.run_full_validation()
    sys.exit(0 if success else 1)
