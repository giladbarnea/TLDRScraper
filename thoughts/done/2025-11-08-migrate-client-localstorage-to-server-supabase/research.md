---
status: completed
last_updated: 2025-11-21 15:35, f37f88a
---
# Supabase Database Research

Researched Supabase integration strategies for the TLDRScraper architecture. Decided on an API-only architecture where the React client communicates with the Flask backend, which then interacts with Supabase using the `service_role` key. This avoids exposing Supabase credentials to the client. Selected a 1:1 JSONB storage strategy for daily payloads (`daily_cache` table) to simplify migration and maintain feature parity without complex schema refactoring. Validated the use of the Python sync client for compatibility with the Flask threading model.

COMPLETED SUCCESSFULLY.
