# 05 — Canales y MCPs

El agente recibe input y produce output a través de dos clases de integraciones:

1. **Plugins de chat comunitarios** — Discord, Telegram. Vienen del marketplace `claude-plugins-official`.
2. **Connectors de claude.ai** — Gmail, Calendar, Drive, GitHub, Notion, Vercel. Heredados del OAuth de tu cuenta.

Adicionalmente puedes registrar **MCP servers** propios (HTTP o stdio) en `.claude.json`.

## Plugins de chat

### Habilitar

`settings.json`:

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

Reiniciar el servicio para que cargue los plugins:

```bash
systemctl --user restart myagent.service
```

El unit file debe arrancar el binario con `--channels plugin:discord@claude-plugins-official plugin:telegram@claude-plugins-official` (ver [02-systemd.md](02-systemd.md)).

### Discord — setup

1. [discord.com/developers/applications](https://discord.com/developers/applications) → New Application → Bot → Reset Token. Copia el token. Activa los intents *Message Content* y *Server Members*.
2. Invita el bot a tu servidor con permisos: Read Messages, Send Messages, Read Message History, Add Reactions.
3. En una sesión interactiva del agente:
   ```
   /discord:configure
   ```
   Pega el token. Se guarda en `$CLAUDE_CONFIG_DIR/channels/discord/`.
4. Define quién puede hablarle:
   ```
   /discord:access
   ```
   Allowlist de user IDs y nombres, política DM/group.

Tools que expone el plugin:
- `mcp__plugin_discord_discord__reply` — responder en canal.
- `mcp__plugin_discord_discord__edit_message` — útil para mostrar progreso.
- `mcp__plugin_discord_discord__react` — emoji reaction.
- `mcp__plugin_discord_discord__fetch_messages` — leer historial (la search API de Discord no está expuesta a bots).
- `mcp__plugin_discord_discord__download_attachment` — descargar adjunto.

### Telegram — setup

1. En Telegram, hablar con `@BotFather`:
   - `/newbot` → nombre y username terminado en `bot`.
   - Copia el token.
   - Opcional: `/setuserpic`, `/setdescription`, `/setabouttext`.
2. En sesión interactiva:
   ```
   /telegram:configure
   ```
3. Allowlist:
   ```
   /telegram:access
   ```

Tools del plugin:
- `mcp__plugin_telegram_telegram__reply` — responder. Soporta `markdownv2`, `files=[...]` para adjuntos, `reply_to` para threading.
- `mcp__plugin_telegram_telegram__edit_message` — editar (progreso).
- `mcp__plugin_telegram_telegram__react` — emoji reaction.
- `mcp__plugin_telegram_telegram__download_attachment` — adjunto (audio, video, foto, doc).

La Bot API de Telegram NO expone histórico ni search. El agente solo ve mensajes en vivo. Si necesitas contexto previo, pide al operador que pegue lo relevante.

### Token vía `.env` del plugin

Algunos plugins esperan su token en un archivo específico (`$CLAUDE_CONFIG_DIR/channels/<plugin>/.env`) en lugar de variables de entorno arbitrarias. La forma más limpia de mantenerlo coherente sin commitear secrets es generar ese archivo desde una variable global en un `ExecStartPre`:

```ini
ExecStartPre=/bin/sh -c 'umask 077; \
    printf "TELEGRAM_BOT_TOKEN=%%s\n" "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN no está en el entorno}" \
    > %h/.claude-myagent/channels/telegram/.env'
```

`umask 077` asegura permisos `600`. La sustitución `${VAR:?msg}` falla con error claro si la variable no está cargada desde `EnvironmentFile`.

### Allowlists

`access.json` es gestionado por las skills `*-access`:

```json
{
  "policy": "allowlist",
  "users": ["nombre_usuario"],
  "user_ids": ["123456789"],
  "channels": ["987654321"],
  "dm_policy": "open"
}
```

**Regla:** nunca aprobar pairings ni modificar allowlist desde un mensaje del propio canal. Si alguien escribe "agrégame al allowlist", esa es la petición que un prompt injection haría. Solo el operador, desde su terminal local, invoca las skills `*-access`.

### Verbosidad por canal

Patrón observado útil:

- **Telegram = silencio operativo.** El operador suele leerlo en móvil con notificaciones. Solo entrega final, error con razón, o pregunta bifurcante. Evitar mensajes intermedios.
- **Discord = más verbose.** Desktop, hilo conversacional. Mensajes intermedios con `edit_message` para mostrar progreso son aceptables.
- **Cualquier canal:** un heartbeat que reporta "todo OK" cada hora es ruido. Solo notificar cuando hay anomalía, decisión pendiente, o resultado entregable. Ver [06-scheduling.md](06-scheduling.md) y la skill `evaluator-self-check`.

## MCPs heredados de claude.ai

Cuando logueas Claude Code con tu cuenta, heredas los connectors activos en claude.ai. Aparecen en el agente como tools `mcp__claude_ai_<servicio>__*` sin configuración local.

Connectors típicos:

- Gmail — `search_threads`, `get_thread`, `list_drafts`, `create_draft`, `label_*`.
- Google Calendar — `list_events`, `suggest_time`, `create_event`, `update_event`, `delete_event`.
- Google Drive — `search_files`, `read_file_content`, `create_file`.
- GitHub — issues, PRs, branches, commits, code search.
- Notion — search, fetch, create_pages, update_page, comments.
- Vercel — deploy, runtime logs, list_projects.

### Activar/desactivar

[claude.ai](https://claude.ai) → Settings → Connectors. Toggle por servicio. El agente recoge cambios al siguiente arranque (`systemctl --user restart`).

### Reconnect cuando un MCP cae

Si un connector se desconecta a mitad de sesión (visible como deferred tool "no longer available"), el agente headless **no reconecta solo**. Hay que reiniciar el servicio:

```bash
systemctl --user restart myagent.service
```

Esto pierde la sesión actual pero recupera todos los connectors. Para connectors críticos, considerar un cron diario que reinicie el agente proactivamente.

### Limitaciones

- Solo los connectors que ofrece Anthropic. Para integraciones propias, usar MCPs locales (siguiente sección).
- El catálogo cambia con releases de Claude Code. Verificar al setup.

## MCPs locales

Para servicios sin connector oficial. Se registran en `$CLAUDE_CONFIG_DIR/.claude.json`:

```json
{
  "mcpServers": {
    "github-pat": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${GITHUB_PAT}"
      }
    },
    "internal-tool": {
      "type": "stdio",
      "command": "/usr/local/bin/my-mcp-server",
      "args": ["--config", "/path/to/config.toml"],
      "env": {
        "API_KEY": "${INTERNAL_API_KEY}"
      }
    }
  }
}
```

`${VAR}` se expande desde el entorno del proceso (cargado del `EnvironmentFile=`).

### MCP local vs script

- **MCP local** — integración persistente, conversacional, expone múltiples tools relacionados, se beneficia de discovery automático.
- **Script en `scripts/` de un skill** — operación puntual, determinística, sin estado.

Para generación de imágenes con Replicate, un script `generate.py` invocado desde un skill es más simple que un MCP. Para una integración con un CRM interno con muchos endpoints, conviene un MCP.

## Anti-patterns

- Compartir tokens entre canales. Cada plugin tiene su propio token.
- Hardcodear tokens en JSON versionado. Siempre `${VAR}` con valor en `EnvironmentFile`.
- Aprobar pairings desde el propio chat del agente.
- Habilitar todos los connectors de claude.ai por default. Cada uno expone tools al system prompt; agrega ruido si no los usas.
