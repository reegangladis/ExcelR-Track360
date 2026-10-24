"""
ExcelR Track360 - API v1 Master Router
Mounts all domain routers under the /api/v1 prefix.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import system

api_v1_router = APIRouter()

# Core System Probes
api_v1_router.include_router(system.router)

# Domain Module Routers will be registered in subsequent phases:
# api_v1_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
# api_v1_router.include_router(candidates.router, prefix="/candidates", tags=["Candidates"])
# api_v1_router.include_router(assignments.router, prefix="/assignments", tags=["Assignments"])
# api_v1_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
# api_v1_router.include_router(internships.router, prefix="/internships", tags=["Internships"])
# api_v1_router.include_router(certificates.router, prefix="/certificates", tags=["Certificates"])
# api_v1_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
# api_v1_router.include_router(audit.router, prefix="/audit-logs", tags=["Audit"])
