# cashing2fast-fastapi
🚀 Simple and fast cashing tools for FastAPI with minimal configuration

## Documentación

- [Guía de Uso (Usage Guide)](docs/usage.md)
- [Ejemplos de configuración](examples/.env.examples)

## Instalación

```bash
uv add cashing2fast-fastapi
```

## Características

- 🎯 **Lógica de 3 Fases:** Tiempo gratuito, periodo de cobro por peticiones y bloqueo final.
- ⚡ **Redis Native:** Contadores atómicos y caché de usuario para evitar cargas innecesarias a DB.
- 🛡️ **Tools2Fast Integration:** Respuestas con formato estándar y código HTTP 402.
