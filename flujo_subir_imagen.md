# Requerimientos de Desarrollo: Módulo de Carga e Importación de Imágenes de Disco (.img)

## Objetivo
Implementar una interfaz en el Frontend y su correspondiente integración que permita a los administradores cargar archivos de imágenes de disco (`.img`), registrarlos públicamente en el servicio de imágenes (Glance de OpenStack) usando el formato `QCOW2`, y posteriormente eliminarlos cuando termine la validación.

---

## 1. Interfaz de Usuario (Frontend)

El sistema debe contar con una sección o pestaña llamada **"Gestión de Imágenes de Sistema"** con los siguientes componentes:

### A. Vista de Listado de Imágenes
* Una tabla que muestre las imágenes registradas en el sistema con las columnas: **Nombre**, **Formato de Disco**, **Visibilidad**, **Tamaño** y **Acciones** (Botón Eliminar).

### B. Formulario de Carga (Modal o Vista)
Un botón de "Cargar Nueva Imagen" que abra un formulario con los siguientes campos:
* **Nombre de la Imagen (Input texto):** Ej. `ubuntu-24.04-minimal`.
* **Archivo de Imagen (Drag & Drop / Selector de archivos):** Debe aceptar archivos con extensión `.img` o `.qcow2`.
* **Formato de Disco (Dropdown/Select):** Opción por defecto fija en `QCOW2` (pero con soporte para expandirse a otros en el futuro).
* **Formato de Contenedor (Dropdown/Select):** Opción por defecto fija en `Bare`.
* **Visibilidad (Checkbox o Switch):** Opción por defecto activada en `Public` (Pública).

---

## 2. Flujo de Trabajo Técnico e Integración

Al presionar el botón **"Guardar/Cargar"**, el Frontend debe realizar lo siguiente:

### Paso 1: Envío del archivo al Backend
* El Frontend enviará el archivo físico junto con los metadatos (Nombre, Formato, Visibilidad) mediante un `POST` usando un formato `multipart/form-data` a la API de tu backend.

### Paso 2: Ejecución del Comando en Backend (Referencia para Lógica)
* El backend recibirá el archivo temporalmente en el servidor (`HeadNode`) y deberá ejecutar de manera automatizada el comando de OpenStack Glance, mapeando las variables de la UI:

```bash
glance image-create --name "[Nombre_UI]" \
  --file [Ruta_Archivo_Temporal] \
  --disk-format qcow2 \
  --container-format bare \
  --visibility public
Paso 3: Borrado Seguro (Requerimiento de Limpieza)
Acción de Eliminación: En la tabla de listado, al hacer clic en el botón "Eliminar", el Frontend enviará una petición DELETE con el ID de la imagen.

El sistema invocará internamente el comando glance image-delete [ID] para limpiar los servidores tras la validación del examen.

3. Criterios de Aceptación para la UI
[ ] El selector de archivos valida que se suban formatos de disco válidos (.img).

[ ] La UI muestra una barra de progreso o un spinner de carga mientras el archivo grande se sube y procesa en Glance (proceso que puede tardar unos minutos).

[ ] Al finalizar la carga exitosa, la tabla se refresca automáticamente mostrando la nueva plantilla disponible para ser usada en el editor de topologías.