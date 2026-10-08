PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS vacancies (
  vacancy_id INTEGER PRIMARY KEY AUTOINCREMENT,
  dedupe_key TEXT NOT NULL UNIQUE,
  external_id TEXT,
  display_title TEXT NOT NULL,
  title_raw TEXT,
  advertiser TEXT,
  advertiser_type TEXT NOT NULL DEFAULT 'MIXED_OR_UNKNOWN',
  advertiser_type_confidence REAL NOT NULL DEFAULT 0,
  role_family TEXT,
  role_seniority TEXT,
  role_specialism TEXT,
  role_confidence REAL NOT NULL DEFAULT 0,
  role_review_required INTEGER NOT NULL DEFAULT 0,
  end_client_name TEXT,
  end_client_sector TEXT,
  end_client_sector_confidence REAL NOT NULL DEFAULT 0,
  end_client_method TEXT,
  sector_basis TEXT,
  sector_review_required INTEGER NOT NULL DEFAULT 0,
  location TEXT,
  employment_type TEXT,
  contract_type TEXT,
  salary_min REAL,
  salary_max REAL,
  salary_currency TEXT,
  salary_period TEXT,
  job_url TEXT,
  description TEXT,
  posted_at TEXT,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  lifecycle_status TEXT NOT NULL DEFAULT 'ACTIVE',
  lifecycle_reason TEXT,
  lifecycle_updated_at TEXT,
  last_verified_at TEXT,
  unavailable_streak INTEGER NOT NULL DEFAULT 0,
  unavailable_first_seen_at TEXT,
  normalized_hash TEXT NOT NULL,
  raw_json TEXT,
  master_data_version TEXT NOT NULL,
  role_taxonomy_version TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_vacancies_posted_at ON vacancies(posted_at);
CREATE INDEX IF NOT EXISTS idx_vacancies_role_family ON vacancies(role_family);
CREATE INDEX IF NOT EXISTS idx_vacancies_sector ON vacancies(end_client_sector);
CREATE INDEX IF NOT EXISTS idx_vacancies_advertiser_type ON vacancies(advertiser_type);

CREATE TABLE IF NOT EXISTS vacancy_sources (
  source_name TEXT NOT NULL,
  source_record_id TEXT NOT NULL,
  vacancy_id INTEGER NOT NULL REFERENCES vacancies(vacancy_id) ON DELETE CASCADE,
  source_url TEXT,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  raw_hash TEXT NOT NULL,
  PRIMARY KEY (source_name, source_record_id)
);

CREATE TABLE IF NOT EXISTS refresh_runs (
  run_id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  inserted_rows INTEGER NOT NULL DEFAULT 0,
  updated_rows INTEGER NOT NULL DEFAULT 0,
  unchanged_rows INTEGER NOT NULL DEFAULT 0,
  rejected_rows INTEGER NOT NULL DEFAULT 0,
  role_review_rows INTEGER NOT NULL DEFAULT 0,
  sector_review_rows INTEGER NOT NULL DEFAULT 0,
  master_data_version TEXT,
  role_taxonomy_version TEXT
);

CREATE TABLE IF NOT EXISTS lifecycle_checks (
  check_id INTEGER PRIMARY KEY AUTOINCREMENT,
  vacancy_id INTEGER NOT NULL REFERENCES vacancies(vacancy_id) ON DELETE CASCADE,
  checked_at TEXT NOT NULL,
  result TEXT NOT NULL,
  evidence_type TEXT NOT NULL,
  http_status INTEGER,
  checked_url TEXT,
  final_url TEXT,
  detail TEXT
);

CREATE INDEX IF NOT EXISTS idx_lifecycle_checks_vacancy ON lifecycle_checks(vacancy_id, checked_at);
