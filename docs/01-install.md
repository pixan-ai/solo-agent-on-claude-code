# 01 — Instalación

Esta sección cubre la instalación del binario `claude` y la configuración de un directorio aislado que será propiedad del agente.

## Node.js

Claude Code se distribuye como paquete npm. Requiere Node 20 LTS o superior.

```bash
# nvm (per-user, sin sudo)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.0/install.sh | bash
source ~/.nvm/nvm.sh
nvm install --lts
node --version  # >= v20
```

Alternativa con `nodesource`/`apt` está documentada en el sitio oficial; cualquier método válido sirve.

## Claude Code

```bash
npm install -g @anthropic-ai/claude-code
claude --version
```

El binario queda en el `PATH` de Node. Si prefieres no instalar global, `npx @anthropic-ai/claude-code` también funciona, pero el unit file de la sección siguiente asume binario absoluto.

## Directorio aislado

Por defecto Claude Code lee y escribe en `~/.claude/`. Si vas a usar también el CLI interactivo en el mismo servidor, conviene aislar el agente para que no comparta credenciales, plugins ni sesiones.

```bash
export CLAUDE_CONFIG_DIR=~/.claude-myagent
mkdir -p "$CLAUDE_CONFIG_DIR"
```

A partir de aquí, **todas** las invocaciones del binario para este agente deben tener `CLAUDE_CONFIG_DIR` en su entorno. El unit file lo declara como `Environment=`; la sección [02-systemd.md](02-systemd.md) lo cubre.

## Login OAuth

```bash
CLAUDE_CONFIG_DIR=~/.claude-myagent claude login
```

El comando imprime una URL. En SSH headless: ábrela en tu laptop, autentica con la cuenta cuyo plan vas a reusar, pega el código de vuelta en la terminal.

Resultado: `$CLAUDE_CONFIG_DIR/.credentials.json`. Permisos restrictivos:

```bash
chmod 600 "$CLAUDE_CONFIG_DIR/.credentials.json"
```

Verificación:

```bash
CLAUDE_CONFIG_DIR=~/.claude-myagent claude --print "ok"
```

Debe responder en texto plano sin pedir login.

## settings.json mínimo

Un archivo en `$CLAUDE_CONFIG_DIR/settings.json` controla flags persistentes:

```json
{
  "skipDangerousModePermissionPrompt": true
}
```

`skipDangerousModePermissionPrompt: true` evita que el binario pida confirmación interactiva al arrancar con `--dangerously-skip-permissions`. Sin esto, una sesión sin TTY se cuelga al arrancar.

Implicación: el agente puede ejecutar shell, escribir archivos y llamar herramientas sin pedir aprobación. La separación de identidades (este agente vs tu CLI personal) y la lista de plugins habilitados son las únicas barreras. Documenta para ti mismo qué hace este agente y por qué confías en él.

`templates/settings.example.json` tiene el archivo completo, incluyendo plugins; ver [05-channels.md](05-channels.md) para detalles.

## Smoke test

Antes de armar el servicio, prueba que Claude Code arranca limpio:

```bash
mkdir -p ~/agents/myagent
cd ~/agents/myagent
CLAUDE_CONFIG_DIR=~/.claude-myagent claude \
    --dangerously-skip-permissions \
    --print "lista los archivos del directorio actual"
```

Si responde con la lista (vacía si no has creado nada), todo bien. Si pide login, `CLAUDE_CONFIG_DIR` no está siendo leído.

## Actualizaciones

```bash
npm update -g @anthropic-ai/claude-code
systemctl --user restart myagent.service
```

Versiones major pueden cambiar comportamiento de plugins o flags. Verifica las release notes de Claude Code antes de actualizar en producción.
