"""Respuestas de error reutilizables para documentar los endpoints en OpenAPI."""

from app import schemas


def error(description: str) -> dict:
    return {"model": schemas.ErrorOut, "description": description}


BAD_REQUEST = error("Solicitud inválida (por ejemplo, un producto que no existe)")
UNAUTHORIZED = error("Token ausente, inválido o expirado")
FORBIDDEN = error("El usuario no tiene permisos para esta operación")
NOT_FOUND = error("El recurso solicitado no existe")
CONFLICT = error("Conflicto con el estado actual (email duplicado o stock insuficiente)")

# slowapi responde con su propio formato, por eso no se asocia a ErrorOut
RATE_LIMITED = {"description": "Demasiadas solicitudes: se superó el límite de la ruta"}