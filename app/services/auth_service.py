from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, Token, UserResponse
from app.utils.security import hash_password, verify_password, create_access_token


class AuthService:
    """Сервис для работы с аутентификацией пользователей."""

    @staticmethod
    def register_user(db: Session, user_data: UserRegister) -> UserResponse:
        """
        Регистрация нового пользователя.
        
        Args:
            db: Сессия базы данных
            user_data: Данные для регистрации
            
        Returns:
            UserResponse: Данные зарегистрированного пользователя
            
        Raises:
            HTTPException: Если email уже занят
        """
        # Проверка существования пользователя
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Хеширование пароля
        hashed_password = hash_password(user_data.password)
        
        # Создание пользователя
        new_user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name
        )
        
        try:
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        return UserResponse.model_validate(new_user)

    @staticmethod
    def authenticate_user(db: Session, credentials: UserLogin) -> Token:
        """
        Аутентификация пользователя и выдача JWT токена.
        
        Args:
            db: Сессия базы данных
            credentials: Email и пароль
            
        Returns:
            Token: JWT токен доступа
            
        Raises:
            HTTPException: Если credentials неверные
        """
        # Поиск пользователя
        user = db.query(User).filter(User.email == credentials.email).first()
        
        # Проверка пароля
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Создание токена
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return Token(access_token=access_token, token_type="bearer")

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        """
        Получение пользователя по ID.
        
        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            
        Returns:
            User: Объект пользователя
            
        Raises:
            HTTPException: Если пользователь не найден
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user