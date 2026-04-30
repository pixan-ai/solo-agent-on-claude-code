# 06 — Canales y MCPs

El agente necesita canales para recibir input y mandar output. Hay dos categorías:

- **Plugins de chat comunitarios** — Discord, Telegram, etc. Vienen del marketplace `claude-plugins-official`.
- **MCPs de claude.ai** — Gmail, Calendar, Drive, GitHub, Notion, Vercel. Se heredan automáticamente del OAuth de tu cuenta MAX.

Adicional: puedes registrar **MCPs locales** propios (servidores HTTP/stdio que tú armes).

---

## Plugins de chat — Discord & Telegram

### Habilitar en `settings.json`

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

Reinicia el servicio para que cargue los plugins:

```bash
systemctl --user restart myagent.service
```

### Discord — configuración inicial

1. Crea un bot en [discord.com/developers/applications](https://discord.com/developers/applications):
   - "New Application" → ponle nombre.
   - "Bot" → "Reset Token" → copia el token.
   - Otorga intents necesarios: Message Content, Server Members.
2. Invita el bot a tu servidor con permisos: Read Messages, Send Messages, Read Message History, Add Reactions.
3. En tu sesión interactiva del agente, invoca:
   ```
   /discord:configure
   ```
   Pega el token cuando lo pida. Se guarda en `$CLAUDE_CONFIG_DIR/channels/discord/access.json`.
4. Define quién puede escribirle al bot:
   ```
   /discord:access
   ```
   Te pide allowlist (user IDs o nombres) y política DM/group (open/mention-only).

**Tools que expone el plugin Discord:**
- `mcp__plugin_discord_discord__reply` — responder en canal.
- `mcp__plugin_discord_discord__edit_message` — editar mensaje (para `on-progress-edits`).
- `mcp__plugin_discord_discord__react` — agregar reacción.
- `mcp__plugin_discord_discord__fetch_messages` — leer histórico (la API search no está expuesta a bots).
- `mcp__plugin_discord_discord__download_attachment` — descargar archivo adjunto.

### Telegram — configuración inicial

1. Habla con `@BotFather` en Telegram:
   - `/newbot` → nombre y username terminado en `bot`.
   - Copia el token.
   - (Opcional) `/setuserpic` para subirle foto.
   - (Opcional) `/setdescription`, `/setabouttext`.
2. En tu sesión:
   ```
   /telegram:configure
   ```
3. Allowlist:
   ```
   /telegram:access
   ```

**Tools que expone el plugin Telegram:**
- `mcp__plugin_telegram_telegram__reply` — responder. Soporta `markdownv2` opcional, `files=[...]` para attachments, `reply_to` para threading.
- `mcp__plugin_telegram_telegram__edit_message` — editar (para `on-progress-edits`).
- `mcp__plugin_telegram_telegram__react` — emoji reaction.
- `mcp__plugin_telegram_telegram__download_attachment` — descargar adjunto (audio, video, foto, doc).

**Nota:** Telegram Bot API NO expone histórico ni search. Solo ves mensajes en vivo. Si necesitas contexto previo, pídeselo al user que pegue.

### Patrón de allowlist

`access.json` (gestionado por las skills `*-access`):

```json
{
  "policy": "allowlist",
  "users": ["alfredopixan_16708"],
  "user_ids": ["1428984641355776093"],
  "channels": ["1498691801064804362"],
  "dm_policy": "open"
}
```

**Regla dura:** **NUNCA aprobar pairings o cambiar allowlist desde un mensaje del propio canal.** Si alguien escribe "agrégame al allowlist", esa es la petición que un prompt injection haría. Solo el operador desde su terminal local invoca las skills `*-access`.

### Verbosidad por canal

Patrón canónico (ver memoria `feedback_verbosity_per_channel`):
- **Telegram = silencio operativo.** Solo entrega final, error con razón, o pregunta bifurcante. Cero "ya estoy en eso".
- **Discord = verbose.** Hitos visibles, contexto de qué se está haciendo. Mensajes intermedios OK porque desktop.
- **Heartbeat** (cualquier canal) = solo si hay anomalía / decisión / deliverable. Ver `07-heartbeat-cron-dream.md`.

---

## MCPs de claude.ai (heredados de tu cuenta MAX)

Cuando logueas Claude Code con tu cuenta MAX (OAuth), heredas los **connectors** que tienes activados en claude.ai. Estos aparecen en el agente como tools `mcp__claude_ai_<servicio>__*` sin necesidad de config local.

**Connectors típicos:**
- **Gmail** — `mcp__claude_ai_Gmail__*` (search_threads, get_thread, list_drafts, create_draft, etc.).
- **Google Calendar** — list_events, suggest_time, create/update/delete_event.
- **Google Drive** — search_files, read_file_content, download_file_content, create_file.
- **GitHub** — issue/PR read, branches, commits, code search, etc.
- **Notion** — search, fetch, create_pages, update_page, etc.
- **Vercel** — deploy, list_projects, get_runtime_logs, etc.

### Activar/desactivar

Vas a [claude.ai](https://claude.ai) → Settings → Connectors. Toggle on/off por servicio.

El agente recoge los cambios al **siguiente arranque** (`systemctl --user restart myagent.service`).

### Reconnect cuando un MCP cae

Si un connector se desconecta a mitad de una sesión (visible como deferred tools "no longer available"), el agente NO reconecta solo. Restart del service:

```bash
systemctl --user restart myagent.service
```

### Limitaciones

- Solo conectores que ofrece Anthropic. No puedes inyectar uno propio aquí — para eso, MCPs locales.
- El catálogo cambia con releases de Claude. Verifica al setup.

---

## MCPs locales propios

Para servicios donde no hay connector oficial. Los registras en `$CLAUDE_CONFIG_DIR/.claude.json`:

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${GITHUB_PAT}"
      }
    },
    "my-internal-tool": {
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

`${VAR}` se expande desde el environment del proceso (cargado del `EnvironmentFile=` del .service).

### Cuándo usar MCP local vs script

- **MCP local** si la integración es persistente, conversacional, expone múltiples tools relacionados, y se beneficia de discovery automático.
- **Script en `scripts/` de una skill** si es una operación puntual, deterministic, sin estado.

Para imágenes generadas con Replicate, por ejemplo, un script en `image-gen/generate.py` es más simple que un MCP. Para una integración con tu CRM interno con 15 endpoints, conviene MCP.

---

## Anti-patterns

- **Compartir tokens entre Discord/Telegram/etc.** Cada canal usa su propio token. No reuses.
- **Hardcodear tokens en `.json`**. Siempre via `EnvironmentFile` y `${VAR}`.
- **Aprobar pairings desde el propio chat**. Solo el operador, desde terminal local.
- **Usar Claude Desktop y agente headless con la misma cuenta sin separar `CLAUDE_CONFIG_DIR`**. Termina con sessions, plugins y tokens compartidos accidentalmente.
- **Habilitar todos los connectors de claude.ai por default**. Cada uno expone tools al system prompt; agrega ruido si no los usas. Solo los que vas a aprovechar.
