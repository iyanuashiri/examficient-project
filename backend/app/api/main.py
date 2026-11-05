from fastapi import APIRouter

from app.api.routes import (
    certifications,
    exams,
    practice,
    rooms,
    users,
    login,
)


api_router = APIRouter()

api_router.include_router(users.router)
api_router.include_router(login.router)
api_router.include_router(exams.router)
api_router.include_router(exams.syllabus_router)
api_router.include_router(exams.topic_router)
api_router.include_router(exams.question_router)
api_router.include_router(practice.router)
api_router.include_router(certifications.router)
api_router.include_router(rooms.router)
api_router.include_router(rooms.practice_extra)
