# revisor-deps

Revisor de dependencias que se corre **antes de subir a producción**. Sustituye a
Dependabot, apagado a propósito en todos los repos el **12ago2026**.

```bash
./revisor-deps.py                 # revisa el repo del directorio actual
./revisor-deps.py ~/Dev/node/peer # o el que le digas
./revisor-deps.py --dias 14       # piso de edad más estricto
./revisor-deps.py --estricto      # para CI: no haber podido mirar TAMBIÉN falla
./revisor-deps.py --json          # para máquinas
./revisor-deps.py --autotest      # se prueba a sí mismo
```

Salida: `0` sin hallazgos · `1` con hallazgos · `2` error. Sirve tal cual como paso de
un pipeline de release.

**`--estricto` no es opcional en CI.** Sin él, una imagen sin `pnpm` hace que el revisor
diga «SIN revisar» y devuelva `0`: el pipeline pasa en verde **sin haber mirado nada**.
Con `--estricto`, un auditor ausente o un ecosistema detectado con cero dependencias
leídas cuentan como hallazgo y el pipeline se pone rojo. En local, sin el flag, se
comporta como un aviso.

## En el CI (Woodpecker)

El paso va **antes de desplegar**, con la misma imagen que ya tiene `composer`, `pnpm` y
`python3`:

```yaml
  - name: revisor-deps
    image: ci-php-node:8.4
    pull: false
    commands:
      - python3 .ci/revisor-deps.py . --dias 7 --estricto
```

Va **después** del paso que instala (`composer install` y `pnpm install`): el revisor lee
lo que hay instalado, no lo instala él. Verificado el 12ago2026: la imagen
`ci-php-node:8.4` trae Python 3.13.5 en `/usr/bin/python3`.

## Qué revisa

Detecta el ecosistema por el archivo que lo delata y **no revisa lo que no está**.

| Ecosistema | Se activa con | Auditor nativo | Fechas |
|---|---|---|---|
| npm | `package.json` | `pnpm audit` / `npm audit` | registry.npmjs.org |
| composer | `composer.json` | `composer audit` | repo.packagist.org |
| python | `pyproject.toml` · `requirements.txt` · `uv.lock` | `pip-audit` | pypi.org |
| rust | `Cargo.toml` | `cargo audit` | crates.io |
| go | `go.mod` | `govulncheck` | proxy.golang.org |

**Vulnerabilidades:** no reimplementa nada, corre el auditor nativo de cada ecosistema.
Si el auditor no está instalado lo dice como `⚠ SIN revisar` — nunca lo cuenta como
verde. Un auditor ausente no es un repo limpio.

**Edad de la versión:** esto es lo que ninguna herramienta hace fuera del mundo npm.
pnpm 11 tiene `minimumReleaseAge` y Dependabot tenía `cooldown`, pero composer, PyPI,
crates.io y el proxy de Go no tienen ese concepto. Aquí se aplica a los cinco: cada
dependencia **directa** se consulta contra su registro y, si se publicó hace menos de N
días (7 por defecto), sale marcada. Una versión de tres horas no la ha mirado nadie.

## Por qué existe

Dependabot abría PRs que nadie revisaba y encima obligaba a mirar 36 alertas por repo,
20 de ellas duplicados del mismo paquete. Los auditores nativos ven exactamente el mismo
conjunto de paquetes — medido el 12ago2026 en diversotex: Dependabot 36 alertas,
`pnpm audit` 16 avisos, los mismos seis paquetes. La diferencia era ruido.

Lo que Dependabot **no** hacía es lo de la edad, y es lo que más duele: subir un `minor`
recién publicado a producción un viernes.

## Trampas medidas (en la VPS de Jemg)

- **`pnpm` y `php` viven detrás de shims de mise** y no siempre están en el `PATH` de un
  shell no interactivo. Si el revisor dice `auditor no instalado: pnpm`, córrelo así:

  ```bash
  PATH=/home/jemg/.local/share/mise/shims:$PATH ./revisor-deps.py <ruta>
  ```

- **El `composer` del `PATH` es el de PHP 8.5.6** y los repos que exigen `~8.4.0` fallan.
  Para esos hay que invocar composer con el PHP de mise.
- El revisor **no instala nada ni toca lockfiles**: solo lee y consulta. Es seguro
  correrlo sobre un árbol sucio.

## Cómo se lee un hallazgo

Que una dependencia salga por edad **no significa que esté rota**. Significa que es
demasiado nueva para que alguien la haya roto en público todavía. Las salidas son tres:

1. Esperar a que cumpla el piso y volver a correrlo.
2. Bajarla a la versión anterior y anotar el motivo en el commit.
3. Subirla igual, con el motivo escrito — que es lo que el canon ya exige para cualquier
   dependencia congelada.

Lo que **no** vale es no mirarlo.

## Primer hallazgo real (12ago2026, diversotex)

Corriéndolo sobre la rama `chore/deps-cobertura-panel-12ago` justo después de subir las
deps, con piso de 7 días:

```text
── composer (37 directas) ──
  ✓  vulnerabilidades: ninguna
  ✗  RECIÉN PUBLICADAS (piso: 7 días):
      pestphp/pest@5.1.1              — 0.2 días
      spatie/laravel-activitylog@5.1.0 — 0.3 días
      resend/resend-php@1.8.0          — 1.0 días
      laravel/framework@13.25.0        — 1.2 días
      ... 15 en total
```

Quince paquetes de menos de una semana, uno de ellos con **cinco horas de vida**, y el
`composer audit` en verde. Ese es justo el hueco que esta herramienta existe para tapar.
