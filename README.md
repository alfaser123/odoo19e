# odoo19e

Proyecto para trabajo con Odoo 19 Enterprise usando la ruta `odoo/addons`.

## Estructura

- `odoo/addons/`: addons de Odoo Enterprise incluidos en el proyecto.
- `odoo/extra-addons/`: addons adicionales cargados desde el ZIP externo.
- `custom_addons/`: módulos propios o de terceros en desarrollo.
- `config/odoo.conf`: configuración base de Odoo.
- `docker-compose.yml`: Odoo + PostgreSQL para desarrollo local.

## Arranque local

1. Copia el archivo de entorno:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Ajusta `.env` si necesitas otro puerto o imagen de Odoo.

3. Levanta los servicios:

   ```powershell
   docker compose up -d
   ```

4. Abre Odoo en `http://localhost:8069`.

La configuración carga los addons desde:

```text
/mnt/odoo/addons,/mnt/odoo/extra-addons,/mnt/custom_addons
```

En Windows, esas rutas corresponden a `.\odoo\addons`, `.\odoo\extra-addons` y `.\custom_addons` dentro del proyecto.
