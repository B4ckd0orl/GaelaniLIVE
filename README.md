# GaelaniLIVE Engine

**Fondos de pantalla animados (vídeo) para la pantalla de inicio de la PS5.**

[![version](https://img.shields.io/badge/version-1.0.0-blue?style=flat-square)]()
[![platform](https://img.shields.io/badge/platform-PS5-003791?style=flat-square)]()
[![license](https://img.shields.io/badge/license-GPL--3.0-green?style=flat-square)](LICENSE)

GaelaniLIVE es un proyecto derivado de **[LiveShell](https://github.com/ZiZc3/LiveShell)** de ZiZc3,
reescrito y traducido al español, con interfaz renovada, propios recursos y nuevas funciones.

---

## Funciones

- **Descubre**: fondos animados para descargar desde la propia PS5, por categorías.
- **Biblioteca**: da a cada juego y app su propio vídeo (experimental).
- **Solo PS Store**: el vídeo se muestra únicamente en la casilla de la PlayStation Store.
- **Listas de reproducción**: el fondo cambia solo entre los vídeos elegidos.
- **Sonido**: los vídeos con audio lo reproducen; la música del juego cede el paso.
- **Tus clips** del almacenamiento interno o de un USB.
- **Estilos**: Oscurecer, Viñeta, Bruma — combinables.
- **Ocultar en Ajustes**: Ajustes mantiene el fondo normal de la PS5.
- **Pausa con juego en marcha** para ceder el decodificador al juego.
- **Parallax** al moverte entre juegos.
- **Vídeo aleatorio** en cada inicio.
- **Reposo**: vuelve solo al despertar la consola.
- **App en la pantalla de inicio** para elegir y controlar todo.
- **Página móvil/PC** para subir, reproducir y borrar vídeos.
- **Interfaz en español** (app de la PS5, página remota y notificaciones).

## Instalación

Necesitas una PS5 con jailbreak y un cargador de payloads.

1. Copia archivos `.mp4` a `/data/GaelaniLIVE/video`, o a una carpeta `gaelanilive` en un USB.
2. Carga `gaelanilive.elf`.
3. Abre **GaelaniLIVE Engine** en la pantalla de inicio (Media).

Vídeos: H.264 o HEVC, 8-bit, hasta 4K, con o sin sonido. Usa el conversor de `GaelaniLIVE-Converter/`.

## Carpetas en la PS5

| Ruta | Contenido |
| --- | --- |
| `/data/GaelaniLIVE/video/` | Tus vídeos |
| `<USB>/gaelanilive/` | Vídeos en un USB |
| `/data/GaelaniLIVE/config.txt` | Ajustes |
| `/data/GaelaniLIVE/gaelanilive.log` | Registro |

## Construcción

Linux o WSL, con el [PS5 payload SDK](https://github.com/ps5-payload-dev/sdk) y el árbol
de [OnionHEN](https://github.com/aydencharles/onionHEN) **v0.9.0-beta2**:

```sh
ONIONHEN=~/onionHEN-beta2 PS5_PAYLOAD_SDK=~/ps5-payload-sdk tools/build.sh
```

`src/` se copia a OnionHEN como `source/gaelanilive` y se construye con el objetivo `gaelanilive`.

También hay un workflow de GitHub Actions (`.github/workflows/build.yml`) que compila
`gaelanilive.elf` automáticamente en cada push y lo publica como artifact/Release.

## Herramientas

- `GaelaniLIVE-Converter/` — convierte cualquier vídeo a un formato apto para la PS5 (arrastra y suelta).
- `tools/gaelanilive_manager.py` — gestor para PC: convierte, sube y borra vídeos por red.
- `tools/analyze_elf.py` — análisis y desensamblado completo de un ELF (Capstone).
- `tools/make_icon.py` — regenera el icono `icon0.png` (512×512).

## Créditos

- **[ZiZc3/LiveShell](https://github.com/ZiZc3/LiveShell)** — proyecto original del que deriva GaelaniLIVE (v1.5.0). Sin él esto no existiría.
- **[OnionHEN](https://github.com/aydencharles/onionHEN/)** — inyector de payloads, librería de detours y base de ShellUI.
- **[PS5 Payload SDK](https://github.com/ps5-payload-dev/sdk)** — toolchain y librerías para PS5.

## Licencia

GPL-3.0. Ver [LICENSE](LICENSE).

Este proyecto es un derivado de LiveShell (© ZiZc3) distribuido bajo los términos de la
GNU General Public License v3.0. Debe mantenerse la licencia, las atribuciones y el
código fuente disponible.
