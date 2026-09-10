"""
资料服务配置

轻量示例服务：无数据库，资料保存在内存中。
与 user-service 共享 JWT 密钥，用于本地校验调用方令牌；
用户基本信息通过 HTTP 调用 user-service 获取。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 服务配置
    SERVICE_NAME: str = "profile-service"
    SERVICE_HOST: str = "0.0.0.0"
    SERVICE_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # JWT（与 user-service 使用相同密钥/算法，才能校验其签发的令牌）
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"

    # user-service 服务间调用地址（compose 网络内的服务名）
    USER_SERVICE_URL: str = "http://user-service:8000"
    USER_SERVICE_TIMEOUT_SECONDS: float = 2.0

    # 资料快照持久化文件路径（JSON 快照，重启后恢复；空字符串表示纯内存模式）
    PROFILE_STORE_PATH: str = "./data/profiles.json"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
