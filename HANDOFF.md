# Application Creation Instructions & Handoff Guide

## Overview
Build a collaborative trip-planning web application where users can authenticate via Google OAuth, create trips, invite companions, and collaboratively manage accommodations, transportation, and activities with high cybersecurity standards.

## Phase 1: Database and Data Modeling
- Implement relational database tables matching `db/schema.sql`.
- Enforce foreign key constraints, cascading deletes, and unique constraints for user handles, emails, and trip memberships.
- Implement structured time handling for trips supporting flexible season/year, exact date ranges, or multi-month spans without risking user input typos.

## Phase 2: Authentication and Security Layer
- Implement secure authentication supporting Google OAuth (Gmail login) and secure sessions/tokens.
- Build application-level encryption utilities (AES-256-GCM) for sensitive fields like confirmation codes.
- Set up secure object storage with short-lived pre-signed URLs for file uploads and booking documents.
- Implement middleware for Role-Based Access Control (RBAC) ensuring users only access authorized trips.

## Phase 3: Core API Development & Desktop Views
- Build server-rendered views for the desktop web interface.
- Build secure REST API endpoints for future mobile app synchronization.
- Build CRUD endpoints for stays, navs, dos, and recs supporting status fields (Idea vs Confirmed).
