# MemeCast — Protocole WebSocket

## Connexion

```
Client → ws://server:8000/ws
```

## Authentification (Client → Server)

```json
{
    "type": "auth",
    "guild_id": "123456789012345678",
    "discord_id": "987654321098765432"
}
```

### Réponse OK (Server → Client)

```json
{
    "type": "auth_ok",
    "message": "Connecté ! (3 client(s) en ligne)",
    "online": ["987654321098765432", "111222333444555666"]
}
```

### Réponse Échec (Server → Client)

```json
{
    "type": "auth_fail",
    "reason": "guild_id et discord_id requis"
}
```

## Drop (Server → Client)

```json
{
    "type": "drop",
    "id": "uuid-unique",
    "media_type": "image | gif | video | text",
    "media_url": "https://...",
    "sound_url": "https://... | null",
    "text": "Texte affiché | null",
    "size": "small | medium | large | fullscreen",
    "position": "center | top | top_left | ...",
    "duration": 8.0,
    "effects": ["fade_in", "fade_out", "spin", "shake", "flip", "bounce"],
    "sender": "username"
}
```

## Réaction (Server → Client)

```json
{
    "type": "react",
    "emoji": "😂",
    "count": 5,
    "sender": "username"
}
```

## Contrôle (Server → Client)

```json
{ "type": "stop" }
{ "type": "skip" }
{ "type": "clear" }
```

## Keep-alive

```json
// Client → Server (toutes les 30s)
{ "type": "ping" }

// Server → Client
{ "type": "pong" }
```
