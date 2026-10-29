"""
ExcelR Track360 - API v1 Master Router
Mounts all domain routers under the /api/v1 prefix.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import system
from app.modules.auth.router import router as auth_router
from app.modules.candidates.router import router as candidates_router
from app.modules.assignments.router import router as assignments_router
from app.modules.projects.router import router as projects_router
from app.modules.internships.router import router as internships_router
from app.modules.certificates.router import router as certificates_router
from app.modules.notifications.router import router as notifications_router
from app.modules.audit.router import router as audit_router

api_v1_router = APIRouter()

# Core System Probes (mounted at root /api/v1 and with /system prefix for Learnova integration)
api_v1_router.include_router(system.router)
api_v1_router.include_router(system.router, prefix="/system")

# Domain Module Routers
api_v1_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_v1_router.include_router(candidates_router, prefix="", tags=["Candidates & Cohorts"])
api_v1_router.include_router(assignments_router, prefix="", tags=["Assignments & Allocations"])
api_v1_router.include_router(projects_router, prefix="", tags=["Projects & Milestones"])
api_v1_router.include_router(internships_router, prefix="", tags=["Internships"])
api_v1_router.include_router(certificates_router, prefix="", tags=["Certificates"])
api_v1_router.include_router(notifications_router, prefix="", tags=["Notifications"])
api_v1_router.include_router(audit_router, prefix="", tags=["Audit"])
