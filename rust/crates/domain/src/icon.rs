use serde::{Deserialize, Serialize};

/// Mirrors `app/domain/icon.py` `Icon` dataclass.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Icon {
    pub id: Option<i32>,
    pub title: String,
    pub url: String,
    pub content: Option<String>,
}
