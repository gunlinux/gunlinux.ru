use serde::{Deserialize, Serialize};

/// Mirrors `app/domain/tag.py` `Tag` dataclass.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Tag {
    pub id: Option<i32>,
    pub title: String,
    pub alias: String,
}
