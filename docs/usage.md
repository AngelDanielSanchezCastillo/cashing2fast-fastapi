# Guía de Uso: Cashing2Fast FastAPI

`cashing2fast-fastapi` es una extensión para gestionar límites de peticiones y control de facturación en aplicaciones FastAPI, utilizando Redis para alta velocidad y minimizando consultas a la base de datos.

## 1. Configuración de Entorno (.env)

Asegúrate de tener las siguientes variables en tu archivo `.env`. Puedes ver un ejemplo completo en [examples/.env.examples](../examples/.env.examples).

```env
# Límites de Facturación (en minutos)
CASHING_FREE_MINUTES=5       # Minutos gratis después de crear la cuenta
CASHING_REDIRECT_MINUTES=60  # Minutos en fase de cobro/conteo
CASHING_MAX_REQUESTS=10      # Máximo de peticiones en fase de cobro

# Redis para el contador y caché
CASHING_REDIS__HOST=localhost
CASHING_REDIS__PORT=6379
```

## 2. Registro del Manejador de Excepciones

Para que tu API responda con el formato estándar (402 Payment Required) y el esquema de `tools2fast`, debes registrar el manejador de excepciones en tu archivo `main.py`:

```python
from fastapi import FastAPI
from cashing2fast_fastapi.dependencies import register_billing_exception_handler

app = FastAPI()

# Esto permite que la excepción PaymentRequiredException 
# se convierta automáticamente en una respuesta Tools2Fast
register_billing_exception_handler(app)
```

## 3. Uso de la Dependencia en Routers

Para proteger un endpoint o un router completo, simplemente utiliza la dependencia `require_billing_checks`.

### Proteger un Endpoint Individual:

```python
from fastapi import APIRouter, Depends
from cashing2fast_fastapi import require_billing_checks

router = APIRouter()

@router.get("/data-limitada", dependencies=[Depends(require_billing_checks)])
async def get_protected_data():
    return {"message": "Has pasado el filtro de facturación correctamente"}
```

### Proteger un Router Completo:

```python
router = APIRouter(
    prefix="/api/premium",
    dependencies=[Depends(require_billing_checks)]
)
```

## 4. ¿Cómo funciona internamente?

La dependencia sigue una lógica de **3 fases** basada en la fecha de creación del usuario (`user.created_at`):

1.  **Fase Gratuita:** Si el tiempo desde la creación es menor o igual a `CASHING_FREE_MINUTES`, el usuario puede navegar libremente.
2.  **Fase de Conteo:** Si el tiempo es mayor a los minutos gratis pero menor al tiempo de redirección (`FREE + REDIRECT`):
    *   Se cuenta cada petición en Redis.
    *   Si se supera el `CASHING_MAX_REQUESTS`, se lanza un error **402**.
    *   **Importante:** Al lanzar el error, el contador se resetea a 0 para que el usuario pueda volver a navegar tras ser redireccionado por el frontend.
3.  **Fase Bloqueada:** Si el tiempo total expira, el acceso se bloquea permanentemente con un error **402** hasta que se realice un pago.

## 5. Optimización (Redis)

La librería minimiza el uso de la base de datos:
*   La primera vez que un usuario hace una petición, se busca su `id` y `created_at` en la DB y se guarda en Redis.
*   En todas las peticiones siguientes, la información se extrae directamente de Redis usando el token Bearer, ahorrando una consulta SQL por cada request.
