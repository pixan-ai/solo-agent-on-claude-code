# 02 — systemd service

El agente corre como `systemd --user` service. No requiere systemd-system, no requiere `sudo` salvo para activar lingering una vez.

## Pre-checks

```bash
# Lingering: el user service sigue corriendo después del logout SSH.
sudo loginctl enable-linger $USER
loginctl show-user $USER | grep Linger   # Linger=yes

# Directorio de unidades:
mkdir -p ~/.config/systemd/user
```

## Unit file

`templates/service.example` contiene la versión completa. Esta es la forma que está corriendo en producción del autor. Las decisiones de diseño y por qué cada campo importa están abajo.

```ini
[Unit]
Description=Claude Code agent — myagent
Documentation=https://docs.claude.com/en/docs/claude-code
After=network-online.target nss-lookup.target
Wants=network-online.target nss-lookup.target

[Service]
Type=forking
WorkingDirectory=%h/agents/myagent
Environment="PATH=%h/.bun/bin:%h/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="CLAUDE_CONFIG_DIR=%h/.claude-myagent"
EnvironmentFile=%h/.env.global

ExecStartPre=/bin/sh -c 'for i in $(seq 1 30); do getent hosts api.anthropic.com >/dev/null 2>&1 && exit 0; sleep 1; done; exit 1'

ExecStart=/usr/bin/tmux -L myagent new-session -d -s myagent \
    -c %h/agents/myagent \
    %h/.local/bin/claude --dangerously-skip-permissions \
        --channels plugin:discord@claude-plugins-official \
                   plugin:telegram@claude-plugins-official

ExecStop=/usr/bin/tmux -L myagent kill-server

Restart=on-failure
RestartSec=10
KillMode=mixed

[Install]
WantedBy=default.target
```

### Por qué `tmux`

Claude Code se diseñó para una sesión interactiva con TTY. Bajo `Type=simple` con `ExecStart=claude ...` directo, parte del manejo de input/output queda mal porque no hay terminal. Envolver el binario en `tmux new-session -d` da el TTY que `claude` espera y le permite seguir escribiendo prompts y leyendo respuestas. `Type=forking` se usa porque `tmux -d` se desprende inmediatamente del proceso padre.

`KillMode=mixed` hace que `systemctl stop` envíe SIGTERM al proceso principal (el cliente tmux que ya salió) y SIGKILL al resto del cgroup (incluyendo el server tmux y `claude`). Sin `mixed`, los procesos hijos pueden sobrevivir al stop.

`-L myagent` da un socket tmux dedicado por agente. Si corres varios agentes en el mismo servidor, sus tmux servers no se pisan.

### Por qué `--channels`

El flag `--channels` indica a Claude Code que debe arrancar los channel handlers (Discord, Telegram) como parte de la sesión. Sin él, los plugins están instalados pero no escuchan eventos. La sintaxis es `plugin:<nombre>@<marketplace>`. Ver [05-channels.md](05-channels.md) para configurar los plugins primero.

### Por qué el `ExecStartPre` con `getent`

El service arranca en `network-online.target`, que solo garantiza que la interfaz tiene IP — no que DNS resuelva. En arranques de servidor, hay una ventana de 1–10 segundos donde DNS puede fallar antes de que el resolver se estabilice. Si Claude Code arranca antes y la primera resolución falla, el cliente OAuth puede entrar en un estado raro. El loop espera a que `api.anthropic.com` resuelva, hasta 30s.

### `EnvironmentFile`

`~/.env.global` con permisos `600` contiene secrets:

```bash
ELEVENLABS_API_KEY="sk_..."
REPLICATE_API_TOKEN="r8_..."
# y cualquier otro token que skills o plugins necesiten
```

systemd lee el archivo y exporta cada variable al proceso. **Nunca commitear.** Excluido en `.gitignore`. Ver `templates/env.example`.

Plugins que requieren un archivo `.env` propio (Discord, Telegram suelen leerlo de un path específico) se inicializan con un `ExecStartPre` adicional que reescribe ese archivo desde la variable de entorno correspondiente. Detalles en [05-channels.md](05-channels.md).

### Restart policy

`Restart=on-failure` reinicia solo si el proceso sale con código distinto de cero. No usar `Restart=always`: eso reinicia incluso después de un `systemctl stop` voluntario.

`RestartSec=10` evita loops de reinicio agresivos cuando el problema es persistente.

## Habilitar y arrancar

```bash
systemctl --user daemon-reload
systemctl --user enable --now myagent.service
```

## Operación

```bash
# Status
systemctl --user status myagent.service

# Logs en vivo
journalctl --user -u myagent.service -f

# Últimas N líneas
journalctl --user -u myagent.service -n 100 --no-pager

# Restart después de editar el .service
systemctl --user daemon-reload
systemctl --user restart myagent.service

# Conectarse al tmux para ver/interactuar con la sesión
tmux -L myagent attach -t myagent
# Detach con Ctrl-b d (no Ctrl-c — eso mata la sesión)

# Stop sin que reinicie
systemctl --user stop myagent.service

# Disable (no arranca al boot)
systemctl --user disable myagent.service
```

## Múltiples agentes en el mismo servidor

Un unit file por agente, cada uno con su `WorkingDirectory`, `CLAUDE_CONFIG_DIR` y socket tmux distintos:

```
~/.config/systemd/user/
├── alpha.service     → CLAUDE_CONFIG_DIR=~/.claude-alpha    tmux -L alpha
├── beta.service      → CLAUDE_CONFIG_DIR=~/.claude-beta     tmux -L beta
```

Si las cuentas Claude que respaldan cada agente son distintas, las cuotas (incluyendo el cupo de runs `CronCreate`/`ScheduleWakeup`/`RemoteTrigger`) son independientes.

## Healthcheck externo (opcional)

`Restart=on-failure` no detecta procesos vivos pero colgados. Si quieres un check activo:

```bash
crontab -e
# */15 * * * * systemctl --user is-active myagent.service > /dev/null \
#   || systemctl --user restart myagent.service
```

Es belt-and-suspenders y no sustituye a investigar la causa real cuando un proceso se cuelga.
