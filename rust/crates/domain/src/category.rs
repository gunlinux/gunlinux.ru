use serde::{Deserialize, Serialize};

/// Blog category entity.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Category {
    pub id: Option<i32>,
    pub title: String,
    pub alias: String,
    pub template: Option<String>,
    pub page: Option<bool>,
}
