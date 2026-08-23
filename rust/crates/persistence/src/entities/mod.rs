//! SeaORM entities mirroring the SQLAlchemy tables in
//! `app/infrastructure/database.py` (column names, nullability, types and
//! relations match the Python side 1:1).

pub mod category;
pub mod icon;
pub mod post;
pub mod posts_tag;
pub mod tag;
pub mod user;
