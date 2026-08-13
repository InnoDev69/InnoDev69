# Configuración de los assets automáticos

Este repositorio genera sus propias imágenes de estadísticas (`assets/*.svg`)
en lugar de depender de servicios externos como github-readme-stats. Los
datos se obtienen directamente de la API de GitHub mediante un script en
Python, y un workflow de GitHub Actions se encarga de mantenerlos
actualizados.

## Pasos para activarlo en tu repositorio InnoDev69/InnoDev69

1. **Crear un Personal Access Token (classic)**
   - Anda a GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Generá uno nuevo con el scope `read:user` (alcanza para leer tus propias
     estadísticas y repos públicos; si querés incluir repos privados en el
     conteo, agregá también `repo`)
   - Copiá el token, no lo vas a volver a ver

2. **Agregarlo como secret del repositorio**
   - En tu repo: Settings → Secrets and variables → Actions → New repository secret
   - Nombre: `ASSETS_TOKEN`
   - Valor: el token que generaste

3. **Subir estos archivos a tu repositorio**
   - `scripts/generate_assets.py`
   - `.github/workflows/update-assets.yml`
   - `README.md` (ya actualizado para usar `./assets/*.svg`)
   - Podés borrar `SETUP.md` una vez que todo funcione

4. **Ejecutar el workflow por primera vez**
   - Anda a la pestaña "Actions" de tu repo
   - Seleccioná "Update README assets" → "Run workflow"
   - Esto va a generar la carpeta `assets/` con los tres SVG y va a
     commitearlos automáticamente

5. **Verificar**
   - Confirmá que aparezcan `assets/stats.svg`, `assets/streak.svg` y
     `assets/languages.svg` en el repo
   - Revisá el README en GitHub para confirmar que las imágenes cargan

A partir de ahí, el workflow corre solo todos los días a las 06:00 UTC y
mantiene los assets actualizados sin que tengas que hacer nada.

## Personalización

Todo el diseño (colores, tamaños, textos) vive en
`scripts/generate_assets.py`, en las funciones `generate_stats_svg`,
`generate_streak_svg` y `generate_languages_svg`. Podés cambiar la paleta
editando las constantes `COLOR_BG`, `COLOR_CARD`, `COLOR_BORDER`, etc. al
principio del archivo.
