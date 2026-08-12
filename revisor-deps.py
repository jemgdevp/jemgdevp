#!/usr/bin/env python3
"""Revisor de dependencias antes de subir a producción.

Reemplaza a Dependabot, apagado a propósito en todos los repos el 12ago2026.
Hace las dos cosas que Dependabot hacía, y una que no hacía:

  1. VULNERABILIDADES — corre el auditor NATIVO de cada ecosistema presente.
     No reimplementa nada: `pnpm audit`, `composer audit`, `pip-audit`,
     `cargo audit`, `govulncheck`.

  2. EDAD DE LA VERSIÓN — lo que pnpm 11 llama `minimumReleaseAge` y que solo
     existe en el mundo npm. Aquí se aplica a los CINCO ecosistemas: una
     dependencia directa publicada hace menos de N días no la ha mirado nadie
     todavía, y no entra a producción por inercia.

  3. Un solo comando para un repo poliglota, sin config.

Uso:
    ./revisor-deps.py [ruta]            # revisa el repo (por defecto, el cwd)
    ./revisor-deps.py --dias 14         # piso de edad más estricto
    ./revisor-deps.py --json            # salida para máquinas
    ./revisor-deps.py --autotest        # prueba del propio revisor

Salida: 0 sin hallazgos · 1 con hallazgos · 2 error de ejecución.

Solo stdlib: se instala copiándolo. Sin dependencias es imposible que el
revisor de dependencias tenga un problema de dependencias.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PISO_DIAS_POR_DEFECTO = 7
TIEMPO_ESPERA = 15


# ── utilidades ──────────────────────────────────────────────────────────────


def correr(cmd: list[str], cwd: Path) -> tuple[int, str]:
    """Ejecuta un comando y devuelve (código, salida). Nunca lanza."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, f"no instalado: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout: {' '.join(cmd)}"


def pedir_json(url: str) -> dict | None:
    """GET a un registro público. Devuelve None si falla — nunca lanza."""
    try:
        peticion = urllib.request.Request(
            url, headers={"User-Agent": "revisor-deps (jemgdevp)"}
        )
        with urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None


def primer_json(texto: str):
    """Extrae el primer objeto o lista JSON de una salida con ruido delante."""
    inicios = [i for i in (texto.find("{"), texto.find("[")) if i != -1]
    if not inicios:
        return None
    try:
        return json.loads(texto[min(inicios) :])
    except json.JSONDecodeError:
        return None


def edad_en_dias(fecha_iso: str, ahora: datetime | None = None) -> float | None:
    """Días transcurridos desde una fecha ISO-8601. None si no se puede leer.

    Pura y con `ahora` inyectable: es lo que permite que --autotest compruebe
    el piso sin depender del día en que se corra.
    """
    if not fecha_iso:
        return None
    texto = fecha_iso.strip().replace("Z", "+00:00")
    # Los registros no se ponen de acuerdo con los decimales del segundo.
    texto = re.sub(r"\.(\d{1,6})\d*", r".\1", texto)
    try:
        publicada = datetime.fromisoformat(texto)
    except ValueError:
        return None
    if publicada.tzinfo is None:
        publicada = publicada.replace(tzinfo=timezone.utc)
    referencia = ahora or datetime.now(timezone.utc)
    return (referencia - publicada).total_seconds() / 86400


# ── fechas de publicación, un registro por ecosistema ────────────────────────


def fecha_npm(paquete: str, version: str) -> str | None:
    datos = pedir_json(f"https://registry.npmjs.org/{paquete}")
    return (datos or {}).get("time", {}).get(version)


def fecha_composer(paquete: str, version: str) -> str | None:
    datos = pedir_json(f"https://repo.packagist.org/p2/{paquete}.json")
    for entrada in (datos or {}).get("packages", {}).get(paquete, []):
        if entrada.get("version", "").lstrip("v") == version.lstrip("v"):
            return entrada.get("time")
    return None


def fecha_pypi(paquete: str, version: str) -> str | None:
    datos = pedir_json(f"https://pypi.org/pypi/{paquete}/{version}/json")
    archivos = (datos or {}).get("urls") or []
    return archivos[0].get("upload_time_iso_8601") if archivos else None


def fecha_crates(paquete: str, version: str) -> str | None:
    datos = pedir_json(f"https://crates.io/api/v1/crates/{paquete}/{version}")
    return (datos or {}).get("version", {}).get("created_at")


def escapar_modulo_go(ruta: str) -> str:
    """proxy.golang.org exige minúsculas: cada mayúscula va como !minúscula."""
    return re.sub(r"([A-Z])", lambda m: "!" + m.group(1).lower(), ruta)


def fecha_go(modulo: str, version: str) -> str | None:
    url = (
        f"https://proxy.golang.org/{escapar_modulo_go(modulo)}"
        f"/@v/{escapar_modulo_go(version)}.info"
    )
    return (pedir_json(url) or {}).get("Time")


# ── dependencias directas, un comando nativo por ecosistema ─────────────────


def directas_npm(raiz: Path) -> list[tuple[str, str]]:
    gestor = "pnpm" if (raiz / "pnpm-lock.yaml").exists() else "npm"
    codigo, salida = correr([gestor, "list", "--depth", "0", "--json"], raiz)
    if codigo not in (0, 1):
        return []
    datos = primer_json(salida)
    if isinstance(datos, list):
        datos = datos[0] if datos else {}
    if not isinstance(datos, dict):
        return []
    fuera = []
    for clave in ("dependencies", "devDependencies"):
        for nombre, info in (datos.get(clave) or {}).items():
            version = info.get("version") if isinstance(info, dict) else None
            if version:
                fuera.append((nombre, version))
    return fuera


def directas_composer(raiz: Path) -> list[tuple[str, str]]:
    codigo, salida = correr(
        ["composer", "show", "--direct", "--format=json", "--no-interaction"], raiz
    )
    if codigo != 0:
        return []
    datos = primer_json(salida)
    if not isinstance(datos, dict):
        return []
    return [
        (p["name"], p["version"].lstrip("v"))
        for p in datos.get("installed", [])
        if p.get("name") and p.get("version") and "/" in p["name"]
    ]


def directas_python(raiz: Path) -> list[tuple[str, str]]:
    for cmd in (
        ["uv", "pip", "list", "--format=json"],
        ["pip", "list", "--format=json"],
    ):
        codigo, salida = correr(cmd, raiz)
        if codigo == 0:
            datos = primer_json(salida)
            if isinstance(datos, list):
                return [(p["name"], p["version"]) for p in datos if p.get("version")]
    return []


def directas_rust(raiz: Path) -> list[tuple[str, str]]:
    codigo, salida = correr(
        ["cargo", "tree", "--depth", "1", "--prefix", "none", "--no-dedupe"], raiz
    )
    if codigo != 0:
        return []
    vistos: dict[str, str] = {}
    for linea in salida.splitlines()[1:]:
        m = re.match(r"^\s*([a-zA-Z0-9_\-]+)\s+v(\d[\w.\-+]*)", linea)
        if m:
            vistos.setdefault(m.group(1), m.group(2))
    return list(vistos.items())


def directas_go(raiz: Path) -> list[tuple[str, str]]:
    """Del go.mod: el bloque require SIN el marcador `// indirect`."""
    texto = (raiz / "go.mod").read_text(encoding="utf-8", errors="replace")
    fuera = []
    for linea in texto.splitlines():
        if "// indirect" in linea:
            continue
        m = re.match(
            r"^\s*(?:require\s+)?([\w.\-/~]+\.[\w.\-/~]+)\s+(v[\w.\-+]+)", linea
        )
        if m:
            fuera.append((m.group(1), m.group(2)))
    return fuera


# ── ecosistemas ─────────────────────────────────────────────────────────────

ECOSISTEMAS = [
    {
        "nombre": "npm",
        "marca": ["package.json"],
        "auditor": lambda raiz: (
            ["pnpm", "audit"] if (raiz / "pnpm-lock.yaml").exists() else ["npm", "audit"]
        ),
        "directas": directas_npm,
        "fecha": fecha_npm,
    },
    {
        "nombre": "composer",
        "marca": ["composer.json"],
        "auditor": lambda raiz: ["composer", "audit", "--no-interaction"],
        "directas": directas_composer,
        "fecha": fecha_composer,
    },
    {
        "nombre": "python",
        "marca": ["pyproject.toml", "requirements.txt", "uv.lock"],
        "auditor": lambda raiz: ["pip-audit"],
        "directas": directas_python,
        "fecha": fecha_pypi,
    },
    {
        "nombre": "rust",
        "marca": ["Cargo.toml"],
        "auditor": lambda raiz: ["cargo", "audit"],
        "directas": directas_rust,
        "fecha": fecha_crates,
    },
    {
        "nombre": "go",
        "marca": ["go.mod"],
        "auditor": lambda raiz: ["govulncheck", "./..."],
        "directas": directas_go,
        "fecha": fecha_go,
    },
]


def revisar(raiz: Path, piso_dias: int) -> dict:
    informe: dict = {"raiz": str(raiz), "piso_dias": piso_dias, "ecosistemas": []}

    for eco in ECOSISTEMAS:
        if not any((raiz / m).exists() for m in eco["marca"]):
            continue

        resultado: dict = {
            "nombre": eco["nombre"],
            "vulnerabilidades": None,
            "auditor_disponible": True,
            "recien_publicadas": [],
            "sin_fecha": [],
            "directas_revisadas": 0,
        }

        cmd_audit = eco["auditor"](raiz)
        codigo, salida = correr(cmd_audit, raiz)
        if codigo == 127:
            resultado["auditor_disponible"] = False
            resultado["vulnerabilidades"] = f"auditor no instalado: {cmd_audit[0]}"
        else:
            resultado["vulnerabilidades"] = (
                "limpio" if codigo == 0 else salida.strip()[-1500:]
            )

        for nombre, version in eco["directas"](raiz):
            resultado["directas_revisadas"] += 1
            fecha = eco["fecha"](nombre, version)
            if fecha is None:
                resultado["sin_fecha"].append(f"{nombre}@{version}")
                continue
            dias = edad_en_dias(fecha)
            if dias is not None and dias < piso_dias:
                resultado["recien_publicadas"].append(
                    {
                        "paquete": nombre,
                        "version": version,
                        "publicada": fecha,
                        "dias": round(dias, 1),
                    }
                )

        informe["ecosistemas"].append(resultado)

    return informe


def hay_hallazgos(informe: dict, estricto: bool = False) -> bool:
    """En modo estricto, no haber podido mirar TAMBIÉN es un hallazgo.

    Sin esto, un CI sin `pnpm` en la imagen devuelve 0 y el pipeline pasa en
    verde sin haber revisado nada. Es el falso verde clásico: el auditor
    ausente no es un repo limpio.
    """
    for eco in informe["ecosistemas"]:
        if eco["auditor_disponible"] and eco["vulnerabilidades"] != "limpio":
            return True
        if eco["recien_publicadas"]:
            return True
        if estricto and not eco["auditor_disponible"]:
            return True
        if estricto and eco["directas_revisadas"] == 0:
            return True
    return False


def pintar(informe: dict) -> None:
    piso = informe["piso_dias"]
    if not informe["ecosistemas"]:
        print("Ningún ecosistema reconocido en", informe["raiz"])
        return

    for eco in informe["ecosistemas"]:
        print(f"\n── {eco['nombre']} ({eco['directas_revisadas']} directas) ──")

        if not eco["auditor_disponible"]:
            print(f"  ⚠  {eco['vulnerabilidades']} — vulnerabilidades SIN revisar")
        elif eco["vulnerabilidades"] == "limpio":
            print("  ✓  vulnerabilidades: ninguna")
        else:
            print("  ✗  VULNERABILIDADES:")
            for linea in eco["vulnerabilidades"].splitlines()[:25]:
                print("     ", linea)

        if eco["recien_publicadas"]:
            print(f"  ✗  RECIÉN PUBLICADAS (piso: {piso} días):")
            for p in sorted(eco["recien_publicadas"], key=lambda x: x["dias"]):
                print(f"      {p['paquete']}@{p['version']} — {p['dias']} días")
        else:
            print(f"  ✓  edad: ninguna directa por debajo de {piso} días")

        if eco["sin_fecha"]:
            muestra = ", ".join(eco["sin_fecha"][:6])
            resto = len(eco["sin_fecha"]) - 6
            cola = f" (+{resto} más)" if resto > 0 else ""
            print(f"  ·  sin fecha en el registro: {muestra}{cola}")


# ── prueba del propio revisor ───────────────────────────────────────────────


def autotest() -> int:
    """Un caso que DEBE fallar y uno que DEBE pasar. Independiente de la fecha."""
    fallos = []
    ahora = datetime(2026, 8, 12, tzinfo=timezone.utc)

    # DEBE FALLAR: publicada ayer contra un piso de 7 días.
    dias = edad_en_dias("2026-08-11T03:09:37.754Z", ahora)
    print(f"  caso que DEBE fallar  → edad {dias:.1f} días, piso 7 → ", end="")
    if dias is not None and dias < 7:
        print("FALLA ✓ (correcto)")
    else:
        print("PASA ✗ (el piso no está mordiendo)")
        fallos.append("una versión de 1 día no debería pasar un piso de 7")

    # DEBE PASAR: publicada hace más de un año.
    dias = edad_en_dias("2025-04-14T20:20:31.218Z", ahora)
    print(f"  caso que DEBE pasar   → edad {dias:.1f} días, piso 7 → ", end="")
    if dias is not None and dias >= 7:
        print("PASA ✓ (correcto)")
    else:
        print("FALLA ✗ (el piso es un falso positivo)")
        fallos.append("una versión de más de un año debería pasar")

    # Una fecha ilegible no puede colarse como "vieja, todo bien".
    print("  fecha ilegible        → ", end="")
    if edad_en_dias("no-es-una-fecha") is None and edad_en_dias("") is None:
        print("None ✓ (se reporta sin fecha, no como aprobada)")
    else:
        print("✗ (una fecha rota se está tratando como válida)")
        fallos.append("una fecha ilegible debe devolver None")

    # El falso verde que --estricto existe para tapar: un CI sin el auditor en
    # la imagen no revisa nada y, sin el flag, devolvería 0.
    ciego = {
        "ecosistemas": [
            {
                "nombre": "npm",
                "auditor_disponible": False,
                "vulnerabilidades": "auditor no instalado: pnpm",
                "recien_publicadas": [],
                "directas_revisadas": 0,
            }
        ]
    }
    print("  auditor ausente       → ", end="")
    if not hay_hallazgos(ciego, estricto=False) and hay_hallazgos(ciego, estricto=True):
        print("permisivo PASA · --estricto FALLA ✓ (correcto)")
    else:
        print("✗ (el modo estricto no está tapando el falso verde)")
        fallos.append("con --estricto, un auditor ausente debe ser hallazgo")

    # El camino HTTP de verdad, contra una versión que ya no va a cambiar.
    print("  registro npm en vivo  → ", end="")
    fecha = fecha_npm("axios", "1.0.0")
    if fecha and (edad_en_dias(fecha) or 0) > 365:
        print(f"axios@1.0.0 publicada {fecha[:10]} ✓")
    else:
        print(f"✗ (no se pudo leer la fecha: {fecha!r}) — ¿sin red?")
        fallos.append("no se pudo consultar registry.npmjs.org")

    print()
    if fallos:
        for f in fallos:
            print("FALLO:", f)
        return 1
    print("autotest: todo correcto")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Revisa deps (vulnerabilidades + edad) antes de producción."
    )
    ap.add_argument(
        "ruta", nargs="?", default=".", help="raíz del repo (por defecto: .)"
    )
    ap.add_argument(
        "--dias",
        type=int,
        default=PISO_DIAS_POR_DEFECTO,
        help=f"piso de edad en días (por defecto: {PISO_DIAS_POR_DEFECTO})",
    )
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument(
        "--estricto",
        action="store_true",
        help="un auditor ausente o cero directas también cuenta como hallazgo (para CI)",
    )
    ap.add_argument("--autotest", action="store_true", help="prueba el propio revisor")
    args = ap.parse_args()

    if args.autotest:
        return autotest()

    raiz = Path(args.ruta).resolve()
    if not raiz.is_dir():
        print(f"no es un directorio: {raiz}", file=sys.stderr)
        return 2

    informe = revisar(raiz, args.dias)

    if args.json:
        print(json.dumps(informe, indent=2, ensure_ascii=False))
    else:
        pintar(informe)

    if hay_hallazgos(informe, args.estricto):
        if not args.json:
            print("\nHAY HALLAZGOS — esto no sube a producción sin mirarlo.")
        return 1

    if not args.json:
        print("\nSin hallazgos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
