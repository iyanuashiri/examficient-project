from sqlalchemy.orm import Session, joinedload

from app.models.user import User
from app.schemas.user import UserCreate


def get_user(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def get_users(session: Session) -> list[User]:
    return session.query(User).all()


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.query(User).filter(User.email == email).first()


def create_user(session: Session, user: UserCreate) -> User:
    db_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
    )
    db_user.set_password(user.password)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def update_user(session: Session, user: User, show_on_leaderboard: bool | None) -> User:
    if show_on_leaderboard is not None:
        user.show_on_leaderboard = show_on_leaderboard
        session.commit()
        session.refresh(user)
    return user