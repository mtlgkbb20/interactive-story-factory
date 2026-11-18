from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    app_name: str = "Interactive Story Factory"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./interactive_story_factory.db"
    elevenlabs_api_key: str | None = None
    elevenlabs_default_voice_id: str | None = None
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    runware_api_key: str | None = None
    runware_base_url: str = "https://api.runware.ai/v1"
    runware_text_model: str = "auto"
    runware_video_model: str = "auto"
    runware_image_model: str = "auto"
    runware_video_width: int = 1080
    runware_video_height: int = 1920
    runware_video_duration: int = 5
    default_voting_hours: int = 24

settings = Settings()
