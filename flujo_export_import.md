# Requerimientos de Desarrollo: Gestión de Slices y Flujo de Topologías (Ex2)

## Objetivo
Implementar un flujo de trabajo en el Frontend que permita separar la **fase de diseño lógico** de una red de la **fase de orquestación y despliegue real**. El sistema debe permitir diseñar, listar, exportar e importar topologías en estado "Borrador" antes de interactuar con el clúster de OpenStack.

---

## 1. Modificaciones en el Modelo de Datos y Listado de Slices
* [cite_start]**Estado del Slice:** Asegurar que cada slice cuente con un atributo de estado (`status`), diferenciando claramente entre un slice **"Guardado/Borrador"** (solo existe en la Base de Datos) y un slice **"Desplegado"** (activo en la infraestructura)[cite: 21, 27].
* **Vista de Listado (Dashboard):** * Crear o adaptar un panel que liste todos los slices del sistema.
  * [cite_start]Los slices que aún no han sido desplegados deben ser completamente visibles en este listado[cite: 21].
  * Al seleccionar un slice no desplegado, el usuario debe poder abrir el **Editor de Topologías** en modo "Vista/Lectura" o "Edición" para observar el diseño lógico sin gatillar acciones en los servidores.

---

## 2. Flujo de Trabajo Requerido (Pasos del Examen)

### Paso A: Creación y Guardado (Ref: Paso 8 del examen)
* [cite_start]**Acción:** Permitir al usuario diseñar la topología especificada en el Anexo 1 utilizando el editor gráfico[cite: 21].
* [cite_start]**Comportamiento:** Al presionar "Guardar" con el nombre `Ex2_GXX_test`, el Frontend debe realizar una petición `POST` exclusivamente a la Base de Datos local[cite: 21]. [cite_start]**No se debe invocar** ninguna API de despliegue en OpenStack ni ejecutar el algoritmo de *Placement* aún[cite: 21].
* [cite_start]**Resultado:** El slice aparece en el listado con estado "Borrador/Inactivo"[cite: 21].

### Paso B: Exportación de Topología (Ref: Paso 9 del examen)
* [cite_start]**Acción:** Agregar un botón de **"Exportar Topología"** dentro del visor/editor del slice o directamente en su fila del listado[cite: 24].
* [cite_start]**Comportamiento:** Al hacer clic, el Frontend debe generar y descargar un archivo estructurado en formato **JSON** o **YAML**[cite: 24].
* [cite_start]**Contenido del archivo:** El archivo debe contener de forma limpia todos los parámetros lógicos del slice: nombres de las VMs, asignación de sabores (Cores, RAM, Almacenamiento), imágenes asociadas y las conexiones/enlaces entre nodos[cite: 24].

### Paso C: Importación y Clonación (Ref: Paso 10 del examen)
* [cite_start]**Acción:** Agregar un botón general de **"Importar Topología"** en la vista del listado de slices[cite: 26].
* [cite_start]**Comportamiento:** 1. El usuario sube el archivo JSON o YAML exportado previamente[cite: 26].
  2. [cite_start]El sistema debe parsear el archivo y abrir un diálogo solicitando un nuevo nombre para la topología[cite: 24, 26].
  3. [cite_start]Al ingresar el nombre `Ex2_GXX_test_2`, el sistema creará un **nuevo registro independiente** en la Base de Datos[cite: 26].
* [cite_start]**Resultado:** El listado ahora muestra dos slices en estado "Borrador" (`Ex2_GXX_test` y `Ex2_GXX_test_2`)[cite: 21, 26].

### Paso D: Despliegue Bajo Demanda (Ref: Paso 11 del examen)
* [cite_start]**Acción:** Para los slices en estado "Borrador", habilitar un botón explícito de **"Desplegar"**[cite: 27].
* [cite_start]**Comportamiento:** Al presionar este botón en `Ex2_GXX_test_2`, se debe invocar al Backend para que ejecute el algoritmo de *Placement*, asigne los recursos correspondientes en OpenStack y cambie el estado del slice a "Desplegado"[cite: 27].

---

## 3. Criterios de Aceptación para la UI
* [cite_start][ ] El usuario puede crear una topología, cerrarla y volverla a abrir desde el listado sin que se haya creado ninguna VM real[cite: 21].
* [cite_start][ ] El botón "Exportar" descarga un JSON/YAML legible y ordenado para su revisión[cite: 24].
* [cite_start][ ] La función de importación recrea fielmente la topología original con un nuevo nombre sin alterar el slice original[cite: 26].