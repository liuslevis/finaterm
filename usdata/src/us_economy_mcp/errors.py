from dataclasses import dataclass


@dataclass
class ServiceError(Exception):
    code: str
    message: str
    source: str | None = None
    retryable: bool = False
    details: dict | None = None

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "source": self.source,
            "retryable": self.retryable,
            "details": self.details,
        }

