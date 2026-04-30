# 02 — Instalación

## Instalar Claude Code

```bash
npm install -g @anthropic-ai/claude-code
claude --version  # verifica
```

Si no quieres global, usa `npx @anthropic-ai/claude-code` en cada invocación. Para servicio systemd, conviene global.

## Aislar el config con `CLAUDE_CONFIG_DIR`

Por defecto Claude Code guarda config en `~/.claude/`. Si tu cuenta de servidor también usa Claude Code interactivo, **vas a querer aislar el agente** para que no contamine sesiones, plugins, ni credentials del CLI normal.

**Patrón canónico:** un dir aparte por agente.

```bash
export CLAUDE_CONFIG_DIR=~/.claude-myagent
mkdir -p $CLAUDE_CONFIG_DIR
```

Pon esa env var en el `.service` (ver `03-systemd-service.md`). El binario `claude` respeta `CLAUDE_CONFIG_DIR` y guarda todo ahí: credentials, plugins, projects, sessions, history.

## Login OAuth (reusar tu suscripción MAX)

```bash
CLAUDE_CONFIG_DIR=~/.claude-myagent claude login
```

Te abre el flujo OAuth en navegador. Si estás en SSH headless:

1. El comando imprime una URL.
2. Abrela en tu laptop.
3. Logueate con la cuenta del MAX.
4. Pega el código de vuelta en la terminal.

Resultado: `$CLAUDE_CONFIG_DIR/.credentials.json` con el OAuth token. **Ese archivo es tu llave maestra al MAX para este agente. Cuídalo.** Permisos típicos: 600.

```bash
chmod 600 $CLAUDE_CONFIG_DIR/.credentials.json
```

### Verificar que el OAuth funciona

```bash
CLAUDE_CONFIG_DIR=~/.claude-myagent claude --print "hola, ¿quién eres?"
```

Debe responder en texto plano sin pedirte login.

## Settings.json mínima

Crea `$CLAUDE_CONFIG_DIR/settings.json` con lo esencial:

```json
{
  "skipDangerousModePermissionPrompt": true,
  "enabledPlugins": {},
  "extraKnownMarketplaces": {}
}
```

`skipDangerousModePermissionPrompt: true` evita que el binario te pregunte cada vez que arrancas con `--dangerously-skip-permissions` (necesario para servicio sin TTY). **Solo activa esto si confías en lo que el agente va a ejecutar** — hace que pueda correr cualquier shell, escribir archivos, etc., sin pedirte permiso. Es el comportamiento que un agente 24/7 necesita; es también el comportamiento que requiere disciplina (ver `08-memory.md` regla `untrusted_content`).

## Plugins comunitarios (opcional, recomendado)

Para chat con Discord/Telegram. Extiende `settings.json`:

```json
{
  "skipDangerousModePermissionPrompt": true,
  "enabledPlugins": {
    "discord@claude-plugins-official": true,
    "telegram@claude-plugins-official": true
  },
  "extraKnownMarketplaces": {
    "claude-plugins-official": {
      "source": {
        "source": "github",
        "repo": "anthropics/claude-plugins-official"
      }
    }
  }
}
```

Configuración detallada de cada plugin en `06-channels-mcp.md`.

## Workspace del agente

Crea el directorio donde va a vivir el "alma" del agente:

```bash
mkdir -p ~/agents/myagent
cd ~/agents/myagent
```

Aquí vas a poner SOUL.md, USER.md, etc. Detalle en `04-workspace-structure.md`.

## Smoke test antes de systemd

Antes de armar el .service, prueba que Claude Code arranca limpio en este workspace:

```bash
cd ~/agents/myagent
CLAUDE_CONFIG_DIR=~/.claude-myagent claude --dangerously-skip-permissions --print "lista los archivos del directorio actual"
```

Si responde con la lista (vacía si no has poblado nada), todo bien. Si te pide login, el `.credentials.json` no se está cargando — revisa `CLAUDE_CONFIG_DIR`.

## MCPs locales (opcional)

Si quieres conectar MCPs adicionales fuera de los que vienen via OAuth de claude.ai (Gmail, Calendar, Drive, GitHub, Notion, Vercel, etc., que se heredan de tu cuenta sin config local), edita `$CLAUDE_CONFIG_DIR/.claude.json`:

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${GITHUB_PAT}"
      }
    }
  }
}
```

Tokens van por env vars del servicio (ver `03-systemd-service.md`). **Nunca hardcodear secrets en JSON versionado.**

## Update path

Para actualizar Claude Code:

```bash
npm update -g @anthropic-ai/claude-code
systemctl --user restart claude-myagent.service
```

Verificar release notes antes de actualizar — versiones major pueden cambiar comportamiento de plugins.
