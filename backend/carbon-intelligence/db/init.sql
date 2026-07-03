CREATE TABLE IF NOT EXISTS verra (
  id SERIAL PRIMARY KEY,
  project_id VARCHAR(255) UNIQUE NOT NULL,
  project_name VARCHAR(500),
  description TEXT,
  methodology VARCHAR(100),
  country VARCHAR(100),
  vintage INT,
  price FLOAT,
  available_credits INT,
  category VARCHAR(100),
  image_url TEXT,
  buy_link TEXT,
  registry_status VARCHAR(100),
  project_summary TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS carbonmark (
  id SERIAL PRIMARY KEY,
  project_id VARCHAR(255) NOT NULL,
  project_name VARCHAR(500),
  vintage INT,
  amount FLOAT,
  project_summary TEXT,
  project_link VARCHAR(500),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS finance (
  id SERIAL PRIMARY KEY,
  ticker VARCHAR(20) NOT NULL UNIQUE,
  company_name TEXT,
  industry TEXT,
  description TEXT,
  gii_score INTEGER,
  stock_price FLOAT,
  market_cap TEXT,
  sustainability_update TEXT,
  esg_rating VARCHAR(10),
  website TEXT,
  price FLOAT,
  volume BIGINT,
  change_percent FLOAT,
  timestamp BIGINT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news (
  id TEXT PRIMARY KEY,
  title TEXT,
  summary TEXT,
  body TEXT,
  author TEXT,
  date TEXT,
  source TEXT,
  sentiment VARCHAR(20),
  image_url TEXT,
  guid TEXT,
  link TEXT,
  published TEXT,
  inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pathway output tables
CREATE TABLE IF NOT EXISTS pathway_projects (
  project_id TEXT PRIMARY KEY,
  project_name TEXT,
  registry_status TEXT,
  country TEXT,
  vintage INTEGER,
  supply DOUBLE PRECISION,
  time BIGINT,
  diff INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS pathway_news (
  guid TEXT PRIMARY KEY,
  title TEXT,
  link TEXT,
  published TEXT,
  source TEXT,
  summary TEXT,
  time BIGINT,
  diff INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ai_insights_cache (
  id SERIAL PRIMARY KEY,
  entity_type VARCHAR(50), 
  entity_id VARCHAR(100), 
  insight_type VARCHAR(50), 
  content TEXT, 
  generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
