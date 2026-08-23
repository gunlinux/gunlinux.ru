use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

/// Mirrors `app/domain/user.py` `User` dataclass.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct User {
    pub id: Option<i32>,
    pub name: String,
    pub password: String,
    pub authenticated: bool,
    pub createdon: Option<DateTime<Utc>>,
}

impl User {
    pub fn new(name: impl Into<String>, password: impl Into<String>) -> Self {
        Self {
            id: None,
            name: name.into(),
            password: password.into(),
            authenticated: false,
            createdon: Some(Utc::now()),
        }
    }
}
