"""
Utilitaires pour le GPU/CPU fallback automatique.
"""
import logging
import torch

logger = logging.getLogger(__name__)


def get_device(prefer_gpu: bool = True, device_id: int = 0) -> torch.device:
    """
    Détecte et retourne le device optimal (GPU ou CPU avec fallback).
    
    Args:
        prefer_gpu: Préférer GPU si disponible
        device_id: ID du GPU à utiliser
        
    Returns:
        torch.device configuré
    """
    if prefer_gpu and torch.cuda.is_available():
        device = torch.device(f'cuda:{device_id}')
        gpu_name = torch.cuda.get_device_name(device_id)
        logger.info(f"GPU détecté et activé: {gpu_name}")
        return device
    else:
        device = torch.device('cpu')
        if prefer_gpu:
            logger.warning(
                "GPU préféré mais indisponible - Fallback CPU "
                "(latence embeddings +700ms)"
            )
        else:
            logger.info("Utilisation CPU pour embeddings")
        return device


def get_embedding_model(device: torch.device, model_name: str = None):
    """
    Charge le modèle d'embedding sur le device approprié.
    
    Args:
        device: Device torch (cuda ou cpu)
        model_name: Nom du modèle (défaut: multilingual-MiniLM)
        
    Returns:
        Modèle sentence-transformers configuré
    """
    try:
        from sentence_transformers import SentenceTransformer
        
        model_name = model_name or 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
        model = SentenceTransformer(model_name, device=str(device))
        
        logger.info(f"Modèle embedding chargé: {model_name} sur {device}")
        return model
    except Exception as e:
        logger.error(f"Erreur chargement modèle embedding: {e}")
        raise


def check_gpu_availability() -> dict:
    """
    Retourne les informations sur la disponibilité GPU.
    
    Returns:
        Dict avec cuda_available, device_count, device_names
    """
    info = {
        'cuda_available': torch.cuda.is_available(),
        'device_count': 0,
        'device_names': [],
        'cuda_version': None
    }
    
    if info['cuda_available']:
        info['device_count'] = torch.cuda.device_count()
        info['device_names'] = [
            torch.cuda.get_device_name(i) 
            for i in range(info['device_count'])
        ]
        info['cuda_version'] = torch.version.cuda
    
    return info
