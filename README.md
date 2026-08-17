<p align="center">
  <img src="./assets/hero.svg" width="900"
       alt="jemg@jemg.dev — os: Arch Linux · shell: bash · back: Laravel 13 con PHP 8.5 · front: Vue 3 con Inertia y TypeScript · infra: Docker, Traefik y FrankenPHP · data: PostgreSQL, pgvector, Valkey y RustFS · apps: os, peer y pearl · also: Rust, Go y Python" />
</p>

<h1 align="center">Juan Esteban Manrique Giraldo</h1>

<p align="center"><strong>Desarrollador full-stack</strong> · Autodidacta · Manizales, Colombia</p>

<p align="center">
  <a href="https://jemg.dev">jemg.dev</a> ·
  <a href="https://www.linkedin.com/in/thisfeeling">LinkedIn</a> ·
  <a href="mailto:murksopps@gmail.com">murksopps@gmail.com</a>
</p>

<p align="center">
Diseño, construyo y opero aplicaciones web de punta a punta — de la API al despliegue.<br>
Arquitectura por dominios, monolito modular y self-hosting detrás de Cloudflare, todo dockerizado.<br>
Escribo código pensando en quien lo tenga que leer dentro de seis meses.
</p>

<p align="center">
<sub><strong>Cómo trabajo</strong> — tecnología aburrida y estable · KISS · YAGNI · PMV primero · <strong>progreso y disciplina</strong></sub>
</p>

### Stack

- **Backend** — Laravel 13 · PHP 8.5 · PostgreSQL + pgvector · Valkey · Pest
- **Frontend** — Vue 3 · Inertia · TypeScript · Tailwind 4 · Pinia + Pinia Colada · vee-validate + zod · TanStack Table · Vitest
- **Infra** — Docker · Traefik · FrankenPHP + Octane · RustFS (S3) · Woodpecker CI · Linux (Arch)
- **También** — Rust · Go · Python · servidores MCP

### En qué ando

- Un ecosistema propio de apps self-host bajo `jemg.dev` — piezas pequeñas con una tarea cada
  una, interconectadas por **MCP** en vez de acopladas entre sí.
- **Design system propio** en Storybook, no plantillas genéricas: tokens, componentes y sus
  estados cubiertos por tests.
- **Datastores compartidos** por la plataforma — un Postgres, un Valkey, un RustFS para todo;
  cada app aporta su contenedor, no los suyos.
- Todo feature lleva **test en el mismo commit** y pasa por gates (Pint · Larastan · Pest ·
  Vitest) antes de tocar `develop`.

<p align="center"><sub>Español (nativo) · Inglés (técnico)</sub></p>
