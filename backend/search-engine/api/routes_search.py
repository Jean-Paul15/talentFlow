from fastapi import APIRouter

from api.search_routes.basic import router as basic_router
from api.search_routes.evaluation_batch import router as evaluation_batch_router
from api.search_routes.evaluation_single import router as evaluation_single_router
from api.search_routes.rerank_policy import router as rerank_policy_router
from api.search_routes.vector import router as vector_router

router = APIRouter(prefix='/search', tags=['search'])
router.include_router(basic_router)
router.include_router(vector_router)
router.include_router(evaluation_single_router)
router.include_router(evaluation_batch_router)
router.include_router(rerank_policy_router)
