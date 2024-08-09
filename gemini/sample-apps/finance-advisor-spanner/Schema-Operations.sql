
ALTER MODEL EmbeddingsModel SET OPTIONS (
endpoint = '//aiplatform.googleapis.com/projects/<project-name>/locations/<location>/publishers/google/models/text-embedding-003'
)
;
ALTER TABLE EU_MutualFunds ADD COLUMN  fund_name_Tokens TOKENLIST AS (TOKENIZE_FULLTEXT(fund_name)) HIDDEN;
ALTER TABLE EU_MutualFunds ADD COLUMN  category_Tokens TOKENLIST AS (TOKENIZE_FULLTEXT(category)) HIDDEN;
ALTER TABLE EU_MutualFunds ADD COLUMN  investment_strategy_Tokens TOKENLIST AS (TOKENIZE_FULLTEXT(investment_strategy)) HIDDEN;
ALTER TABLE EU_MutualFunds ADD COLUMN  investment_managers_Tokens TOKENLIST AS (TOKENIZE_FULLTEXT(investment_managers)) HIDDEN;
ALTER TABLE EU_MutualFunds ADD COLUMN  fund_benchmark_Tokens TOKENLIST AS (TOKENIZE_FULLTEXT(fund_benchmark)) HIDDEN;
ALTER TABLE EU_MutualFunds ADD COLUMN  morningstar_benchmark_Tokens TOKENLIST AS (TOKENIZE_FULLTEXT(morningstar_benchmark)) HIDDEN;
ALTER TABLE EU_MutualFunds ADD COLUMN  top5_regions_Tokens TOKENLIST AS (TOKENIZE_FULLTEXT(top5_regions)) HIDDEN;
ALTER TABLE EU_MutualFunds ADD COLUMN  top5_holdings_Tokens TOKENLIST AS (TOKENIZE_FULLTEXT(top5_holdings)) HIDDEN;
ALTER TABLE EU_MutualFunds ADD COLUMN  investment_managers_Substring_Tokens  TOKENLIST AS (TOKENIZE_SUBSTRING(investment_managers)) HIDDEN;
ALTER TABLE
  EU_MutualFunds ADD COLUMN investment_managers_Substring_Tokens_NGRAM TOKENLIST AS ( TOKENIZE_SUBSTRING(investment_managers,
      ngram_size_min=>2,
      ngram_size_max=>3,
      relative_search_types=>["word_prefix",
      "word_suffix"])) HIDDEN;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1958 ;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2008;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2004;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1989;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2002;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2014;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2019;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2005;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1988;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2006;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1987;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2007;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1992;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1974;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2011;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1996;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2018;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1941;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1972;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1993;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2013;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1991;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2010;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1997;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2001;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2015;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1934;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1985;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1990;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2017;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1998;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1999;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2012;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1984;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1995;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2009;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2003;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1994;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1973;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1981;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2016;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2020;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 2000;
UPDATE EU_MutualFunds SET investment_strategy_Embedding_vector = investment_strategy_Embedding WHERE investment_strategy_Embedding is not NULL and  EXTRACT(YEAR from inception_date)  = 1992;
CREATE SEARCH INDEX
  category_Tokens_IDX
ON
  EU_MutualFunds(category_Tokens);
CREATE SEARCH INDEX
  fund_benchmark_Tokens_IDX
ON
  EU_MutualFunds(fund_benchmark_Tokens);
CREATE SEARCH INDEX
  fund_name_Tokens_IDX
ON
  EU_MutualFunds(fund_name_Tokens);
CREATE SEARCH INDEX
  investment_managers_Tokens_IDX
ON
  EU_MutualFunds(investment_managers_Tokens);
CREATE SEARCH INDEX
  investment_strategy_Tokens_IDX
ON
  EU_MutualFunds(investment_strategy_Tokens);
CREATE SEARCH INDEX
  morningstar_benchmark_Tokens_IDX
ON
  EU_MutualFunds(morningstar_benchmark_Tokens);
CREATE SEARCH INDEX
  top5_holdings_Tokens_IDX
ON
  EU_MutualFunds(top5_holdings_Tokens);
CREATE SEARCH INDEX
  top5_regions_Tokens_IDX
ON
  EU_MutualFunds(top5_regions_Tokens);
CREATE SEARCH INDEX
  investment_managers_Substring_Tokens_IDX
ON
  EU_MutualFunds(investment_managers_Substring_Tokens);
CREATE SEARCH INDEX
  investment_managers_Substring_investment_Strategy_Tokens_Combo_IDX
ON
  EU_MutualFunds(investment_managers_Substring_Tokens,
    investment_strategy_Tokens);
CREATE SEARCH INDEX
  investment_managers_Substring_NgRAM_investment_Strategy_Tokens_Combo_IDX
ON
  EU_MutualFunds(investment_strategy_Tokens,
    investment_managers_Substring_Tokens_NGRAM);
CREATE VECTOR INDEX
  InvestmentStrategyEmbeddingIndex
ON
  EU_MutualFunds(investment_strategy_Embedding_vector)
WHERE
  investment_strategy_Embedding_vector IS NOT NULL OPTIONS ( tree_depth = 2,
    num_leaves = 40,
    distance_type = 'EUCLIDEAN' );
CREATE SEARCH INDEX
  investment_managers_Substring_Tokens_with_vectors_NGRAM_IDX
ON
  EU_MutualFunds(investment_managers_Substring_Tokens_NGRAM) STORING (investment_strategy_Embedding_vector);
CREATE OR REPLACE PROPERTY GRAPH FundGraph NODE TABLES( Companies AS Company DEFAULT LABEL PROPERTIES ALL COLUMNS,
    EU_MutualFunds AS Fund DEFAULT LABEL PROPERTIES ALL COLUMNS EXCEPT (_Injected_SearchUid,
      _Injected_VectorIndex_InvestmentStrategyEmbeddingIndex_FP8,
      _Injected_VectorIndex_InvestmentStrategyEmbeddingIndex_LeafId),
    Sectors AS Sector DEFAULT LABEL PROPERTIES ALL COLUMNS ) EDGE TABLES( FundHoldsCompany SOURCE KEY(NewMFSequence)
  REFERENCES
    Fund(NewMFSequence) DESTINATION KEY(CompanySeq)
  REFERENCES
    Company(CompanySeq) LABEL Holds PROPERTIES ALL COLUMNS,
    CompanyBelongsSector SOURCE KEY(CompanySeq)
  REFERENCES
    Company(CompanySeq) DESTINATION KEY(SectorSeq)
  REFERENCES
    Sector(SectorSeq) LABEL Belongs_To PROPERTIES ALL COLUMNS );
