-- Copyright 2026 Google LLC
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

-- 1. Product Catalog Table with Text & Image Embeddings for Semantic/Multimodal Search
CREATE TABLE products (
  product_id STRING(50) NOT NULL,
  name STRING(255) NOT NULL,
  description STRING(MAX),
  price NUMERIC NOT NULL,
  inventory_level INT64 NOT NULL,
  image_url STRING(MAX), -- URL pointing to the product image
  embedding ARRAY<FLOAT32>(vector_length=>768), -- Text semantic embeddings
  image_embedding ARRAY<FLOAT32>(vector_length=>1408), -- Multimodal image embeddings
  name_tokens TOKENLIST AS (TOKENIZE_FULLTEXT(name)) STORED HIDDEN, -- Fulltext search index
) PRIMARY KEY (product_id);

-- 2. Customer Profiles
CREATE TABLE customers (
  customer_id STRING(50) NOT NULL,
  name STRING(255) NOT NULL,
  email STRING(255) NOT NULL,
  created_at TIMESTAMP OPTIONS (allow_commit_timestamp=true),
) PRIMARY KEY (customer_id);

-- 3. Ephemeral Shopping Carts (Multi-User Session Isolation Sandbox)
CREATE TABLE shopping_carts (
  session_id STRING(100) NOT NULL,
  product_id STRING(50) NOT NULL,
  quantity INT64 NOT NULL,
  updated_at TIMESTAMP OPTIONS (allow_commit_timestamp=true),
) PRIMARY KEY (session_id, product_id);

-- 4. Order Transactions
CREATE TABLE orders (
  order_id STRING(50) NOT NULL,
  customer_id STRING(50) NOT NULL,
  total_amount NUMERIC NOT NULL,
  created_at TIMESTAMP OPTIONS (allow_commit_timestamp=true),
) PRIMARY KEY (order_id);

-- 5. Order Lines
CREATE TABLE order_items (
  order_id STRING(50) NOT NULL,
  product_id STRING(50) NOT NULL,
  quantity INT64 NOT NULL,
  unit_price NUMERIC NOT NULL,
) PRIMARY KEY (order_id, product_id),
  INTERLEAVE IN PARENT orders ON DELETE CASCADE;

-- 6. Retailer Active Theme & Configurations
CREATE TABLE retailer_settings (
  config_id STRING(50) NOT NULL,
  retailer_name STRING(255) NOT NULL,
  theme_config JSON,
  assistant_persona STRING(50),
  updated_at TIMESTAMP OPTIONS (allow_commit_timestamp=true),
) PRIMARY KEY (config_id);

-- 7. Product Reviews and Ratings (Interleaved under products)
CREATE TABLE reviews (
  product_id STRING(50) NOT NULL,
  review_id STRING(50) NOT NULL,
  customer_name STRING(255) NOT NULL,
  rating INT64 NOT NULL,
  comment STRING(MAX),
  created_at TIMESTAMP OPTIONS (allow_commit_timestamp=true),
) PRIMARY KEY (product_id, review_id),
  INTERLEAVE IN PARENT products ON DELETE CASCADE;
