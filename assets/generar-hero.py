#!/usr/bin/env python3
"""Genera assets/hero.svg — la tarjeta neofetch del perfil de GitHub.

El SVG resultante es auto-contenido: sin scripts, sin hojas de estilo externas
y sin fuentes remotas, que es lo único que el proxy de imágenes de GitHub deja
pasar. El logotipo va en rectángulos y no en arte ASCII para que no dependa de
que la fuente del visitante tenga los caracteres de bloque.

    python3 assets/generar-hero.py && python3 assets/generar-hero.py --probar
"""

from pathlib import Path
import sys

ANCHO = 900
PANEL_ALTO = 424

FONDO = "#0b0e14"
BORDE = "#1c222c"
TENUE = "#5c6773"
TEXTO = "#c8d1dc"
ACENTO = "#4d9fd6"
VERDE = "#7ec699"

MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

# Mapa de bits 5x7 por letra. Una fila por cadena, '1' = píxel encendido.
LETRAS = {
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
}

PIXEL = 9  # paso de la rejilla
LADO = 8  # lado del rectángulo pintado (deja 1px de aire)

# Campos del panel. Cada valor está medido contra el repo real, no de memoria.
CAMPOS = [
    ("os", "Arch Linux"),
    ("shell", "bash"),
    ("back", "Laravel 13 · PHP 8.5"),
    ("front", "Vue 3 · Inertia · TypeScript"),
    ("infra", "Docker · Traefik · FrankenPHP"),
    ("data", "PostgreSQL · pgvector · Valkey · RustFS"),
    ("apps", "os · peer · pearl"),
    ("also", "Rust · Go · Python"),
]

LOGO_X = 48
COL_X = 300  # columna derecha: etiquetas
PUNTOS_X1, PUNTOS_X2 = 366, 392  # tramo de la línea punteada
VALOR_X = 404
HOST_Y = 120
CAMPO_Y0, CAMPO_PASO = 176, 28
CAMPO_YN = CAMPO_Y0 + (len(CAMPOS) - 1) * CAMPO_PASO

# El logotipo se centra contra la columna derecha en vez de fijarse a ojo, para
# que añadir o quitar un campo no descuadre la composición.
LOGO_Y = round((HOST_Y + CAMPO_YN) / 2 - (7 * PIXEL) / 2)


def logo(texto="JEMG"):
    """Devuelve (rects, ancho) del logotipo en píxeles."""
    partes, x = [], LOGO_X
    # El retardo crece en diagonal para que el logo entre con un barrido.
    for letra in texto:
        filas = LETRAS[letra]
        for fila, bits in enumerate(filas):
            for col, bit in enumerate(bits):
                if bit != "1":
                    continue
                retardo = 0.02 * (col + fila) + 0.10 * texto.index(letra)
                partes.append(
                    f'<rect class="px" x="{x + col * PIXEL}" y="{LOGO_Y + fila * PIXEL}"'
                    f' width="{LADO}" height="{LADO}" rx="1"'
                    f' style="animation-delay:{retardo:.2f}s"/>'
                )
        x += 5 * PIXEL + PIXEL  # ancho de la letra + una columna de aire
    return "\n    ".join(partes), x - PIXEL - LOGO_X


def campos():
    partes = []
    for i, (etiqueta, valor) in enumerate(CAMPOS):
        y = CAMPO_Y0 + i * CAMPO_PASO
        retardo = 0.55 + i * 0.07
        partes.append(
            f'<g class="linea" style="animation-delay:{retardo:.2f}s">'
            f'<text class="et" x="{COL_X}" y="{y}">{etiqueta}</text>'
            f'<line class="pt" x1="{PUNTOS_X1}" y1="{y - 5}" x2="{PUNTOS_X2}" y2="{y - 5}"/>'
            f'<text class="vl" x="{VALOR_X}" y="{y}">{valor}</text>'
            f"</g>"
        )
    return "\n    ".join(partes)


def construir():
    rects, _ = logo()
    prompt_y = CAMPO_YN + 52
    alto = prompt_y + 30
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {alto}"
     width="{ANCHO}" height="{alto}" role="img"
     aria-labelledby="titulo descripcion">
  <title id="titulo">jemg@jemg.dev</title>
  <desc id="descripcion">Tarjeta de terminal con el stack de Juan Esteban Manrique Giraldo:
    Arch Linux, Laravel 13 con PHP 8.5, Vue 3 con Inertia y TypeScript, Docker con Traefik y
    FrankenPHP, PostgreSQL con pgvector, Valkey y RustFS, las apps os, peer y pearl, y además
    Rust, Go y Python.</desc>
  <style>
    text {{ font-family: {MONO}; }}
    /* Sin `opacity: 0` de base a propósito: un renderizador que ignore las
       animaciones CSS debe ver la tarjeta completa, no una vacía. */
    .px {{ fill: {TEXTO}; animation: aparecer .28s ease-out both; }}
    .linea {{ animation: aparecer .3s ease-out both; }}
    .et {{ fill: {ACENTO}; font-size: 16px; }}
    .vl {{ fill: {TEXTO}; font-size: 16px; }}
    .pt {{ stroke: {TENUE}; stroke-width: 2; stroke-linecap: round; stroke-dasharray: 0 6; }}
    .prompt {{ fill: {VERDE}; font-size: 15px; }}
    .cmd {{ fill: {TENUE}; font-size: 15px; }}
    .host {{ fill: {ACENTO}; font-size: 17px; font-weight: 600; }}
    .regla {{ stroke: {BORDE}; stroke-width: 1; }}
    .cursor {{ fill: {VERDE}; animation: latir 1.06s steps(1) infinite; }}
    @keyframes aparecer {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes latir {{ 0%, 50% {{ opacity: 1; }} 50.01%, 100% {{ opacity: 0; }} }}
    @media (prefers-reduced-motion: reduce) {{
      .px, .linea {{ opacity: 1; animation: none; }}
      .cursor {{ animation: none; }}
    }}
  </style>

  <rect x="1" y="1" width="{ANCHO - 2}" height="{alto - 2}" rx="12"
        fill="{FONDO}" stroke="{BORDE}"/>

  <text class="prompt" x="{LOGO_X}" y="58">~$ <tspan class="cmd">neofetch</tspan></text>

  <g>
    {rects}
  </g>

  <text class="host" x="{COL_X}" y="120">jemg@jemg.dev</text>
  <line class="regla" x1="{COL_X}" y1="136" x2="{ANCHO - 48}" y2="136"/>

  <g>
    {campos()}
  </g>

  <text class="prompt" x="{LOGO_X}" y="{prompt_y}">~$ <tspan class="cursor">█</tspan></text>
</svg>
"""


def probar():
    """Comprobaciones mínimas: lo que rompería el SVG en GitHub."""
    svg = construir()
    assert "<script" not in svg, "GitHub descarta los SVG con script"
    assert "@import" not in svg and "https://" not in svg.replace(
        'xmlns="http://www.w3.org/2000/svg"', ""
    ), "sin recursos remotos: el proxy de GitHub no los sigue"
    assert svg.count("<rect") == sum(
        fila.count("1") for letra in "JEMG" for fila in LETRAS[letra]
    ) + 1, "un rect por píxel encendido, más el panel"
    assert all(f">{e}</text>" in svg for e, _ in CAMPOS), "falta alguna etiqueta"
    assert "prefers-reduced-motion" in svg, "la animación debe poder apagarse"
    # El contenido no puede depender de que la animación corra: un renderizador
    # que ignore las animaciones CSS dejaría la tarjeta en blanco.
    for regla in (".px", ".linea"):
        cuerpo = svg.split(regla + " {")[1].split("}")[0]
        assert "opacity: 0" not in cuerpo, f"{regla} se esconde sin animación"
    # Control negativo: una letra sin definir tiene que reventar, no pasar en silencio.
    try:
        LETRAS["Z"]
    except KeyError:
        pass
    else:
        raise AssertionError("LETRAS['Z'] no debería existir")
    print(f"ok — {len(svg)} bytes, {svg.count('<rect') - 1} píxeles, {len(CAMPOS)} campos")


if __name__ == "__main__":
    if "--probar" in sys.argv:
        probar()
    else:
        destino = Path(__file__).parent / "hero.svg"
        destino.write_text(construir(), encoding="utf-8")
        print(f"escrito {destino} ({destino.stat().st_size} bytes)")
