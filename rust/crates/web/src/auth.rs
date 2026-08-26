//! Auth: JWT (HS256) + signed session cookie.
//!
//! - JWT claims `{sub, exp}` where `exp = now + jwt_expire_minutes`, HS256
//!   signed with `settings.secret_key`; `decode_token` returns `None` on *any*
//!   error (bad signature, expired, malformed — the caller treats all as
//!   "not authenticated").
//! - The browser cookie is named `session` and its value is
//!   `base64url(json) + "." + hex(hmac_sha256(base64url(json), secret_key))`
//!   where `json` is `{"access_token": "<jwt>"}` (the JWT lives under the
//!   `access_token` key of the session).

use std::collections::HashMap;

use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use base64::Engine;
use chrono::Utc;
use hmac::{Hmac, Mac};
use jsonwebtoken::{decode, encode, Algorithm, DecodingKey, EncodingKey, Header, Validation};
use serde::{Deserialize, Serialize};
use sha2::Sha256;

use crate::settings::Settings;

/// The signed session cookie name.
pub const SESSION_COOKIE_NAME: &str = "session";
/// The JSON key under which the JWT lives inside the session.
pub const ACCESS_TOKEN_KEY: &str = "access_token";

#[derive(Debug, Serialize, Deserialize)]
struct Claims {
    sub: String,
    exp: usize,
}

/// Create a JWT for `subject` (the user name), valid for
/// `settings.jwt_expire_minutes`.
pub fn create_access_token(
    subject: &str,
    settings: &Settings,
) -> Result<String, jsonwebtoken::errors::Error> {
    let exp = (Utc::now().timestamp() + settings.jwt_expire_minutes * 60) as usize;
    let claims = Claims {
        sub: subject.to_string(),
        exp,
    };
    encode(
        &Header::new(Algorithm::HS256),
        &claims,
        &EncodingKey::from_secret(settings.secret_key.as_bytes()),
    )
}

/// Decode a JWT and return the `sub` claim. `None` on any error (bad signature,
/// expired, malformed).
pub fn decode_token(token: &str, settings: &Settings) -> Option<String> {
    let data = decode::<Claims>(
        token,
        &DecodingKey::from_secret(settings.secret_key.as_bytes()),
        &Validation::new(Algorithm::HS256),
    )
    .ok()?;
    Some(data.claims.sub)
}

fn sign(data: &str, secret: &[u8]) -> String {
    type HmacSha256 = Hmac<Sha256>;
    let mut mac = HmacSha256::new_from_slice(secret).expect("HMAC accepts any key length");
    mac.update(data.as_bytes());
    hex::encode(mac.finalize().into_bytes())
}

/// Build the signed `session` cookie *value* for a session holding the given
/// access token: `base64url(json) + "." + hex(hmac)`.
pub fn set_access_token(token: &str, secret: &[u8]) -> String {
    let json = serde_json::to_string(&HashMap::from([(ACCESS_TOKEN_KEY, token)]))
        .expect("session json serialization cannot fail");
    let data = URL_SAFE_NO_PAD.encode(json.as_bytes());
    let signature = sign(&data, secret);
    format!("{data}.{signature}")
}

/// Read and verify a signed `session` cookie value, returning the JWT stored
/// under `access_token` — or `None` if missing, tampered, or malformed.
pub fn read_access_token(cookie_value: &str, secret: &[u8]) -> Option<String> {
    let (data, signature) = cookie_value.split_once('.')?;
    // Constant-time comparison to avoid timing side channels.
    let expected = sign(data, secret);
    let ok = constant_time_eq(&expected, signature);
    if !ok {
        return None;
    }
    let json = URL_SAFE_NO_PAD.decode(data.as_bytes()).ok()?;
    let session: HashMap<String, String> = serde_json::from_slice(&json).ok()?;
    session.get(ACCESS_TOKEN_KEY).cloned()
}

/// Build a `Set-Cookie` header that expires the `session` cookie (logout).
pub fn clear_access_token() -> String {
    // Empty value + Max-Age=0 → the browser drops the cookie immediately.
    format!("{SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=lax; Max-Age=0")
}

/// Build a `Set-Cookie` header that installs a signed session cookie carrying
/// `token` (HttpOnly, SameSite=lax, 14 day max-age).
pub fn set_cookie_header(token: &str, secret: &[u8]) -> String {
    let value = set_access_token(token, secret);
    format!("{SESSION_COOKIE_NAME}={value}; Path=/; HttpOnly; SameSite=lax; Max-Age=1209600")
}

/// Extract the value of `name` from a `Cookie` header.
pub fn cookie_value(cookie_header: &str, name: &str) -> Option<String> {
    cookie_header.split(';').find_map(|part| {
        let part = part.trim();
        let (key, value) = part.split_once('=')?;
        if key.trim() == name {
            Some(value.to_string())
        } else {
            None
        }
    })
}

fn constant_time_eq(a: &str, b: &str) -> bool {
    let a = a.as_bytes();
    let b = b.as_bytes();
    if a.len() != b.len() {
        return false;
    }
    let mut diff = 0u8;
    for (x, y) in a.iter().zip(b.iter()) {
        diff |= x ^ y;
    }
    diff == 0
}

#[cfg(test)]
mod tests {
    use super::*;

    fn settings_with(secret: &str, expire_minutes: i64) -> Settings {
        Settings {
            secret_key: secret.to_string(),
            jwt_expire_minutes: expire_minutes,
            ..Settings::default()
        }
    }

    #[test]
    fn jwt_roundtrip() {
        let s = Settings::default();
        let token = create_access_token("testuser", &s).unwrap();
        assert!(token.contains('.'));
        assert_eq!(decode_token(&token, &s).as_deref(), Some("testuser"));
    }

    #[test]
    fn jwt_invalid_returns_none() {
        let s = Settings::default();
        assert_eq!(decode_token("not-a-valid-token", &s), None);
        assert_eq!(decode_token("", &s), None);
    }

    #[test]
    fn jwt_secret_comes_from_injected_settings() {
        let a = settings_with("secret-a", 60);
        let b = settings_with("secret-b", 60);
        let token = create_access_token("testuser", &a).unwrap();
        assert_eq!(decode_token(&token, &a).as_deref(), Some("testuser"));
        assert_eq!(decode_token(&token, &b), None);
    }

    #[test]
    fn jwt_respects_expiry_from_injected_settings() {
        // A token issued with a negative expiry window is already expired and
        // must not decode (jsonwebtoken default leeway is 60 s; -2 minutes
        // keeps the assertion deterministic).
        let s = settings_with("secret-a", -2);
        let token = create_access_token("testuser", &s).unwrap();
        assert_eq!(decode_token(&token, &s), None);
    }

    #[test]
    fn session_cookie_roundtrip() {
        let secret = b"hard-to-guess-string-change-in-production";
        let cookie = set_access_token("my-jwt", secret);
        assert_eq!(
            read_access_token(&cookie, secret).as_deref(),
            Some("my-jwt")
        );
    }

    #[test]
    fn session_cookie_tamper_detected() {
        let secret = b"hard-to-guess-string-change-in-production";
        let mut cookie = set_access_token("my-jwt", secret);
        // Flip a character inside the base64 payload.
        let dot = cookie.find('.').unwrap();
        let first = cookie.as_bytes()[0];
        let replacement = if first == b'A' { b'B' } else { b'A' };
        cookie.replace_range(0..1, &(replacement as char).to_string());
        let _ = dot;
        assert_eq!(read_access_token(&cookie, secret), None);
        assert_eq!(read_access_token("garbage", secret), None);
        assert_eq!(read_access_token("", secret), None);
    }

    #[test]
    fn session_cookie_wrong_secret_detected() {
        let cookie = set_access_token("my-jwt", b"secret-a");
        assert_eq!(read_access_token(&cookie, b"secret-b"), None);
    }

    #[test]
    fn cookie_header_parsing() {
        let header = "session=abc.def; other=x";
        assert_eq!(cookie_value(header, "session").as_deref(), Some("abc.def"));
        assert_eq!(cookie_value(header, "missing"), None);
    }
}
