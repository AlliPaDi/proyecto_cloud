# Image Manager — Contrato de API (Puerto 8083)

## Endpoints

### GET /images/
Lista las imágenes base disponibles en `/mnt/storage/base/`.

**Output (200):**
```json
{
  "images": [
    {"name": "ubuntu-22.04.qcow2", "size_mb": 2048, "path": "/mnt/storage/base/ubuntu-22.04.qcow2"},
    {"name": "debian-12.qcow2", "size_mb": 1536, "path": "/mnt/storage/base/debian-12.qcow2"}
  ]
}
```

---

### GET /images/{name}/validate
Valida la existencia de una imagen base.

**Ejemplo:** `GET /images/ubuntu-22.04.qcow2/validate`

**Output (200):**
```json
{
  "exists": true,
  "name": "ubuntu-22.04.qcow2",
  "path": "/mnt/storage/base/ubuntu-22.04.qcow2"
}
```

**Errores:**
- `404`: Imagen no encontrada.

---

### POST /images/provision
Genera el comando de thin provisioning para una VM.

**Input:**
```json
{
  "vm_id": 3,
  "base_image": "ubuntu-22.04.qcow2"
}
```

**Output (200):**
```json
{
  "vm_id": 3,
  "base_path": "/mnt/storage/base/ubuntu-22.04.qcow2",
  "instance_path": "/mnt/storage/instances/3.qcow2",
  "command": "qemu-img create -f qcow2 -b /mnt/storage/base/ubuntu-22.04.qcow2 /mnt/storage/instances/3.qcow2"
}
```

**Errores:**
- `404`: Imagen base no existe.

---

## Configuración para testing local
```bash
# Variable de entorno para apuntar a una carpeta local
IMAGE_BASE_PATH=./test_images/

# Crear carpeta de prueba con imágenes dummy
mkdir -p test_images
touch test_images/ubuntu-22.04.qcow2
touch test_images/debian-12.qcow2
```

## Test cURL
```bash
# Listar imágenes
curl http://localhost:8083/images/

# Validar imagen existente
curl http://localhost:8083/images/ubuntu-22.04.qcow2/validate

# Validar imagen inexistente (espera 404)
curl http://localhost:8083/images/windows-11.qcow2/validate

# Provisionar disco
curl -X POST http://localhost:8083/images/provision \
  -H "Content-Type: application/json" \
  -d '{"vm_id": 3, "base_image": "ubuntu-22.04.qcow2"}'
```
