Actúa como experto en arquitectura de microservicios y redes Linux.

Objetivo:
Implementar completamente el módulo `driver` dentro de `/driver/`, respetando estrictamente la estructura existente del proyecto.

IMPORTANTE:
- No inventes lógica de red.
- No cambies contratos existentes.
- Basa toda la implementación únicamente en los documentos de referencia.
- Mantén compatibilidad con FastAPI async.
- Usa tipado completo y código production-ready.

Documentos de referencia obligatorios:
1. docs/modules/dispatcher_driver_contract.md
   - Contratos API
   - Payloads JSON
   - Respuestas esperadas

2. .agents/rules/rule-driver.md
   - Comandos QEMU obligatorios
   - Comandos Open vSwitch obligatorios
   - Uso obligatorio de archivos `.pid`

3. docs/context/05_Logica_Consistencia_L2.md
   - Modelo Br-Slice
   - VLAN Inner
   - Patch Ports remotos
   - Reglas de consistencia L2

4. README.md
   - Puertos
   - venv
   - Convenciones generales

5. db/init_schema.sql
   - Fuente de verdad para las tablas:
     - virtual_machines
     - tasks
     - vm_interfaces
   - Usar exactamente los nombres de columnas definidos allí

Archivos a editar:

- requirements.txt
- Dockerfile
- .env

- app/main.py
- app/models.py
- app/dependencies.py
- app/base_driver.py
- app/factory.py

- app/linux/linux_driver.py
- app/linux/qemu_commands.py
- app/linux/ovs_commands.py
- app/linux/__init__.py

Requisitos funcionales:

1. app/main.py
- Implementar:
  - POST /execute
  - POST /delete
- Ambos endpoints deben usar la Factory.

2. app/models.py
- Crear modelos Pydantic basados en el contrato del Dispatcher.

3. app/dependencies.py
- Configuración de Settings usando pydantic-settings.
- Configuración async de SQLAlchemy + asyncpg.

4. app/base_driver.py
- Clase abstracta BaseDriver.
- Métodos abstractos:
  - create_vm
  - delete_vm
  - setup_network
  - rollback

5. app/factory.py
- Instanciar LinuxDriver cuando cluster_type == "linux".

6. app/linux/linux_driver.py
- Implementar ejecución remota usando AsyncSSH.
- Implementar:
  - create_vm
  - delete_vm
  - setup_network
  - rollback
- Manejo correcto de errores y rollback.

7. app/linux/qemu_commands.py
- Centralizar generación de comandos QEMU.
- Incluir SIEMPRE:
  - -pidfile
- Los comandos deben cumplir exactamente rule-driver.md.

8. app/linux/ovs_commands.py
- Centralizar comandos Open vSwitch.
- Usar:
  - ovs-vsctl --may-exist
- Implementar lógica de Patch Ports remotos según la lógica L2 definida.

Aclaraciones adicionales:

Rollback:
- El método `rollback` en `app/linux/linux_driver.py`
  debe ser capaz de:
  - eliminar interfaces TAP
  - eliminar el bridge `br-sl-{id}` únicamente si queda vacío
- Está estrictamente prohibido:
  - modificar/eliminar el bridge `br-wk`
  - modificar/eliminar la interfaz física `ens4`

SSH:
- En `app/linux/linux_driver.py`, si la variable
  `SSH_ENABLED=false`, los comandos deben ejecutarse localmente
  usando:
  - `asyncio.create_subprocess_exec`
- Si `SSH_ENABLED=true`, debe utilizarse `AsyncSSH`.
- La lógica de ejecución debe mantenerse transparente para el resto
  del driver.

Persistencia:
- Asegura que el Driver actualice correctamente la tabla `virtual_machines`
  usando los datos obtenidos del Worker.
- Actualiza el estado de la tabla `tasks` a `READY`
  cuando la operación finalice correctamente.
- Usa exclusivamente los nombres de columnas definidos en
  `db/init_schema.sql`.
- No inventes columnas ni estructuras ORM distintas al esquema SQL.

Restricción crítica:
Después de lanzar QEMU, linux_driver.py DEBE:
1. Leer el archivo `.pid`
2. Obtener el PID real del proceso QEMU
3. Retornar ese process_id en la respuesta

No uses PID del shell ni de subprocess.
Debe usarse exclusivamente el PID almacenado en `.pid`.

Entrega esperada:
- Código completo listo para ejecutar
- Imports corregidos
- Tipado completo
- Async/await consistente
- Sin pseudocódigo
- Sin TODOs
- Sin stubs vacíos