# ADR-005: Autenticación con JWT + Refresh Token Rotation

**Estado:** Aceptada
**Fecha:** 2024-01-01
**Autor:** Equipo de Arquitectura

## Contexto

Necesitamos un sistema de autenticación que sea stateless (para escalar horizontalmente), seguro, y que soporte múltiples dispositivos por usuario.

## Decisión

Implementar **JWT para access tokens** (corta vida, 15 min) + **Refresh tokens opacos almacenados en DB** (7 días, rotación en cada uso).

## Flujo

```
1. Login → access_token (15min) + refresh_token (7d)
2. API calls → Authorization: Bearer {access_token}
3. Token expirado → POST /auth/refresh con refresh_token
4. Server: verifica refresh_token, genera nuevo par, invalida el anterior
5. Si refresh_token ya fue usado → revocar todos los tokens del usuario (compromised)
```

## Justificación

- Access tokens cortos limitan la ventana de ataque si se comprometen
- Refresh token rotation detecta robo: si un token se usa dos veces, significa que fue interceptado
- Almacenar refresh tokens en DB permite revocación granular (por dispositivo, por sesión)
- JWT es stateless: no requiere consultar DB en cada request (solo validar firma)
- Compatible con OAuth2 flows para Google/Microsoft

## Seguridad Adicional

- Refresh tokens hasheados en DB (nunca en texto plano)
- Bound a IP y device fingerprint (alerta si cambian)
- Rate limiting en /auth/login: 10 intentos/minuto por IP
- MFA como segundo factor (TOTP via Google Authenticator)
- Blacklist de access tokens en Redis para revocación inmediata (logout)

## Consecuencias

- Los access tokens expirados no se pueden revocar instantáneamente (ventana de 15 min)
- Para logout inmediato: se usa una blacklist en Redis (trade-off: ya no es 100% stateless)
- Múltiples dispositivos requieren tracking de sesiones activas
- Los refresh tokens requieren limpieza periódica (cron para expirados)
