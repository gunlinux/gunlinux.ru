use serde::{Deserialize, Serialize};

/// Blog tag entity.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Tag {
    pub id: Option<i32>,
    pub title: String,
    pub alias: String,
}
