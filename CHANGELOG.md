# Changelog

Todos los cambios notables de GaelaniLIVE.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).

## [v1.1.0] - 2026-10-22

### Añadido
- **Auto-actualización**: "Actualizaciones" (en Acerca de, y en Sistema del remoto)
  comprueba el release en GitHub, descarga `gaelanilive.elf`, verifica el sha256,
  lo instala con verificación de firma ELF y reinicia el payload. Ante un arranque
  fallido revierte automáticamente a la versión anterior (ventana de estabilización
  de 30 s); si la versión recién instalada arranca bien, la ventana continúa y se
  confirma al estabilizarse.
- **Color de acento configurable**: 8 temas (Azul, Cian, Verde, Ámbar, Naranja,
  Rosa, Violeta, Rojo) aplicados a pestañas, interruptores, segmentos activos y
  puntos de estado; sincronizados entre la página principal y el remoto.
- **Diagnóstico**: registro del payload (logtail) visible desde la UI con
  copiar/refrescar.

### Cambiado
- UI 100 % en español: etiquetas, botones, toasts, mensajes de error y avisos del
  payload (tabs, controles de imagen/sonido, listas, listas de reproducción,
  cargador del remoto).
- Marca unificada **GaelaniLIVE** (sin subtítulo) en la UI, los avisos y el tile.
- Salida total en 4K: vista previa, textos y arte sin salir de FHD como base.
- Ajustes de imagen renombrados en español: Oscurecer, Viñeta, Neblina; segmentos
  No/Suave/Fuerte; sonido: Silencio/Sonido.

### Corregido
- Remoto: botón "Ocultar mientras hay un juego abierto" con marcado incompleto que
  hacía que pulsar sus controles alternara también esa opción.
- Remoto: textos mezclados inglés/español en la sección de usuarios y en las
  pistas de las categorías.
- Cuenta de elementos "seleccionados" con singular/plural correcto en listas.

## [v1.0.0] - 2026-10-22

### Añadido
- Primera versión: rebrand completo a GaelaniLIVE, UI en español, compilación
  automática en CI (OnionHEN v0.9.0-beta2 + PS5 Payload SDK), herramientas de
  conversión y gestión por PC.
