#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GaelaniLIVE Manager para PC.

Sube, baja, convierte y controla los vídeos del fondo animado de la PS5 por red.
Solo necesita Python 3 (sin librerías externas) y ffmpeg para convertir.

Ejemplos:
  python tools/gaelanilive_manager.py --host 192.168.1.50 estado
  python tools/gaelanilive_manager.py convertir clips/
  python tools/gaelanilive_manager.py empujar clips/mi.mp4
  python tools/gaelanilive_manager.py borrar 3
  python tools/gaelanilive_manager.py volumen 70
"""
import argparse
import http.client
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

PUERTO = 9050
BLOQUE = 1024 * 1024
EXT_VIDEO = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".ts", ".flv", ".wmv", ".mpg", ".mpeg", ".3gp")


def error(msg):
    print("error: " + msg, file=sys.stderr)
    sys.exit(1)


def api(host, ruta):
    """GET a la PS5; devuelve el JSON como dict."""
    url = "http://%s:%d%s" % (host, PUERTO, ruta)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.URLError as e:
        error("no se pudo contactar con la PS5 en %s (%s). ¿Está cargado el payload?" % (url, getattr(e, "reason", e)))
    except ValueError:
        error("la PS5 respondió algo que no es JSON en %s" % url)


def api_ok(host, ruta):
    d = api(host, ruta)
    if not d.get("ok"):
        error(d.get("error") or "la PS5 rechazó la operación (%s)" % ruta)
    return d


def estado(host):
    return api(host, "/api/state")


def videos(st):
    return st.get("videos") or []


def idx_por_nombre_o_indice(st, arg):
    vs = videos(st)
    if arg.isdigit():
        i = int(arg)
        if 0 <= i < len(vs):
            return i
        error("índice %d fuera de rango (0..%d)" % (i, len(vs) - 1))
    for i, v in enumerate(vs):
        if v.get("name") == arg or os.path.basename(v.get("path", "")) == arg:
            return i
    error("no existe ningún vídeo llamado %r (usa 'lista' para verlos)" % arg)


def subir(host, ruta):
    nombre = os.path.basename(ruta)
    if not nombre.lower().endswith(".mp4"):
        error("%s no es .mp4 (conviértelo antes: 'convertir' o 'empujar')" % nombre)
    tam = os.path.getsize(ruta)
    if tam == 0:
        error("%s está vacío" % nombre)
    conn = http.client.HTTPConnection(host, PUERTO, timeout=600)
    try:
        conn.putrequest("POST", "/api/upload?name=" + urllib.parse.quote(nombre))
        conn.putheader("Content-Length", str(tam))
        conn.endheaders()
        with open(ruta, "rb") as f:
            while True:
                b = f.read(BLOQUE)
                if not b:
                    break
                conn.sendall(b)
        r = conn.getresponse()
        cuerpo = r.read().decode("utf-8", "replace")
        try:
            d = json.loads(cuerpo)
        except ValueError:
            d = {"ok": r.status == 200}
        if not d.get("ok"):
            error("fallo al subir %s: %s" % (nombre, d.get("error") or cuerpo[:200]))
        print("subido: %s (%s)" % (nombre, tam_legible(tam)))
    except OSError as e:
        error("la conexión con la PS5 falló al subir %s: %s" % (nombre, e))
    finally:
        conn.close()


def bajar(host, i, destino):
    url = "http://%s:%d/video?i=%d" % (host, PUERTO, i)
    try:
        with urllib.request.urlopen(url, timeout=300) as r, open(destino, "wb") as f:
            while True:
                b = r.read(BLOQUE)
                if not b:
                    break
                f.write(b)
        print("guardado: %s (%s)" % (destino, tam_legible(os.path.getsize(destino))))
    except urllib.error.URLError as e:
        error("no se pudo descargar: %s" % getattr(e, "reason", e))


def tam_legible(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return "%.1f %s" % (n, u) if u != "B" else "%d B" % n
        n /= 1024.0


def hallar_ffmpeg():
    cands = [os.environ.get("FFMPEG"),
             os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe"),
             os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "GaelaniLIVE-Converter", "ffmpeg.exe")]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    w = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if w:
        return w
    error("no se encontró ffmpeg (ponlo en GaelaniLIVE-Converter\\ o define la variable FFMPEG)")


def convertir(archivo, salida, hevc, force, ffmpeg):
    if os.path.exists(salida) and not force:
        print("omitido (ya existe): %s" % os.path.basename(salida))
        return True
    sw = "if(gt(iw*ih,3686400),3840,if(gt(iw*ih,2073600),2560,1920))"
    sh = "if(gt(iw*ih,3686400),2160,if(gt(iw*ih,2073600),1440,1080))"
    pw = "if(gt(iw,2560)+gt(ih,1440),3840,if(gt(iw,1920)+gt(ih,1080),2560,1920))"
    ph = "if(gt(iw,2560)+gt(ih,1440),2160,if(gt(iw,1920)+gt(ih,1080),1440,1080))"
    vf = ("scale=w='%s':h='%s':force_original_aspect_ratio=decrease:force_divisible_by=2:flags=lanczos,"
          "pad=w='%s':h='%s':x=(ow-iw)/2:y=(oh-ih)/2,format=yuv420p" % (sw, sh, pw, ph))
    codec = "libx265" if hevc else "libx264"
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-stats", "-y", "-i", archivo,
           "-map", "0:v:0", "-map", "0:a?", "-vf", vf,
           "-fpsmax", "60", "-c:v", codec]
    if hevc:
        cmd += ["-x265-params", "keyint=60:min-keyint=30:scenecut=0:open-gop=0:ref=4"]
    else:
        cmd += ["-profile:v", "high", "-x264-params", "keyint=60:min-keyint=30:scenecut=0:open-gop=0:ref=4"]
    cmd += ["-preset", "slow", "-crf", "17", "-maxrate", "40M", "-bufsize", "60M",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart", salida]
    print("convirtiendo: %s -> %s" % (os.path.basename(archivo), os.path.basename(salida)))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print("FALLIDO: %s" % os.path.basename(archivo), file=sys.stderr)
        return False
    print("OK: %s (%s)" % (os.path.basename(salida), tam_legible(os.path.getsize(salida))))
    return True


def expandir(rutas):
    out = []
    for ruta in rutas:
        if os.path.isdir(ruta):
            for nom in sorted(os.listdir(ruta)):
                p = os.path.join(ruta, nom)
                if os.path.isfile(p) and nom.lower().endswith(EXT_VIDEO):
                    out.append(p)
        elif os.path.isfile(ruta):
            out.append(ruta)
        else:
            error("no existe: %s" % ruta)
    if not out:
        error("ningún vídeo que convertir")
    return out


def cmd_convertir(a):
    ffmpeg = hallar_ffmpeg()
    fallos = 0
    for p in expandir(a.rutas):
        base, _ = os.path.splitext(p)
        if not convertir(p, base + "_ps5.mp4", a.hevc, a.force, ffmpeg):
            fallos += 1
    sys.exit(1 if fallos else 0)


def cmd_empujar(a):
    ffmpeg = hallar_ffmpeg()
    fallos = 0
    for p in expandir(a.rutas):
        if p.lower().endswith(".mp4"):
            subir(a.host, p)
            continue
        base, _ = os.path.splitext(p)
        salida = base + "_ps5.mp4"
        if convertir(p, salida, a.hevc, a.force, ffmpeg):
            subir(a.host, salida)
        else:
            fallos += 1
    sys.exit(1 if fallos else 0)


def cmd_subir(a):
    for p in expandir(a.rutas):
        subir(a.host, p)


def cmd_estado(a):
    st = estado(a.host)
    print("fondo: %s" % ("encendido" if st.get("enabled") else "apagado"))
    print("estado: %s" % (st.get("status") or "-"))
    print("actual: %s" % (st.get("current") or "-"))
    print("volumen: %s%%  oscurecer: %s%%  mezclar: %s" %
          (st.get("volume"), st.get("dim"), "sí" if st.get("shuffle") else "no"))
    vs = videos(st)
    print("vídeos: %d" % len(vs))


def cmd_lista(a):
    vs = videos(estado(a.host))
    if not vs:
        print("no hay vídeos (sube alguno con 'subir' o 'empujar')")
        return
    for i, v in enumerate(vs):
        marcas = []
        if v.get("fav"):
            marcas.append("fav")
        if v.get("k4"):
            marcas.append("4K")
        if not v.get("snd"):
            marcas.append("sin audio")
        if v.get("why"):
            marcas.append("aviso: " + v["why"])
        print("%3d  %-40s  %8s  %s" % (i, v.get("name", "?"), tam_legible(v.get("size", 0)),
                                       ",".join(marcas) or v.get("res", "")))


def cmd_borrar(a):
    st = estado(a.host)
    i = idx_por_nombre_o_indice(st, a.objetivo)
    nombre = videos(st)[i].get("name")
    if not a.si:
        resp = input("¿Borrar %s de la PS5? [s/N] " % nombre).strip().lower()
        if resp not in ("s", "si", "sí", "y", "yes"):
            print("cancelado")
            return
    api_ok(a.host, "/api/delete?i=%d" % i)
    print("borrado: %s" % nombre)


def cmd_elegir(a):
    api_ok(a.host, "/api/select?i=%d" % a.indice)
    print("reproduciendo el vídeo %d" % a.indice)


def cmd_onoff(a):
    api_ok(a.host, "/api/" + ("on" if a.encender else "off"))
    print("fondo %s" % ("encendido" if a.encender else "apagado"))


def cmd_volumen(a):
    if not 0 <= a.n <= 100:
        error("el volumen va de 0 a 100")
    api_ok(a.host, "/api/volume?v=%d" % a.n)
    print("volumen: %d%%" % a.n)


def cmd_oscurecer(a):
    if not 0 <= a.n <= 80:
        error("el oscurecimiento va de 0 a 80")
    api_ok(a.host, "/api/dim?v=%d" % a.n)
    print("oscurecer: %d%%" % a.n)


def cmd_mezclar(a):
    api_ok(a.host, "/api/set?k=shuffle&v=%d" % (0 if a.apagar else 1))
    print("mezclar (vídeo aleatorio): %s" % ("desactivado" if a.apagar else "activado"))


def cmd_apagar(a):
    if not a.si:
        resp = input("¿Apagar GaelaniLIVE en la PS5? [s/N] ").strip().lower()
        if resp not in ("s", "si", "sí", "y", "yes"):
            print("cancelado")
            return
    api_ok(a.host, "/api/shutdown")
    print("gaelanilive detenido (vuelve a cargar el payload cuando quieras)")


def cmd_bajar(a):
    st = estado(a.host)
    i = idx_por_nombre_o_indice(st, a.objetivo)
    v = videos(st)[i]
    destino = a.archivo or v.get("name") or ("video_%d.mp4" % i)
    bajar(a.host, i, destino)


def main():
    p = argparse.ArgumentParser(description="GaelaniLIVE Manager: vídeos del fondo de la PS5 desde el PC")
    p.add_argument("--host", default=os.environ.get("GAELANI_HOST", "127.0.0.1"),
                   help="IP de la PS5 en la red (o variable GAELANI_HOST)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("estado", help="ver estado del fondo").set_defaults(fn=cmd_estado)
    sub.add_parser("lista", help="listar vídeos de la PS5").set_defaults(fn=cmd_lista)

    s = sub.add_parser("subir", help="subir .mp4 ya convertidos")
    s.add_argument("rutas", nargs="+"); s.set_defaults(fn=cmd_subir)

    s = sub.add_parser("convertir", help="convertir vídeos aptos para la PS5 (local)")
    s.add_argument("rutas", nargs="+"); s.add_argument("--force", action="store_true")
    s.add_argument("--hevc", action="store_true", help="salir en HEVC en vez de H.264")
    s.set_defaults(fn=cmd_convertir)

    s = sub.add_parser("empujar", help="convertir si hace falta y subir a la PS5")
    s.add_argument("rutas", nargs="+"); s.add_argument("--force", action="store_true")
    s.add_argument("--hevc", action="store_true")
    s.set_defaults(fn=cmd_empujar)

    s = sub.add_parser("bajar", help="descargar un vídeo de la PS5")
    s.add_argument("objetivo", help="índice o nombre"); s.add_argument("-o", "--archivo")
    s.set_defaults(fn=cmd_bajar)

    s = sub.add_parser("borrar", help="borrar un vídeo de la PS5")
    s.add_argument("objetivo", help="índice o nombre"); s.add_argument("--si", action="store_true")
    s.set_defaults(fn=cmd_borrar)

    s = sub.add_parser("elegir", help="reproducir un vídeo ahora")
    s.add_argument("indice", type=int); s.set_defaults(fn=cmd_elegir)

    s = sub.add_parser("on", help="encender el fondo"); s.set_defaults(fn=cmd_onoff, encender=True)
    s = sub.add_parser("off", help="apagar el fondo"); s.set_defaults(fn=cmd_onoff, encender=False)

    s = sub.add_parser("volumen", help="sonido de los vídeos (0-100)")
    s.add_argument("n", type=int); s.set_defaults(fn=cmd_volumen)

    s = sub.add_parser("oscurecer", help="oscurecer el vídeo (0-80)")
    s.add_argument("n", type=int); s.set_defaults(fn=cmd_oscurecer)

    s = sub.add_parser("mezclar", help="vídeo aleatorio al inicio")
    s.add_argument("--apagar", action="store_true"); s.set_defaults(fn=cmd_mezclar)

    s = sub.add_parser("apagar", help="detener GaelaniLIVE en la PS5")
    s.add_argument("--si", action="store_true"); s.set_defaults(fn=cmd_apagar)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
