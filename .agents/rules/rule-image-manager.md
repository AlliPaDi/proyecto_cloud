---
trigger: model_decision
description: Actívate en /image-manager/ para validar la existencia de imágenes .qcow2 en el Server 4. Obliga al uso de Thin Provisioning mediante Backing Files y gestiona el catálogo central de SO.
---

# Especificación Técnica: Image Manager (Storage Guardian)

## Stack Tecnológico
- **Lenguaje:** Python 3.12
- **Framework:** FastAPI
- **File Interaction:** Librerías `os` y `pathlib` para verificación de sistema de archivos.

## Responsabilidad Operativa
Actuar como el bibliotecario del almacenamiento centralizado en el Server 4, validando imágenes antes de cualquier intento de despliegue.

## Gestión de Imágenes y Thin Provisioning
- **Validación:** Verifica que la `base_image` solicitada (ej. Ubuntu 24.04) esté presente en `/mnt/storage/base/`.
- **Regla de Oro (CoW):** Debe generar la instrucción técnica para que el Driver use exclusivamente: `qemu-img create -f qcow2 -b {base_img} {inst_img}`.
- **Ubicación de Instancia:** Define la ruta de escritura para el disco de la VM en `/mnt/storage/instances/{vm_id}.qcow2`.

## Restricciones Técnicas
- **Inmutabilidad:** Las imágenes base en el Server 4 deben ser de solo lectura para los Workers.
- **Seguridad:** Validar que el nombre de la imagen solicitado no contenga secuencias de escape de directorio (Path Traversal).
- **Reporte:** Informar al sistema de monitoreo sobre el espacio disponible en el disco del Server 4.