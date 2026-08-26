use serde::{Deserialize, Serialize};

/// Icon entity (footer/social icons).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Icon {
    pub id: Option<i32>,
    pub title: String,
    pub url: String,
    pub content: Option<String>,
}
