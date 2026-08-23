//! Password hashing. Ported from `app/models/user.py` `_hash`/`_verify`:
//! bcrypt, hashes stored in the existing DB must keep verifying, so the
//! algorithm and cost are fixed.

/// Hash a plaintext password with bcrypt.
pub fn hash_password(plain: &str) -> Result<String, bcrypt::BcryptError> {
    bcrypt::hash(plain, bcrypt::DEFAULT_COST)
}

/// Verify a plaintext password against a bcrypt hash. Any error (malformed
/// hash, etc.) is treated as a mismatch — never panics, mirroring the Python
/// `_verify` which swallows exceptions and returns False.
pub fn verify_password(plain: &str, hashed: &str) -> bool {
    bcrypt::verify(plain, hashed).unwrap_or(false)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hash_verify_roundtrip() {
        let hashed = hash_password("s3cret").unwrap();
        assert_ne!(hashed, "s3cret");
        assert!(verify_password("s3cret", &hashed));
    }

    #[test]
    fn wrong_password_fails() {
        let hashed = hash_password("right").unwrap();
        assert!(!verify_password("wrong", &hashed));
    }

    #[test]
    fn malformed_hash_is_false() {
        assert!(!verify_password("x", "not-a-bcrypt-hash"));
        assert!(!verify_password("x", ""));
    }
}
